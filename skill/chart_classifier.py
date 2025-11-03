import json

from colorama import Style
from jinja2 import Template
from pharia_skill import ChatParams, Csi, Message, skill
from pydantic import BaseModel

SYSTEM_PROMPT = """
You are an expert data visualization consultant. Your task is to analyze SQL query results and determine the most appropriate chart type for visualizing the data.

CHART TYPES AVAILABLE:
1. bar - For categorical data with counts or values (e.g., sales by region, products by category) - STATIC comparisons
2. line - For time series data or trends over time/continuous variables - showing CHANGE over time
3. pie - For proportional data with few categories (max 8-10 categories showing parts of a whole)
4. scatter - For showing correlation or relationship between two numeric variables
5. histogram - For showing distribution of a single numeric variable

ANALYSIS GUIDELINES:
1. Consider the data types (categorical vs numeric)
2. Consider the number of rows and columns
3. Consider the nature of the question being asked
4. Consider what insights the visualization should convey
5. Choose the chart type that best represents the data relationships

SPECIAL CASES:
- 3 columns with [Time/Date/Year, Category, Value]: Use LINE chart to show trends over time for each category
- Data with Year, Month, Date, or time-related columns: Strongly prefer LINE chart
- Questions asking about "change", "trend", "over time", "growth": Use LINE chart
- Simple categorical comparisons without time: Use BAR chart

RESPONSE FORMAT:
You must respond with ONLY ONE of these exact values: bar, line, pie, scatter, histogram
Do not include any explanations, just the chart type.
"""

USER_PROMPT_TEMPLATE = """
SQL Query: {{ query }}

Data Headers: {{ headers_json }}
Sample Data (first few rows): {{ sample_data_json }}
Total Rows: {{ total_rows }}

Analyze this data and determine the most appropriate chart type.

Data Analysis:
- Number of columns: {{ num_columns }}
- Column names: {{ headers_json }}
- Data types observed: Inspect the sample data to determine which columns are categorical (text) and which are numeric

KEY OBSERVATIONS:
- Look for time-related columns: Year, Month, Date, Time, Period
- Check if query contains ORDER BY time/date column (indicates trend analysis)
- If data has 3 columns [Time, Category, Value], this is a multi-series time trend → Use LINE
- If query asks about "change", "trend", "growth", "over time" → Use LINE

Based on the data structure and the query intent, what is the single best chart type for this visualization?

Respond with only one word: bar, line, pie, scatter, or histogram
"""


class Input(BaseModel):
    query: str
    headers: list[str]
    rows: list[list]


class Output(BaseModel):
    chart_type: str | None = None


@skill
def classify_chart_type(csi: Csi, input: Input) -> Output:
    sample_data = input.rows[:5] if input.rows else []
    num_columns = len(input.headers)

    # Pre-serialize complex data to avoid Jinja2 template parsing issues
    headers_json = json.dumps(input.headers)
    sample_data_json = json.dumps(sample_data)

    formatted_system_prompt = SYSTEM_PROMPT
    formatted_user_prompt = Template(USER_PROMPT_TEMPLATE).render(
        query=input.query,
        headers_json=headers_json,
        sample_data_json=sample_data_json,
        total_rows=len(input.rows),
        num_columns=num_columns,
    )

    messages = [
        Message.system(formatted_system_prompt),
        Message.user(formatted_user_prompt),
    ]

    params = ChatParams()

    try:
        response = csi.chat("qwen3-30b-a3b-thinking-2507-fp8", messages, params)
        chart_type = extract_chart_type(response.message.content.strip())

        if not chart_type or chart_type not in [
            "bar",
            "line",
            "pie",
            "scatter",
            "histogram",
        ]:
            print(
                f"Warning: Invalid or missing chart type '{chart_type}', defaulting to 'bar'"
            )
            return Output(chart_type="bar")

        return Output(chart_type=chart_type)

    except Exception as e:
        print(f"Error classifying chart type: {e}")
        return Output(chart_type="bar")


def extract_chart_type(response_text: str) -> str:
    """Extract the chart type from the response, handling thinking tags and extra text."""
    if "</think>" in response_text:
        response_text = response_text.split("</think>", 1)[1].strip()

    response_text = response_text.lower().strip()

    valid_types = ["bar", "line", "pie", "scatter", "histogram"]
    for chart_type in valid_types:
        if chart_type in response_text:
            return chart_type

    return response_text.split()[0] if response_text.split() else ""


def print_colored_prompt(prompt_type: str, content: str, color: str):
    print(f"{color}{prompt_type}:{Style.RESET_ALL}")
    print(f"{color}{content}{Style.RESET_ALL}")
    print("\n")


if __name__ == "__main__":
    from pharia_skill.testing import DevCsi

    csi = DevCsi()

    input1 = Input(
        query="SELECT Region, COUNT(*) as Count FROM Customers GROUP BY Region;",
        headers=["Region", "Count"],
        rows=[["North", 25], ["South", 30], ["East", 20], ["West", 15]],
    )
    output1 = classify_chart_type(csi, input1)
    print(f"Test 1 - Categorical counts: {output1.chart_type}")

    input2 = Input(
        query="SELECT Month, SUM(Sales) as TotalSales FROM Orders GROUP BY Month ORDER BY Month;",
        headers=["Month", "TotalSales"],
        rows=[
            ["2024-01", 10000],
            ["2024-02", 12000],
            ["2024-03", 15000],
            ["2024-04", 13000],
        ],
    )
    output2 = classify_chart_type(csi, input2)
    print(f"Test 2 - Time series: {output2.chart_type}")

    input3 = Input(
        query="SELECT Category, COUNT(*) as Count FROM Products GROUP BY Category;",
        headers=["Category", "Count"],
        rows=[
            ["Electronics", 45],
            ["Clothing", 30],
            ["Food", 15],
            ["Books", 10],
        ],
    )
    output3 = classify_chart_type(csi, input3)
    print(f"Test 3 - Proportional data: {output3.chart_type}")
