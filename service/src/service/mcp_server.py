"""
FastMCP server wrapping Pharia skills.

Tools defined with @mcp.tool() decorators can be:
1. Called via MCP protocol (stdio/SSE) for Claude Desktop
2. Called programmatically via execute_tool() for HTTP API
"""

from typing import Any, Callable

from fastmcp import FastMCP

from service.logging_config import logger
from service.tools import (
    tool_classify_chart_type,
    tool_execute_sql,
    tool_generate_chart,
    tool_generate_sql,
)

mcp = FastMCP("Text2SQL")

_kernel: Any = None
_database: Any = None
_token: str = ""


def initialize(kernel, database):
    """Initialize tool executor with kernel and database."""
    global _kernel, _database
    _kernel = kernel
    _database = database
    logger.info("Tool executor initialized with kernel and database")


def set_token(token: str):
    """Set authentication token for current request."""
    global _token
    _token = token
    logger.debug("Token set for request")


async def _run_generate_sql(
    question: str, error_feedback: str | None = None
) -> dict[str, Any]:
    """Execute SQL generation tool."""
    logger.info("Executing: generate_sql")
    if error_feedback:
        logger.info(f"With error feedback: {error_feedback[:100]}...")

    result = await tool_generate_sql(_kernel, _token, question, error_feedback)

    if not result["success"]:
        raise Exception(result.get("error", "SQL generation failed"))

    return {"sql_query": result["sql_query"]}


async def _run_execute_sql(query: str) -> dict[str, Any]:
    """Execute SQL query tool."""
    logger.info("Executing: execute_sql")

    result = await tool_execute_sql(_database, query)

    if not result["success"]:
        raise Exception(result.get("error", "Query execution failed"))

    return {
        "query": result["query"],
        "headers": result["headers"],
        "rows": result["rows"],
        "count": result["count"],
    }


async def _run_classify_chart_type(
    query: str, headers: list[str], rows: list[list]
) -> dict[str, Any]:
    """Execute chart classification tool."""
    logger.info(f"Executing: classify_chart_type ({len(rows)} rows)")

    result = await tool_classify_chart_type(_kernel, _token, query, headers, rows)

    if not result["success"]:
        raise Exception(result.get("error", "Chart classification failed"))

    return {
        "chart_type": result["chart_type"],
        "headers": result["headers"],
        "rows_count": result["rows_count"],
    }


async def _run_generate_chart(
    query: str, headers: list[str], rows: list[list]
) -> dict[str, Any]:
    """Execute chart generation tool."""
    logger.info(f"Executing: generate_chart ({len(rows)} rows)")

    result = await tool_generate_chart(_kernel, _token, query, headers, rows)

    if not result["success"]:
        raise Exception(result.get("error", "Chart generation failed"))

    return {
        "chart_image": result["chart_image"],
        "image_size_kb": result["image_size_kb"],
        "rows_count": result["rows_count"],
    }


@mcp.tool()
async def generate_sql(
    question: str, error_feedback: str | None = None
) -> dict[str, Any]:
    """Convert natural language to SQL query."""
    return await _run_generate_sql(question, error_feedback)


@mcp.tool()
async def execute_sql(query: str) -> dict[str, Any]:
    """Execute SQL query on database."""
    return await _run_execute_sql(query)


@mcp.tool()
async def classify_chart_type(
    query: str, headers: list[str], rows: list[list]
) -> dict[str, Any]:
    """Analyze data and recommend chart type."""
    return await _run_classify_chart_type(query, headers, rows)


@mcp.tool()
async def generate_chart(
    query: str, headers: list[str], rows: list[list]
) -> dict[str, Any]:
    """Generate chart visualization."""
    return await _run_generate_chart(query, headers, rows)


_TOOL_IMPLEMENTATIONS: dict[str, Callable] = {
    "generate_sql": _run_generate_sql,
    "execute_sql": _run_execute_sql,
    "classify_chart_type": _run_classify_chart_type,
    "generate_chart": _run_generate_chart,
}


async def execute_tool(tool_name: str, arguments: dict[str, Any]) -> Any:
    """
    Execute FastMCP tool programmatically.

    This allows HTTP endpoint to call tools without MCP protocol.

    Args:
        tool_name: Name of tool to execute
        arguments: Tool arguments

    Returns:
        Tool result data

    Raises:
        ValueError: If tool not found
        Exception: If tool execution fails
    """
    if tool_name not in _TOOL_IMPLEMENTATIONS:
        raise ValueError(f"Unknown tool: {tool_name}")

    tool_impl = _TOOL_IMPLEMENTATIONS[tool_name]
    return await tool_impl(**arguments)


__all__ = ["mcp", "initialize", "set_token", "execute_tool"]
