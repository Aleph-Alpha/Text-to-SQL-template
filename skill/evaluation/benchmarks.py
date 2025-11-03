import os
from uuid import uuid4

from dotenv import load_dotenv
from evaluation.logic import SQLAggregationLogic, SQLEvaluationLogic, SQLGenerationTask
from pharia_studio_sdk.connectors import StudioClient
from pharia_studio_sdk.evaluation import StudioBenchmarkRepository

load_dotenv()

PHARIA_AI_TOKEN = os.getenv("PHARIA_AI_TOKEN")

PHARIA_STUDIO_PROJECT_NAME = os.getenv("PHARIA_STUDIO_PROJECT_NAME")
PHARIA_STUDIO_ADDRESS = os.getenv("PHARIA_STUDIO_ADDRESS")

PHARIA_STUDIO_EVALUATION_SET_ID = os.getenv("PHARIA_STUDIO_EVALUATION_SET_ID")
PHARIA_STUDIO_BENCHMARK_ID = os.getenv("PHARIA_STUDIO_BENCHMARK_ID")

studio_client = StudioClient(
    project=PHARIA_STUDIO_PROJECT_NAME,
    studio_url=PHARIA_STUDIO_ADDRESS,
    auth_token=PHARIA_AI_TOKEN,
)

benchmark_repository = StudioBenchmarkRepository(studio_client=studio_client)


def create_benchmark():
    benchmark = benchmark_repository.create_benchmark(
        dataset_id=PHARIA_STUDIO_EVALUATION_SET_ID,
        eval_logic=SQLEvaluationLogic(),
        aggregation_logic=SQLAggregationLogic(),
        name="Text-to-SQL-benchmark",
        description="This benchmark evaluates the Text-to-SQL model.",
    )

    print(benchmark.id)


def run_benchmark():
    benchmark = benchmark_repository.get_benchmark(
        benchmark_id=PHARIA_STUDIO_BENCHMARK_ID,
        eval_logic=SQLEvaluationLogic(),
        aggregation_logic=SQLAggregationLogic(),
    )

    benchmark_execution_id = benchmark.execute(
        task=SQLGenerationTask(),
        name=str(uuid4()),
    )

    print(benchmark_execution_id)


if __name__ == "__main__":
    # create_benchmark()
    run_benchmark()
