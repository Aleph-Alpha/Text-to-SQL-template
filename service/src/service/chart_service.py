"""Chart generation service."""

import base64
import hashlib
import os
import subprocess
import sys
import tempfile
import uuid
from typing import List

from service.kernel import Kernel, KernelException, Skill
from service.logging_config import logger


def _generate_unique_chart_id(query: str, headers: list, rows: list) -> str:
    """Generate a unique identifier for the chart based on query and data."""
    query_hash = hashlib.md5(
        f"{query}_{str(headers)}_{str(rows)}".encode()
    ).hexdigest()[:8]
    return f"chart_{query_hash}_{uuid.uuid4().hex[:8]}"


def _create_data_preparation_code(headers: list, rows: list) -> str:
    """Create Python code to prepare and clean the data for chart generation."""
    return f"""
import pandas as pd
import numpy as np

# Data from SQL query
headers = {headers}
rows = {rows}

# Create DataFrame and clean data
df = pd.DataFrame(rows, columns=headers)

# Simple data cleaning - convert columns to appropriate types
for col in df.columns:
    if df[col].dtype == 'object':
        # Try to convert to numeric, but keep as string if it fails
        numeric_series = pd.to_numeric(df[col], errors='coerce')
        # Only convert if most values are successfully converted to numbers
        if not numeric_series.isna().all():
            # Check if it looks like it should be numeric (more than 50% converted successfully)
            if (numeric_series.notna().sum() / len(df)) > 0.5:
                df[col] = numeric_series.fillna(0)

print(f"DataFrame shape after cleaning: {{df.shape}}")
print(f"DataFrame dtypes: {{df.dtypes.to_dict()}}")
print(f"DataFrame head: {{df.head().to_dict()}}")
"""


def _create_chart_execution_code(
    chart_code: str, chart_uuid: str, temp_dir: str
) -> str:
    """Create the complete Python code to execute chart generation."""
    return f"""
import sys
sys.path.append({repr(temp_dir)})
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server-side generation
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Import the prepared data
from data import df, headers, rows

print("DataFrame loaded:")
print(f"Shape: {{df.shape}}")
print(f"Columns: {{df.columns.tolist()}}")
print(f"Data types: {{df.dtypes.to_dict()}}")
print("First few rows:")
print(df.head())

# Check if DataFrame is empty
if df.empty:
    print("DataFrame is empty, creating placeholder chart")
    plt.figure(figsize=(8, 6))
    plt.text(0.5, 0.5, 'No data available', ha='center', va='center', fontsize=16)
    plt.xlim(0, 1)
    plt.ylim(0, 1)
    plt.title('No Data Available')
else:
    print("Generating chart with data")
    {chart_code}

# Save the chart with unique filename
plt.savefig({repr(chart_uuid + '.png')}, dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
print(f"Chart saved as {chart_uuid}.png")
plt.close()
"""


def _execute_chart_generation(
    chart_file: str, temp_dir: str
) -> subprocess.CompletedProcess:
    """Execute the chart generation Python script."""
    return subprocess.run(
        [sys.executable, chart_file],
        cwd=temp_dir,
        capture_output=True,
        text=True,
        timeout=60,
    )


async def _generate_chart_code(
    kernel: Kernel, token: str, query: str, headers: list, rows: list
) -> str:
    """Use AI to determine chart type and generate Python chart code based on the data."""
    logger.info(f"Chart generation step 1: Classifying chart type for {len(rows)} rows")
    logger.debug(f"Headers: {headers}")

    # Step 1: Classify the chart type
    classifier_skill = Skill(namespace="playground", name="chart_classifier")
    classifier_input = {"query": query, "headers": headers, "rows": rows}

    try:
        classifier_response = await kernel.run(
            classifier_skill, token, classifier_input
        )
        chart_type = classifier_response.get("chart_type")

        if not chart_type:
            logger.warning("Chart classification failed, defaulting to bar chart")
            chart_type = "bar"

        logger.info(f"Chart type classified as: {chart_type.upper()}")

    except KernelException as exp:
        logger.error(f"Chart classifier skill error: {exp}")
        logger.warning("Using default chart type: bar")
        chart_type = "bar"

    # Step 2: Generate chart code based on the classified type
    logger.info(f"Chart generation step 2: Generating {chart_type} chart code")
    generator_skill = Skill(namespace="playground", name="chart_generator")
    generator_input = {
        "chart_type": chart_type,
        "query": query,
        "headers": headers,
        "rows": rows,
    }

    try:
        generator_response = await kernel.run(generator_skill, token, generator_input)
        chart_code = generator_response.get("chart_code")

        if not chart_code:
            logger.error("No chart code returned from generator skill")
            raise Exception("Failed to generate chart code")

        code_lines = len(chart_code.split("\n"))
        logger.info(
            f"Chart code generated successfully: {code_lines} lines of Python code"
        )
        logger.debug(f"Code preview: {chart_code[:150]}...")

        return chart_code
    except KernelException as exp:
        logger.error(f"Chart generator skill error: {exp}")
        raise Exception("Chart generation skill not available") from exp


async def generate_chart_image(
    kernel: Kernel, token: str, query: str, headers: List[str], rows: List[List]
) -> str:
    """
    Generate a chart image and return it as base64 encoded string.

    Returns:
        Base64 encoded PNG image data
    """
    logger.info(
        f"Chart generation started for query with {len(rows)} rows and {len(headers)} columns"
    )
    logger.debug(f"Headers: {headers}")
    logger.debug(f"Sample rows: {rows[:3] if rows else 'No rows'}")

    chart_code = await _generate_chart_code(kernel, token, query, headers, rows)
    chart_uuid = _generate_unique_chart_id(query, headers, rows)

    logger.debug(f"Chart UUID generated: {chart_uuid}")

    with tempfile.TemporaryDirectory() as temp_dir:
        logger.debug(f"Using temp directory: {temp_dir}")

        data_file = os.path.join(temp_dir, "data.py")
        chart_file = os.path.join(temp_dir, "chart.py")
        output_image = os.path.join(temp_dir, f"{chart_uuid}.png")

        logger.info("Chart generation step 3: Creating data preparation code")
        data_code = _create_data_preparation_code(headers, rows)
        with open(data_file, "w") as f:
            f.write(data_code)
        logger.debug(f"Created data.py ({len(data_code)} bytes)")

        logger.info("Chart generation step 4: Creating chart execution code")
        complete_chart_code = _create_chart_execution_code(
            chart_code, chart_uuid, temp_dir
        )
        with open(chart_file, "w") as f:
            f.write(complete_chart_code)
        logger.debug(f"Created chart.py ({len(complete_chart_code)} bytes)")

        try:
            logger.info(
                "Chart generation step 5: Executing chart generation Python script"
            )
            result = _execute_chart_generation(chart_file, temp_dir)

            if result.returncode != 0:
                logger.error("Chart generation script execution failed")
                logger.error(f"stderr: {result.stderr}")
                logger.debug(f"stdout: {result.stdout}")
                raise Exception(f"Chart generation failed: {result.stderr}")

            logger.info("Chart generation script executed successfully")
            logger.debug(f"Script stdout: {result.stdout}")
            logger.debug(f"Files created in temp dir: {os.listdir(temp_dir)}")

            if not os.path.exists(output_image):
                logger.error(f"Chart image file not found at path: {output_image}")
                raise Exception("Chart image was not generated")

            logger.info("Chart generation step 6: Encoding image to base64")
            # Read image and encode as base64
            with open(output_image, "rb") as img_file:
                img_data = img_file.read()
                img_size_kb = len(img_data) / 1024
                logger.debug(f"PNG image size: {img_size_kb:.2f} KB")

                img_base64 = base64.b64encode(img_data).decode("utf-8", errors="ignore")
                base64_size_kb = len(img_base64) / 1024
                logger.debug(f"Base64 encoded size: {base64_size_kb:.2f} KB")

            logger.info(
                f"Chart image generation completed successfully: {img_size_kb:.2f}KB PNG"
            )

            return img_base64

        except subprocess.TimeoutExpired:
            logger.error("Chart generation timed out after 60 seconds")
            raise Exception("Chart generation timed out")
        except Exception as e:
            logger.exception(f"Error executing chart generation code: {e}")
            raise Exception(f"Error executing chart code: {str(e)}")
