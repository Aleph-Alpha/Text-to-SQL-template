import json
import re

from colorama import Style
from pharia_skill import ChatParams, Csi, Message, skill
from pydantic import BaseModel


def get_system_prompt(chart_type: str) -> str:
    """Generate system prompt based on chart type without using Jinja2."""

    base_prompt = """You are an expert Python data visualization specialist. Your task is to generate Python code that creates a {chart_type} chart for the given SQL query results.

CRITICAL INSTRUCTIONS:
1. Generate ONLY executable Python code - no explanations, no markdown formatting
2. Use matplotlib and pandas for visualization
3. The DataFrame 'df' is already created and cleaned (null values removed, strings converted)
4. Create a {chart_type} chart appropriate for the data structure
5. Always include proper titles, labels, and formatting
6. Use plt.tight_layout() to ensure proper spacing
7. Do NOT include plt.savefig(), plt.close(), or plt.show() - these will be handled automatically
8. Handle data safely - check if DataFrame is not empty before plotting
9. The code should end after creating the plot - no display or save commands

REQUIRED IMPORTS (always include these):
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

CHART-SPECIFIC GUIDELINES:
{guidelines}

RESPONSE FORMAT:
- Return ONLY the Python code
- No explanations or comments except for code comments
- Code should be ready to execute
- Include basic error handling for empty data
"""

    guidelines_map = {
        "bar": """ALGORITHM for bar charts:

1. IDENTIFY columns:
   - VALUE: numeric (Sales, Count, Amount, etc.)
   - CATEGORY: text/categorical (Region, Product, Category, etc.)
   - TIME (if present): Year, Month, etc.

2. CHOOSE strategy:
   - 2 cols [Category, Value]: Simple bar chart
   - 3+ cols: Aggregate or group data, or use grouped/stacked bars

3. TEMPLATES:
   Simple (2 columns):
   ```python
   df.plot.bar(x='Category', y='Value', color='skyblue', edgecolor='black')
   ```
   
   Horizontal (many categories >10):
   ```python
   df.plot.barh(x='Category', y='Value', color='skyblue', edgecolor='black')
   ```
   
   Grouped bars (3 cols - show categories side by side per time period):
   ```python
   pivot = df.pivot(index='Time', columns='Category', values='Value')
   pivot.plot.bar(figsize=(12, 6), width=0.8)
   plt.legend(title='Category', bbox_to_anchor=(1.05, 1))
   ```

4. RULES:
   - ALWAYS: x = categorical, y = numeric (never swap!)
   - Rotate labels if >8 categories: plt.xticks(rotation=45, ha='right')
   - Use figsize=(12, 6) for many categories or grouped bars""",
        "line": """ALGORITHM for line charts:

1. IDENTIFY columns (inspect headers and sample data):
   - VALUE: numeric column (Sales, Count, Total, Amount, Revenue, etc.) - what to plot on y-axis
   - TIME: Year, Month, Date, Period, Quarter, Time - what to plot on x-axis
   - CATEGORY: text columns for grouping (CategoryName, Region, Product, Type, etc.)

2. CHOOSE strategy based on column count:
   - 2 cols [Time, Value]: df.plot.line(x='Time', y='Value', marker='o')
   - 3 cols [Time, Category, Value]: Iterate through categories
   - 4+ cols [Time, Cat1, Cat2, Value]: Pick PRIMARY category (fewest unique values, usually 3-15)

3. MULTI-SERIES template (3+ columns):
   ```python
   plt.figure(figsize=(12, 7))
   for cat_value in df['CategoryColumn'].unique():
       subset = df[df['CategoryColumn'] == cat_value]
       plt.plot(subset['TimeColumn'], subset['ValueColumn'], 
                marker='o', label=cat_value, linewidth=2, markersize=6)
   plt.legend(title='Category', bbox_to_anchor=(1.05, 1), loc='upper left')
   plt.grid(True, alpha=0.3)
   ```

4. ESSENTIAL elements:
   - marker='o' for data points
   - linewidth=2 for visibility
   - plt.grid(True, alpha=0.3) for readability
   - Legend with title for multi-series
   - Larger figure: (12, 7) for multi-line, (10, 6) for simple

FORBIDDEN: Do NOT use 'hue', 'by', 'color' as parameters in df.plot.line()""",
        "pie": """- Use plt.pie() or df.plot.pie()
- Include autopct to show percentages
- Add legend if categories are not clearly labeled
- Only use for data with less than 10 categories
- Use the first column as labels and second column as values""",
        "scatter": """- Use plt.scatter() or df.plot.scatter()
- Set appropriate marker size and transparency (alpha)
- Add trend line if correlation is being analyzed
- Use first column as x-axis and second column as y-axis""",
        "histogram": """- Use plt.hist() or df.plot.hist()
- Choose appropriate number of bins (default is usually good)
- Add vertical lines for mean/median if insightful
- Use the numeric column for the distribution""",
    }

    guidelines = guidelines_map.get(
        chart_type, "- Create an appropriate visualization for the data"
    )

    return base_prompt.format(chart_type=chart_type, guidelines=guidelines)


USER_PROMPT_TEMPLATE = """SQL Query: {query}

Chart Type: {chart_type}

Data Headers: {headers_json}
Sample Data (first few rows): {sample_data_json}
Total Rows: {total_rows}

Generate Python code to create a {chart_type} chart for this data.

IMPORTANT: 
- The DataFrame 'df' is already loaded and cleaned
- Always check if the DataFrame is empty before plotting
- End your code with plt.tight_layout() ONLY
- Do NOT include plt.show(), plt.savefig(), or plt.close()

Column Information:
- Available columns: {headers_json}
- Number of columns: {num_headers}

CRITICAL Column Mapping for {chart_type} charts:
- Number of columns: {num_headers}
- Available columns: {headers_json}

PATTERN RECOGNITION FOR MULTI-DIMENSIONAL DATA:

Step 1: IDENTIFY COLUMN TYPES by inspecting headers AND sample data:
  a) VALUE column (what to measure):
     - Usually last column or has keywords: Sales, Count, Total, Sum, Avg, Amount, Revenue
     - Always numeric
  
  b) TIME column (x-axis for trends):
     - Column names: Year, Month, Date, Period, Time, Quarter
     - Often first column in time series queries
     - Can be numeric (2012, 2013) or text ('2012', '01', 'Jan')
  
  c) CATEGORY/GROUPING columns (for multiple lines/series):
     - Text columns: CategoryName, Region, Product, CustomerType, etc.
     - Used to split data into multiple series
     - Each unique value becomes a separate line/bar/series

Step 2: VISUALIZATION STRATEGY based on number of columns:

2 columns [X, Value]:
  → Simple plot: df.plot.bar() or df.plot.line()

3 columns [Time, Category, Value]:
  → Multi-series: Loop through categories, plot each
  ```
  for cat in df['Category'].unique():
      data = df[df['Category'] == cat]
      plt.plot(data['Time'], data['Value'], marker='o', label=cat)
  plt.legend()
  ```

4+ columns [Time, Cat1, Cat2, ..., Value]:
  → Choose PRIMARY grouping column (usually the one with fewer unique values, 3-10 categories)
  → If multiple category columns, pick ONE for grouping (most meaningful based on query)
  → Can also aggregate: df.groupby(['Time', 'PrimaryCategory'])['Value'].sum()
  ```
  # Group by time and primary category
  grouped = df.groupby(['Time', 'PrimaryCategory'])['Value'].sum().reset_index()
  for cat in grouped['PrimaryCategory'].unique():
      data = grouped[grouped['PrimaryCategory'] == cat]
      plt.plot(data['Time'], data['Value'], marker='o', label=cat)
  plt.legend()
  ```

FORBIDDEN:
- Do NOT use 'hue', 'by', or other unsupported parameters
- Do NOT use df.plot.line() for multi-series data
- Do NOT plot without identifying column types first

Column names to use: {headers_json}

Example structures:

For 2-column {chart_type} chart:
```python
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

if df.empty:
    print("No data available for plotting")
    exit()

plt.figure(figsize=(10, 6))
df.plot.bar(x='Country', y='COUNT(*)', color='skyblue', edgecolor='black')
plt.title('Chart Title')
plt.xlabel('X Label')
plt.ylabel('Y Label')
plt.tight_layout()
```

For MULTI-DIMENSIONAL line chart (3+ columns):
```python
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

if df.empty:
    print("No data available for plotting")
    exit()

# STEP 1: Identify column types from headers: {headers_json}
# Example for ['Year', 'CategoryName', 'TotalSales']:
#   - Time column: 'Year' (numeric, time-related name)
#   - Category column: 'CategoryName' (text, for grouping)
#   - Value column: 'TotalSales' (numeric, what to measure)

# STEP 2: Create multi-series line chart
plt.figure(figsize=(12, 7))

# Plot each category as a separate colored line
for category in df['CategoryName'].unique():
    category_data = df[df['CategoryName'] == category]
    plt.plot(category_data['Year'], category_data['TotalSales'], 
             marker='o', label=category, linewidth=2, markersize=6)

plt.title('Sales Trend by Category Over Years', fontsize=14, fontweight='bold')
plt.xlabel('Year', fontsize=12)
plt.ylabel('Total Sales', fontsize=12)
plt.legend(title='Category', bbox_to_anchor=(1.05, 1), loc='upper left', frameon=True, shadow=True)
plt.grid(True, alpha=0.3, linestyle='--')
plt.tight_layout()
```

For 4+ columns, pick the MOST IMPORTANT category column (check query context):
```python
# Example: ['Year', 'Region', 'ProductCategory', 'TotalSales']
# If query focuses on category trends, group by CategoryName
# If too many unique values (>15), consider aggregating or showing top N

grouped = df.groupby(['Year', 'ProductCategory'])['TotalSales'].sum().reset_index()
for cat in grouped['ProductCategory'].unique():
    data = grouped[grouped['ProductCategory'] == cat]
    plt.plot(data['Year'], data['TotalSales'], marker='o', label=cat, linewidth=2)
```

CRITICAL: Always identify columns before plotting! Never guess!
```
"""


class Input(BaseModel):
    chart_type: str
    query: str
    headers: list[str]
    rows: list[list]


class Output(BaseModel):
    chart_code: str | None = None


@skill
def generate_chart_code(csi: Csi, input: Input) -> Output:
    sample_data = input.rows[:5] if input.rows else []

    # Use Python function instead of Jinja2 to avoid unicode-escape errors
    formatted_system_prompt = get_system_prompt(input.chart_type)

    headers_json = json.dumps(input.headers)
    sample_data_json = json.dumps(sample_data)

    formatted_user_prompt = USER_PROMPT_TEMPLATE.format(
        chart_type=input.chart_type,
        query=input.query,
        headers_json=headers_json,
        sample_data_json=sample_data_json,
        total_rows=len(input.rows),
        num_headers=len(input.headers),
    )

    messages = [
        Message.system(formatted_system_prompt),
        Message.user(formatted_user_prompt),
    ]

    params = ChatParams()

    try:
        response = csi.chat("qwen3-30b-a3b-thinking-2507-fp8", messages, params)
        chart_code = extract_python_code(response.message.content.strip())

        if not chart_code:
            return Output(chart_code=None)

        return Output(chart_code=chart_code)

    except Exception as e:
        print(f"Error generating chart code: {e}")
        return Output(chart_code=None)


def extract_python_code(response_text: str) -> str:
    """Extract Python code from the response, removing all thinking tags and content."""
    if "</think>" in response_text:
        response_text = response_text.split("</think>", 1)[1].strip()

    code = response_text.strip()
    lines = code.split("\n")
    filtered_lines = []
    for line in lines:
        stripped = line.strip()
        # Skip lines with unsupported commands
        if (
            not stripped.startswith("plt.show()")
            and not stripped.startswith("plt.savefig(")
            and not stripped.startswith("plt.close()")
        ):

            if "hue=" in line:
                line = re.sub(r",?\s*hue\s*=\s*['\"]?\w+['\"]?", "", line)
            if "by=" in line and ".plot." in line:
                line = re.sub(r",?\s*by\s*=\s*['\"]?\w+['\"]?", "", line)
            # Remove hardcoded color in loop-based plots (let matplotlib use default color cycle)
            if "for " in code and "plt.plot(" in line and "color=" in line:
                line = re.sub(r",?\s*color\s*=\s*['\"][^'\"]+['\"]", "", line)

            filtered_lines.append(line)

    return "\n".join(filtered_lines)


def print_colored_prompt(prompt_type: str, content: str, color: str):
    print(f"{color}{prompt_type}:{Style.RESET_ALL}")
    print(f"{color}{content}{Style.RESET_ALL}")
    print("\n")


if __name__ == "__main__":
    from pharia_skill.testing import DevCsi

    csi = DevCsi()

    input1 = Input(
        chart_type="bar",
        query="SELECT Region, COUNT(*) as Count FROM Customers GROUP BY Region;",
        headers=["Region", "Count"],
        rows=[["North", 25], ["South", 30], ["East", 20], ["West", 15]],
    )
    output1 = generate_chart_code(csi, input1)
    print(f"Generated Bar Chart Code:\n{output1.chart_code}\n")

    input2 = Input(
        chart_type="line",
        query="SELECT Month, SUM(Sales) as TotalSales FROM Orders GROUP BY Month;",
        headers=["Month", "TotalSales"],
        rows=[
            ["2024-01", 10000],
            ["2024-02", 12000],
            ["2024-03", 15000],
            ["2024-04", 13000],
        ],
    )
    output2 = generate_chart_code(csi, input2)
    print(f"Generated Line Chart Code:\n{output2.chart_code}\n")

    input3 = Input(
        chart_type="pie",
        query="SELECT Category, COUNT(*) as Count FROM Products GROUP BY Category;",
        headers=["Category", "Count"],
        rows=[
            ["Electronics", 45],
            ["Clothing", 30],
            ["Food", 15],
            ["Books", 10],
        ],
    )
    output3 = generate_chart_code(csi, input3)
    print(f"Generated Pie Chart Code:\n{output3.chart_code}\n")
