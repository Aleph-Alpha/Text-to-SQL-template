from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"]


class QaInput(BaseModel):
    question: str


class QaOutput(BaseModel):
    answer: str | None


class SpiderExample(BaseModel):
    question: str
    query: str
    db_id: str


class ToolResponseType(str, Enum):
    """Types of tool responses for frontend handling."""

    SQL_QUERY = "sql_query"
    QUERY_RESULTS = "query_results"
    CHART_TYPE = "chart_type"
    CHART_IMAGE = "chart_image"
    ERROR = "error"


class AgentRequest(BaseModel):
    """Request to /agent endpoint."""

    message: str = Field(..., description="User question or command")
    context: dict[str, Any] | None = Field(
        None, description="Optional context (query, data for charts)"
    )


class AgentResponse(BaseModel):
    """Response from /agent endpoint."""

    response_type: ToolResponseType = Field(..., description="Type of response")
    data: dict[str, Any] = Field(..., description="Response data")
    tool_used: str = Field(..., description="Tool that was executed")
    success: bool = Field(..., description="Whether operation succeeded")


class ToolRouterDecision(BaseModel):
    """Decision from tool_router skill."""

    tool: str = Field(..., description="Tool to execute")
    arguments: dict[str, Any] = Field(
        default_factory=dict, description="Tool arguments"
    )


class SQLQueryData(BaseModel):
    """Data for SQL query response."""

    sql_query: str


class QueryResultsData(BaseModel):
    """Data for query results response."""

    query: str
    headers: list[str]
    rows: list[list]
    count: int


class ChartTypeData(BaseModel):
    """Data for chart type response."""

    chart_type: str
    headers: list[str]
    rows_count: int


class ChartImageData(BaseModel):
    """Data for chart image response."""

    chart_image: str  # base64
    image_size_kb: float
    rows_count: int


class ErrorData(BaseModel):
    """Data for error response."""

    error: str
