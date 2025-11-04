import re

from pydantic import BaseModel

class Input(BaseModel):
    chart_type: str
    query: str
    headers: list[str]
    rows: list[list]


class Output(BaseModel):
    chart_code: str | None = None

def extract_python_code(response_text: str) -> str:
    """Extract Python code from the response, removing all thinking tags and content."""
    if "</think>" in response_text:
        response_text = response_text.split("</think>", 1)[1].strip()

    code = response_text.strip()
    lines = code.split("\n")
    filtered_lines = []
    for line in lines:
        stripped = line.strip()
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


if __name__ == "__main__":
    from pharia_skill.testing import DevCsi

    csi = DevCsi()

    input1 = Input(
        chart_type="bar",
        query="SELECT Region, COUNT(*) as Count FROM Customers GROUP BY Region;",
        headers=["Region", "Count"],
        rows=[["North", 25], ["South", 30], ["East", 20], ["West", 15]],
    )
    # TODO: Implement the generate_chart_code skill
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
    # TODO: Implement the generate_chart_code skill
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
    # TODO: Implement the generate_chart_code skill
    output3 = generate_chart_code(csi, input3)
    print(f"Generated Pie Chart Code:\n{output3.chart_code}\n")
