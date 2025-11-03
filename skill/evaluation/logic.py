import logging
import os
import time
from statistics import mean
from typing import Iterable

from evaluation.models import ExpectedOutput, SQLAggregatedEvaluation, SQLEvaluation
from pharia_inference_sdk.core import NoOpTracer, Task, TaskSpan
from pharia_studio_sdk.evaluation import (
    AggregationLogic,
    Example,
    SingleOutputEvaluationLogic,
)
from pharia_skill import ChatParams, Message
from pharia_skill.testing import DevCsi
from qa import Input, Output, custom_rag

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

PHARIA_STUDIO_PROJECT_NAME = os.getenv("PHARIA_STUDIO_PROJECT_NAME")


class SQLGenerationTask(Task[Input, Output]):
    def __init__(self) -> None:
        self.dev_csi = DevCsi(project=PHARIA_STUDIO_PROJECT_NAME)

    def do_run(self, input: Input, task_span: TaskSpan) -> Output:
        start_time = time.time()
        output = custom_rag(self.dev_csi, input)
        duration = time.time() - start_time

        return Output(answer=output.answer, duration=duration)


class SQLEvaluationLogic(
    SingleOutputEvaluationLogic[
        Input,
        Output,
        ExpectedOutput,
        SQLEvaluation,
    ]
):
    def __init__(self) -> None:
        self.csi = DevCsi(project=PHARIA_STUDIO_PROJECT_NAME)
        self.evaluation_model = "llama-3.3-70b-instruct"
        self.system_prompt = """
        You are a SQL expert tasked with evaluating whether a generated SQL query is logically equivalent 
        to a reference (expected) SQL query. Both queries should return the same results when executed 
        against the provided database schema.

        You must base your evaluation on:
        - The **core intent** of the query (what it's trying to retrieve or calculate)
        - The **tables** being queried
        - The **columns** being selected
        - The **WHERE clauses** and filtering conditions
        - The **JOIN operations** and their logic
        - The **GROUP BY, ORDER BY, and HAVING clauses**
        - The **aggregate functions** used (COUNT, SUM, AVG, etc.)

        Consider queries equivalent if:
        - They retrieve the same data even with different SQL syntax approaches
        - Column aliases differ but the underlying data is the same
        - JOIN syntax varies (INNER JOIN vs WHERE conditions) but produces same results
        - Subqueries vs JOINs that achieve the same logical result
        - Different but equivalent WHERE conditions (e.g., `status = 'active'` vs `status IN ('active')`)

        Consider queries NOT equivalent if:
        - They query different tables or miss required tables
        - They have different filtering logic that would change results
        - They use different aggregate functions or grouping logic
        - One has a critical WHERE clause that the other lacks
        - The generated query has syntax errors or is invalid SQL

        Reply only with "True" or "False".

        ### Examples:

        1.
        Question: How many customers are there in each country?
        Generated Query: SELECT Country, COUNT(*) FROM Customers GROUP BY Country
        Expected Query: SELECT Country, COUNT(CustomerID) as customer_count FROM Customers GROUP BY Country ORDER BY Country
        Output: "True" (same logical result despite different COUNT and missing ORDER BY)

        2.
        Question: List all products with their category names
        Generated Query: SELECT ProductName FROM Products
        Expected Query: SELECT p.ProductName, c.CategoryName FROM Products p JOIN Categories c ON p.CategoryID = c.CategoryID
        Output: "False" (missing category information and JOIN)
        """

        self.user_prompt = """
        Database Schema:
        {schema}
        
        Question: {question}

        Generated Query:
        {answer}

        Expected Query:
        {expected_query}
        """

    def do_evaluate_single_output(
        self,
        example: Example[Input, ExpectedOutput],
        output: ExpectedOutput,
    ) -> SQLEvaluation:
        """
        Main evaluation method that determines if the generated SQL is correct.
        """

        formatted_user_prompt = self.user_prompt.format(
            schema=example.input.database_schema,
            question=example.input.question,
            answer=output.answer,
            expected_query=example.expected_output.answer,
        )

        try:
            messages = [
                Message.system(self.system_prompt),
                Message.user(formatted_user_prompt),
                Message.assistant("Output:"),
            ]
            params = ChatParams(max_tokens=10)
            response = self.csi.chat(self.evaluation_model, messages, params)
            return SQLEvaluation(
                query_is_correct="true" in response.message.content.lower(),
                duration=output.duration,
            )
        except Exception as e:
            logger.error(f"Error in SQL correctness evaluation: {e}")
            return SQLEvaluation(
                query_is_correct=False,
                duration=output.duration,
            )


class SQLAggregationLogic(AggregationLogic[SQLEvaluation, SQLAggregatedEvaluation]):
    def aggregate(
        self, evaluations: Iterable[SQLEvaluation]
    ) -> SQLAggregatedEvaluation:
        evaluation_list = list(evaluations)
        if not evaluation_list:
            return SQLAggregatedEvaluation(
                correct_percentage=0.0,
                mean_duration=0.0,
            )

        correct_count = sum(e.query_is_correct for e in evaluation_list)
        total_count = len(evaluation_list)

        return SQLAggregatedEvaluation(
            correct_percentage=round((correct_count / total_count) * 100, 2),
            mean_duration=round(mean(e.duration for e in evaluation_list), 2),
        )


if __name__ == "__main__":
    task = SQLGenerationTask()
    evaluation_logic = SQLEvaluationLogic()
    aggregation_logic = SQLAggregationLogic()

    sample_schema = """
        CREATE TABLE concert (
        concert_ID    INT,
        PRIMARY KEY (concert_ID),
        concert_Name  TEXT,
        Theme         TEXT,
        Stadium_ID    TEXT,
        Year          TEXT,
        CONSTRAINT sqlite_autoindex_concert_1 UNIQUE (concert_ID),
        FOREIGN KEY (Stadium_ID) REFERENCES stadium (Stadium_ID)
        );
        CREATE TABLE singer (
            Singer_ID          INT,
            PRIMARY KEY (Singer_ID),
            Name               TEXT,
            Country            TEXT,
            Song_Name          TEXT,
            Song_release_year  TEXT,
            Age                INT,
            Is_male            bool,
            CONSTRAINT sqlite_autoindex_singer_1 UNIQUE (Singer_ID)
        );
        CREATE TABLE singer_in_concert (
            concert_ID  INT,
            Singer_ID   TEXT,
            CONSTRAINT sqlite_autoindex_singer_in_concert_1 UNIQUE (concert_ID, Singer_ID),
            FOREIGN KEY (Singer_ID) REFERENCES singer (Singer_ID),
            FOREIGN KEY (concert_ID) REFERENCES concert (concert_ID),
            PRIMARY KEY (concert_ID, Singer_ID)
        );
        CREATE TABLE stadium (
            Stadium_ID  INT,
            PRIMARY KEY (Stadium_ID),
            Location    TEXT,
            Name        TEXT,
            Capacity    INT,
            Highest     INT,
            Lowest      INT,
            Average     INT,
            CONSTRAINT sqlite_autoindex_stadium_1 UNIQUE (Stadium_ID)
        );
    """

    test_input_1 = Input(
        question="How many singers do we have?", database_schema=sample_schema
    )

    expected_output_1 = ExpectedOutput(answer="SELECT count(*) FROM singer")

    # Test case 2
    test_input_2 = Input(
        question="Show name, country, age for all singers ordered by age from the oldest to the youngest.",
        database_schema=sample_schema,
    )

    expected_output_2 = ExpectedOutput(
        answer="SELECT name ,  country ,  age FROM singer ORDER BY age DESC"
    )

    output_1 = task.run(test_input_1, NoOpTracer())
    output_2 = task.run(test_input_2, NoOpTracer())

    evaluation_1 = evaluation_logic.do_evaluate_single_output(
        example=Example(input=test_input_1, expected_output=expected_output_1),
        output=output_1,
    )

    evaluation_2 = evaluation_logic.do_evaluate_single_output(
        example=Example(input=test_input_2, expected_output=expected_output_2),
        output=output_2,
    )

    print("Evaluation 1:", evaluation_1)
    print("Evaluation 2:", evaluation_2)

    # Aggregate results
    aggregated_evaluation = aggregation_logic.aggregate([evaluation_1, evaluation_2])
    print("Aggregated Evaluation:", aggregated_evaluation)
