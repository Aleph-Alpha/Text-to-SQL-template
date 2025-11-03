import re

from pydantic import BaseModel



class Input(BaseModel):
    question: str
    database_schema: str | None = None


class Output(BaseModel):
    answer: str | None
    duration: float | None = None


def extract_sql_text(sql_text: str) -> str:
    sql_text_cleaned = re.sub(r"<think>(.*?)</think>", "", sql_text, flags=re.DOTALL)
    lines = [
        line.strip() for line in sql_text_cleaned.strip().split("\n") if line.strip()
    ]

    for i in range(len(lines) - 1, -1, -1):
        line = lines[i]

        if line.upper().startswith("SELECT"):
            sql_lines = [line]

            for j in range(i + 1, len(lines)):
                next_line = lines[j]
                if (
                    next_line.upper().startswith("SELECT")
                    or next_line.startswith("//")
                    or next_line.startswith("#")
                ):
                    break
                sql_lines.append(next_line)
                if next_line.endswith(";"):
                    break

            sql_query = " ".join(sql_lines).rstrip(".")
            if not sql_query.endswith(";"):
                sql_query += ";"
            return sql_query

    return sql_text_cleaned.strip()


if __name__ == "__main__":
    from pharia_skill.testing import DevCsi

    csi = DevCsi()

    input = Input(question="Total number of customers per regions?")
    # TODO: Implement the generate_sql skill
    output = generate_sql(csi, input)
    print(f"Generated SQL: {output.answer}")