"""Tool functions that wrap Pharia skills for Text2SQL."""

from typing import Any, Dict, List

from service.chart_service import generate_chart_image
from service.db_service import SQLiteDatabase
from service.kernel import Kernel, KernelException, Skill
from service.logging_config import logger


async def tool_generate_sql(
    kernel: Kernel, token: str, question: str, error_feedback: str | None = None
) -> Dict[str, Any]:
    """
    Generate SQL from natural language using Pharia sql-generator skill.

    Args:
        error_feedback: Optional SQL error from previous attempt for self-correction
    """
    logger.info("Tool generate_sql called")
    logger.debug(f"Question: {question}")
    if error_feedback:
        logger.info(f"Retrying with error feedback: {error_feedback[:100]}...")

    try:
        skill = Skill(namespace="playground", name="sql-generator")

        # Include error feedback to help skill correct itself
        skill_question = question
        if error_feedback:
            skill_question = f"{question}\n\nPrevious attempt failed with error: {error_feedback}\nPlease fix the SQL for SQLite (use strftime for dates, etc.)"

        response = await kernel.run(skill, token, {"question": skill_question})

        sql_query = response.get("answer")
        if not sql_query:
            logger.warning("No SQL query returned from skill")
            return {"success": False, "error": "Unable to generate SQL query"}

        logger.info("SQL query generated successfully")
        return {"success": True, "sql_query": sql_query}

    except KernelException as e:
        logger.error(f"Kernel error in generate_sql: {e}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.exception(f"Error in generate_sql: {e}")
        return {"success": False, "error": str(e)}


async def tool_execute_sql(database: SQLiteDatabase, query: str) -> Dict[str, Any]:
    """Execute SQL query on database."""
    logger.info("Tool execute_sql called")
    logger.debug(f"Query: {query}")

    try:
        if not database.is_connected:
            logger.debug("Connecting to database...")
            database.connect()

        headers, rows = database.query(query)
        row_count = len(rows) if isinstance(rows, list) else 1

        logger.info(
            f"Query executed successfully: {row_count} rows, {len(headers)} columns"
        )

        return {
            "success": True,
            "query": query,
            "headers": headers,
            "rows": rows,
            "count": row_count,
        }

    except Exception as e:
        logger.exception(f"Error in execute_sql: {e}")
        return {"success": False, "error": str(e)}


async def tool_classify_chart_type(
    kernel: Kernel, token: str, query: str, headers: List[str], rows: List[List]
) -> Dict[str, Any]:
    """Classify chart type using Pharia chart-classifier skill."""
    logger.info("Tool classify_chart_type called")
    logger.debug(f"Analyzing {len(rows)} rows with {len(headers)} columns: {headers}")

    try:
        skill = Skill(namespace="playground", name="chart_classifier")
        response = await kernel.run(
            skill, token, {"query": query, "headers": headers, "rows": rows}
        )

        chart_type = response.get("chart_type", "bar")
        logger.info(f"Chart type classified as: {chart_type.upper()}")

        return {
            "success": True,
            "chart_type": chart_type,
            "rows_count": len(rows),
            "headers": headers,
        }

    except KernelException as e:
        logger.error(f"Kernel error in classify_chart_type: {e}")
        return {"success": False, "error": str(e), "chart_type": "bar"}
    except Exception as e:
        logger.exception(f"Error in classify_chart_type: {e}")
        return {"success": False, "error": str(e), "chart_type": "bar"}


async def tool_generate_chart(
    kernel: Kernel, token: str, query: str, headers: List[str], rows: List[List]
) -> Dict[str, Any]:
    """Generate chart image using Pharia chart-classifier and chart-code-generator skills."""
    logger.info("Tool generate_chart called")
    logger.debug(f"Chart data: {len(rows)} rows, {len(headers)} columns")

    try:
        chart_base64 = await generate_chart_image(kernel, token, query, headers, rows)

        image_size_kb = len(chart_base64) * 3 / 4 / 1024
        logger.info(f"Chart image generated successfully: ~{image_size_kb:.1f}KB PNG")

        return {
            "success": True,
            "chart_image": chart_base64,
            "image_size_kb": image_size_kb,
            "rows_count": len(rows),
        }

    except Exception as e:
        logger.exception(f"Error in generate_chart: {e}")
        return {"success": False, "error": str(e)}
