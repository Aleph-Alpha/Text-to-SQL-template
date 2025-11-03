import re

from colorama import Fore, Style
from jinja2 import Template
from pharia_skill import ChatParams, Csi, IndexPath, Message, skill
from pydantic import BaseModel

NAMESPACE = "Studio"
COLLECTION = "text-to-sql-examples"
INDEX = "asym-1024"


DATABASE_SCHEMA = """
CREATE TABLE Categories (
    CategoryID    INTEGER,
    PRIMARY KEY (CategoryID),
    CategoryName  TEXT,
    Description   TEXT,
    Picture       BLOB   
);
CREATE TABLE CustomerCustomerDemo (
    CustomerID      TEXT  NOT NULL,
    CustomerTypeID  TEXT  NOT NULL,
    CONSTRAINT sqlite_autoindex_CustomerCustomerDemo_1 UNIQUE (CustomerID, CustomerTypeID),
    FOREIGN KEY (CustomerTypeID) REFERENCES CustomerDemographics (CustomerTypeID),
    FOREIGN KEY (CustomerID) REFERENCES Customers (CustomerID),
    PRIMARY KEY (CustomerID, CustomerTypeID)
);
CREATE TABLE CustomerDemographics (
    CustomerTypeID  TEXT  NOT NULL,
    PRIMARY KEY (CustomerTypeID),
    CustomerDesc    TEXT,
    CONSTRAINT sqlite_autoindex_CustomerDemographics_1 UNIQUE (CustomerTypeID)
);
CREATE TABLE Customers (
    CustomerID    TEXT,
    PRIMARY KEY (CustomerID),
    CompanyName   TEXT,
    ContactName   TEXT,
    ContactTitle  TEXT,
    Address       TEXT,
    City          TEXT,
    Region        TEXT,
    PostalCode    TEXT,
    Country       TEXT,
    Phone         TEXT,
    Fax           TEXT,
    CONSTRAINT sqlite_autoindex_Customers_1 UNIQUE (CustomerID)
);
CREATE TABLE EmployeeTerritories (
    EmployeeID   INTEGER  NOT NULL,
    TerritoryID  TEXT     NOT NULL,
    CONSTRAINT sqlite_autoindex_EmployeeTerritories_1 UNIQUE (EmployeeID, TerritoryID),
    FOREIGN KEY (TerritoryID) REFERENCES Territories (TerritoryID),
    FOREIGN KEY (EmployeeID) REFERENCES Employees (EmployeeID),
    PRIMARY KEY (EmployeeID, TerritoryID)
);
CREATE TABLE Employees (
    EmployeeID       INTEGER,
    PRIMARY KEY (EmployeeID),
    LastName         TEXT,
    FirstName        TEXT,
    Title            TEXT,
    TitleOfCourtesy  TEXT,
    BirthDate        DATE,
    HireDate         DATE,
    Address          TEXT,
    City             TEXT,
    Region           TEXT,
    PostalCode       TEXT,
    Country          TEXT,
    HomePhone        TEXT,
    Extension        TEXT,
    Photo            BLOB,
    Notes            TEXT,
    ReportsTo        INTEGER,
    PhotoPath        TEXT,
    FOREIGN KEY (ReportsTo) REFERENCES Employees (EmployeeID)
);
CREATE TABLE Order Details (
    OrderID    INTEGER  NOT NULL,
    ProductID  INTEGER  NOT NULL,
    UnitPrice  NUMERIC  NOT NULL  DEFAULT 0,
    Quantity   INTEGER  NOT NULL  DEFAULT 1,
    Discount   REAL     NOT NULL  DEFAULT 0,
    CONSTRAINT sqlite_autoindex_Order Details_1 UNIQUE (OrderID, ProductID),
    FOREIGN KEY (ProductID) REFERENCES Products (ProductID),
    FOREIGN KEY (OrderID) REFERENCES Orders (OrderID),
    PRIMARY KEY (OrderID, ProductID)
);
CREATE TABLE Orders (
    OrderID         INTEGER   NOT NULL,
    PRIMARY KEY (OrderID),
    CustomerID      TEXT,
    EmployeeID      INTEGER,
    OrderDate       DATETIME,
    RequiredDate    DATETIME,
    ShippedDate     DATETIME,
    ShipVia         INTEGER,
    Freight         NUMERIC   DEFAULT 0,
    ShipName        TEXT,
    ShipAddress     TEXT,
    ShipCity        TEXT,
    ShipRegion      TEXT,
    ShipPostalCode  TEXT,
    ShipCountry     TEXT,
    FOREIGN KEY (ShipVia) REFERENCES Shippers (ShipperID),
    FOREIGN KEY (CustomerID) REFERENCES Customers (CustomerID),
    FOREIGN KEY (EmployeeID) REFERENCES Employees (EmployeeID)
);
CREATE TABLE Products (
    ProductID        INTEGER  NOT NULL,
    PRIMARY KEY (ProductID),
    ProductName      TEXT     NOT NULL,
    SupplierID       INTEGER,
    CategoryID       INTEGER,
    QuantityPerUnit  TEXT,
    UnitPrice        NUMERIC  DEFAULT 0,
    UnitsInStock     INTEGER  DEFAULT 0,
    UnitsOnOrder     INTEGER  DEFAULT 0,
    ReorderLevel     INTEGER  DEFAULT 0,
    Discontinued     TEXT     NOT NULL  DEFAULT '0',
    FOREIGN KEY (SupplierID) REFERENCES Suppliers (SupplierID),
    FOREIGN KEY (CategoryID) REFERENCES Categories (CategoryID)
);
CREATE TABLE Regions (
    RegionID           INTEGER  NOT NULL,
    PRIMARY KEY (RegionID),
    RegionDescription  TEXT     NOT NULL
);
CREATE TABLE Shippers (
    ShipperID    INTEGER  NOT NULL,
    PRIMARY KEY (ShipperID),
    CompanyName  TEXT     NOT NULL,
    Phone        TEXT   
);
CREATE TABLE Suppliers (
    SupplierID    INTEGER  NOT NULL,
    PRIMARY KEY (SupplierID),
    CompanyName   TEXT     NOT NULL,
    ContactName   TEXT,
    ContactTitle  TEXT,
    Address       TEXT,
    City          TEXT,
    Region        TEXT,
    PostalCode    TEXT,
    Country       TEXT,
    Phone         TEXT,
    Fax           TEXT,
    HomePage      TEXT   
);
CREATE TABLE Territories (
    TerritoryID           TEXT     NOT NULL,
    PRIMARY KEY (TerritoryID),
    TerritoryDescription  TEXT     NOT NULL,
    RegionID              INTEGER  NOT NULL,
    CONSTRAINT sqlite_autoindex_Territories_1 UNIQUE (TerritoryID),
    FOREIGN KEY (RegionID) REFERENCES Regions (RegionID)
);
"""

SYSTEM_PROMPT = """
You are an expert SQL query generator. Your task is to convert natural language questions into precise SQL queries based on the provided database schema.

INSTRUCTIONS:
1. Generate syntactically correct SQL that will execute successfully
2. Use proper SQL syntax with correct table and column names from the schema
3. Handle edge cases gracefully (e.g., case-insensitive matching, NULL values)
4. Use appropriate JOIN operations when querying multiple tables
5. Apply proper aggregation functions (COUNT, SUM, AVG, etc.) when needed
6. Use LIKE operator with wildcards (%) for partial text matching
7. If the question cannot be answered with the given schema, return: {{ unable_response }}

You can think through the problem, but make sure to end your response with the final SQL query.
"""

USER_PROMPT_TEMPLATE = """
The following is the database schema:
{{ database_schema }}

These are some examples of questions and their corresponding SQL queries:
{% for example in few_shot_examples %}
Example {{ loop.index }}:
    Question: {{ example.question }}
    SQL: {{ example.sql_query }}
{% endfor %}

TASK:
Convert the following natural language question into a SQL query using the provided database schema.

QUESTION: {{ question }}
"""


class Input(BaseModel):
    question: str
    database_schema: str | None = None


class Output(BaseModel):
    answer: str | None
    duration: float | None = None


class FewShotExample(BaseModel):
    question: str
    sql_query: str


@skill
def custom_rag(csi: Csi, input: Input) -> Output:
    index = IndexPath(
        namespace=NAMESPACE,
        collection=COLLECTION,
        index=INDEX,
    )

    few_shot_examples = []
    if documents := csi.search(index, input.question, 10):
        documents_metadata = [
            csi.document_metadata(result.document_path) for result in documents
        ]

        few_shot_examples = [
            FewShotExample(
                question=document.content,
                sql_query=document_metadata.get("query", ""),
            )
            for document, document_metadata in zip(documents, documents_metadata)
            if document_metadata.get("query")
        ]

    unable_response = "None"
    formatted_system_prompt = Template(SYSTEM_PROMPT).render(
        unable_response=unable_response
    )
    formatted_user_prompt = Template(USER_PROMPT_TEMPLATE).render(
        database_schema=(
            input.database_schema if input.database_schema else DATABASE_SCHEMA
        ),
        few_shot_examples=few_shot_examples,
        question=input.question,
    )

    print_colored_prompt("SYSTEM PROMPT", formatted_system_prompt, Fore.GREEN)
    print_colored_prompt("USER PROMPT", formatted_user_prompt, Fore.BLUE)

    messages = [
        Message.system(formatted_system_prompt),
        Message.user(formatted_user_prompt),
    ]

    params = ChatParams()

    try:
        response = csi.chat("qwen3-30b-a3b-thinking-2507-fp8", messages, params)
        sql_output = extract_sql_text(response.message.content.strip())

        print_colored_prompt(
            "ASSISTANT ANSWER", response.message.content.strip(), Fore.YELLOW
        )

        if sql_output == unable_response or not sql_output:
            return Output(answer=None)

        return Output(answer=sql_output)

    except Exception as e:
        print(f"Error generating SQL: {e}")
        return Output(answer=None)


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


def print_colored_prompt(prompt_type: str, content: str, color: str):
    print(f"{color}{prompt_type}:{Style.RESET_ALL}")
    print(f"{color}{content}{Style.RESET_ALL}")
    print("\n")


if __name__ == "__main__":
    from pharia_skill.testing import DevCsi

    csi = DevCsi()

    input = Input(question="Total number of customers per regions?")
    output = custom_rag(csi, input)
    print(f"Generated SQL: {output.answer}")
