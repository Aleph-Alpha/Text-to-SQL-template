import json
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel
from models import ExpectedOutput
from pharia_studio_sdk.connectors import StudioClient
from pharia_studio_sdk.evaluation import Example, StudioDatasetRepository

class Input(BaseModel):
    question: str
    database_schema: str | None = None
    
load_dotenv()
PHARIA_STUDIO_PROJECT_NAME = os.getenv("PHARIA_STUDIO_PROJECT_NAME")


def get_database_schema(db_id: str) -> str:
    path_to_database_schema = Path(__file__).parent / "data"
    with open(path_to_database_schema / f"{db_id}.sql", "r") as f:
        database_schema = f.read()
    return database_schema


if __name__ == "__main__":
    studio_client = StudioClient(
        project=PHARIA_STUDIO_PROJECT_NAME,
        studio_url=os.getenv("PHARIA_STUDIO_ADDRESS"),
        auth_token=os.getenv("PHARIA_AI_TOKEN"),
        create_project=True,
    )

    studio_dataset_repo = StudioDatasetRepository(studio_client=studio_client)
    path_to_test_set = Path(__file__).parent / "data" / "test_split.json"

    with open(path_to_test_set, "r") as f:
        test_set = json.load(f)

    examples = [
        Example(
            input=Input(
                question=example["question"],
                database_schema=get_database_schema(example["db_id"]),
            ),
            expected_output=ExpectedOutput(answer=example["query"]),
        )
        for example in test_set
    ]

    studio_dataset = studio_dataset_repo.create_dataset(
        examples=examples, dataset_name="Spider-test-set"
    )

    print(f"Dataset created with id {studio_dataset.id}")
