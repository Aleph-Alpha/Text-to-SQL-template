from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from service.dependencies import get_token, with_kernel
from service.kernel import Json, Kernel, KernelException, Skill
from service.logging_config import logger
from service.mcp_server import execute_tool, set_token
from service.models import (
    AgentRequest,
    AgentResponse,
    HealthResponse,
    ToolResponseType,
    ToolRouterDecision,
)

router: APIRouter = APIRouter()


@router.get("/health")
def health() -> HealthResponse:
    """Health check."""
    return HealthResponse(status="ok")


@router.post("/agent")
async def agent_endpoint(
    request: Request,
    token: str = Depends(get_token),
    kernel: Kernel = Depends(with_kernel),
) -> Json:
    """
    Intelligent agent endpoint.

    Orchestrates tools using tool_router skill + FastMCP.
    """
    logger.info("Agent: Request received")

    try:
        body = await request.json()
        req = AgentRequest(**body)
        logger.info(f"Agent: Message: {req.message}")

        set_token(token)

        decision = await _get_tool_decision(
            kernel, token, req.message, req.context or {}
        )

        if not decision:
            return _error_response("Could not determine tool")

        logger.info(f"Agent: Executing tool: {decision.tool}")

        response = await _execute_with_retry(decision, req.message, req.context or {})

        return response.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Agent failed: {e}")
        return _error_response(str(e)).model_dump()


async def _get_tool_decision(
    kernel: Kernel, token: str, message: str, context: dict[str, Any]
) -> ToolRouterDecision | None:
    """
    Call tool_router Pharia skill to determine which tool to execute.

    Returns:
        ToolRouterDecision with tool name and arguments, or None if failed
    """
    logger.debug("Calling tool_router skill")

    try:
        router_skill = Skill(namespace="playground", name="tool_router")
        response = await kernel.run(
            router_skill,
            token,
            {"message": message, "context": context if context else None},
        )

        decision = ToolRouterDecision(
            tool=response.get("tool", ""), arguments=response.get("arguments", {})
        )

        logger.info(f"Tool-router chose: {decision.tool}")
        return decision

    except KernelException as e:
        logger.error(f"Tool-router skill failed: {e}")
        return _fallback_tool_decision(message, context)
    except Exception as e:
        logger.exception(f"Tool-router error: {e}")
        return None


def _fallback_tool_decision(
    message: str, context: dict[str, Any]
) -> ToolRouterDecision:
    """Fallback decision when tool_router skill fails."""
    logger.warning("Using fallback tool decision")

    if context.get("query") and not context.get("headers"):
        return ToolRouterDecision(
            tool="execute_sql", arguments={"query": context["query"]}
        )
    elif context.get("headers"):
        return ToolRouterDecision(
            tool="generate_chart",
            arguments={
                "query": context.get("query", ""),
                "headers": context["headers"],
                "rows": context.get("rows", []),
            },
        )
    else:
        return ToolRouterDecision(tool="generate_sql", arguments={"question": message})


async def _execute_with_retry(
    decision: ToolRouterDecision, message: str, context: dict[str, Any]
) -> AgentResponse:
    """
    Execute tool with automatic retry on SQL errors.

    Returns:
        AgentResponse with typed data
    """
    response_types = {
        "generate_sql": ToolResponseType.SQL_QUERY,
        "execute_sql": ToolResponseType.QUERY_RESULTS,
        "classify_chart_type": ToolResponseType.CHART_TYPE,
        "generate_chart": ToolResponseType.CHART_IMAGE,
    }

    try:
        data = await execute_tool(decision.tool, decision.arguments)

        return AgentResponse(
            response_type=response_types.get(decision.tool, ToolResponseType.ERROR),
            data=data,
            tool_used=decision.tool,
            success=True,
        )

    except Exception as e:
        error_msg = str(e)

        if decision.tool == "execute_sql" and _is_fixable_sql_error(error_msg):
            retry_response = await _retry_sql_with_correction(
                error_msg, message, context
            )
            if retry_response:
                return retry_response

        return _error_response(error_msg, decision.tool)


def _is_fixable_sql_error(error: str) -> bool:
    """Check if SQL error is fixable through regeneration."""
    fixable_errors = ["no such function", "syntax error", "no such column", "near"]
    return any(err in error.lower() for err in fixable_errors)


async def _retry_sql_with_correction(
    error: str, message: str, context: dict[str, Any]
) -> AgentResponse | None:
    """
    Attempt to fix SQL error by regenerating with feedback.

    Returns:
        AgentResponse if successful, None if failed
    """
    logger.warning(f"SQL failed: {error}")
    logger.info("Attempting SQL self-correction")

    try:
        original_question = context.get("original_question", message)

        corrected = await execute_tool(
            "generate_sql", {"question": original_question, "error_feedback": error}
        )

        logger.info("Retrying with corrected SQL")

        data = await execute_tool("execute_sql", {"query": corrected["sql_query"]})

        logger.info("SQL self-correction successful!")

        return AgentResponse(
            response_type=ToolResponseType.QUERY_RESULTS,
            data=data,
            tool_used="execute_sql",
            success=True,
        )

    except Exception as retry_error:
        logger.error(f"Retry failed: {retry_error}")
        return None


def _error_response(error: str, tool_used: str = "unknown") -> AgentResponse:
    """Create error response."""
    return AgentResponse(
        response_type=ToolResponseType.ERROR,
        data={"error": error},
        tool_used=tool_used,
        success=False,
    )
