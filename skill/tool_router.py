import json

from pharia_skill import ChatParams, Csi, Message, skill
from pydantic import BaseModel

SYSTEM_PROMPT = """You are a tool router for a Text2SQL application.

Your job: Analyze the user message and context to determine which tool should be called.

AVAILABLE TOOLS:
1. generate_sql - Convert natural language question to SQL query
2. execute_sql - Execute a SQL query on the database
3. classify_chart_type - Analyze data and recommend chart type
4. generate_chart - Create a chart visualization from data

ROUTING RULES:
- If no context provided → generate_sql
- If context has "query" field but no "headers" → execute_sql
- If context has "headers" and "rows" → generate_chart
- If user explicitly asks about chart type → classify_chart_type

RESPONSE FORMAT (JSON only):
{
  "tool": "tool_name",
  "arguments": {
    "param": "value"
  }
}

PARAMETER REQUIREMENTS:
- generate_sql needs: {"question": "the user's question"}
- execute_sql needs: {"query": "the SQL query"}
- classify_chart_type needs: {"query": "SQL", "headers": [...], "rows": [...]}
- generate_chart needs: {"query": "SQL", "headers": [...], "rows": [...]}

Respond with ONLY the JSON object. No explanations.
"""


class Input(BaseModel):
    message: str
    context: dict | None = None


class Output(BaseModel):
    tool: str
    arguments: dict


@skill
def route_tool(csi: Csi, input: Input) -> Output:
    """
    Determine which tool to call based on message and context.

    Returns:
        tool: Name of tool to call
        arguments: Arguments to pass to the tool
    """
    context_parts = []
    if input.context:
        if input.context.get("query"):
            query = input.context["query"]
            context_parts.append(f"SQL query available: {query[:100]}...")

        if input.context.get("headers") and input.context.get("rows"):
            headers = input.context["headers"]
            rows = input.context["rows"]
            context_parts.append(
                f"Data available: {len(rows)} rows, columns: {headers}"
            )

    context_desc = "\n".join(context_parts) if context_parts else "No context provided"

    user_prompt = f"""Message: {input.message}

Context:
{context_desc}

Which tool should be called? Respond with JSON only.
"""

    messages = [
        Message.system(content=SYSTEM_PROMPT),
        Message.user(content=user_prompt),
    ]

    params = ChatParams(temperature=0.0, max_tokens=1024)

    response = csi.chat("qwen3-30b-a3b-thinking-2507-fp8", messages, params)

    llm_response = response.message.content

    if "</think>" in llm_response:
        llm_response = llm_response.split("</think>", 1)[1].strip()

    start = llm_response.find("{")
    if start != -1:
        brace_count = 0
        for i in range(start, len(llm_response)):
            if llm_response[i] == "{":
                brace_count += 1
            elif llm_response[i] == "}":
                brace_count -= 1
                if brace_count == 0:
                    json_str = llm_response[start : i + 1]
                    try:
                        decision = json.loads(json_str)

                        tool = decision.get("tool", "")
                        arguments = decision.get("arguments", {})

                        if tool == "generate_chart":
                            if input.context:
                                arguments["query"] = input.context.get("query", "")
                                arguments["headers"] = input.context.get("headers", [])
                                arguments["rows"] = input.context.get("rows", [])
                            else:
                                arguments.setdefault("query", "")
                                arguments.setdefault("headers", [])
                                arguments.setdefault("rows", [])
                        elif tool == "execute_sql":
                            if "query" not in arguments:
                                arguments["query"] = (
                                    input.context.get("query", "")
                                    if input.context
                                    else ""
                                )
                        elif tool == "generate_sql":
                            if "question" not in arguments:
                                arguments["question"] = input.message
                        elif tool == "classify_chart_type":
                            if input.context:
                                arguments["query"] = input.context.get("query", "")
                                arguments["headers"] = input.context.get("headers", [])
                                arguments["rows"] = input.context.get("rows", [])
                            else:
                                arguments.setdefault("query", "")
                                arguments.setdefault("headers", [])
                                arguments.setdefault("rows", [])

                        return Output(tool=tool, arguments=arguments)

                    except json.JSONDecodeError:
                        pass
    print(f"Warning: Could not parse tool decision from LLM, using fallback")
    if (
        input.context
        and input.context.get("query")
        and not input.context.get("headers")
    ):
        return Output(tool="execute_sql", arguments={"query": input.context["query"]})
    elif input.context and input.context.get("headers") and input.context.get("rows"):
        return Output(
            tool="generate_chart",
            arguments={
                "query": input.context.get("query", ""),
                "headers": input.context["headers"],
                "rows": input.context["rows"],
            },
        )
    else:
        return Output(tool="generate_sql", arguments={"question": input.message})


if __name__ == "__main__":
    from pharia_skill.testing import DevCsi

    csi = DevCsi()

    input1 = Input(message="How many customers per country?")
    output1 = route_tool(csi, input1)
    print(f"Test 1: tool={output1.tool}, args={output1.arguments}")

    input2 = Input(
        message="Execute this query",
        context={"query": "SELECT Country, COUNT(*) FROM Customers GROUP BY Country;"},
    )
    output2 = route_tool(csi, input2)
    print(f"Test 2: tool={output2.tool}, args={output2.arguments}")

    input3 = Input(
        message="Create visualization",
        context={
            "query": "SELECT Country, COUNT(*) FROM Customers GROUP BY Country;",
            "headers": ["Country", "Count"],
            "rows": [["USA", 13], ["Canada", 3]],
        },
    )
    output3 = route_tool(csi, input3)
    print(f"Test 3: tool={output3.tool}, args={output3.arguments}")
