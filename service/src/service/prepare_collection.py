import json
import logging
import os
import random
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from pharia_data_sdk.connectors import (
    CollectionPath,
    DocumentContents,
    DocumentIndexClient,
    DocumentPath,
    IndexConfiguration,
    IndexPath,
    SemanticEmbed,
)
from models import SpiderExample
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()

PHARIA_AI_TOKEN = os.getenv("PHARIA_AI_TOKEN")
DOCUMENT_INDEX_CLIENT_URL = os.getenv("DOCUMENT_INDEX_CLIENT_URL")
DOCUMENT_INDEX_NAMESPACE = os.getenv("DOCUMENT_INDEX_NAMESPACE")
DOCUMENT_INDEX_COLLECTION = os.getenv("DOCUMENT_INDEX_COLLECTION")

document_index_client = DocumentIndexClient(
    token=PHARIA_AI_TOKEN, base_url=DOCUMENT_INDEX_CLIENT_URL
)


def validate_environment():
    """
    Validates that all required environment variables are set.

    Raises:
        ValueError: If any required environment variable is missing.
    """
    missing_vars = []
    if not PHARIA_AI_TOKEN:
        missing_vars.append("PHARIA_AI_TOKEN")
    if not DOCUMENT_INDEX_CLIENT_URL:
        missing_vars.append("DOCUMENT_INDEX_CLIENT_URL")
    if not DOCUMENT_INDEX_NAMESPACE:
        missing_vars.append("DOCUMENT_INDEX_NAMESPACE")
    if not DOCUMENT_INDEX_COLLECTION:
        missing_vars.append("DOCUMENT_INDEX_COLLECTION")

    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )


def setup_collection() -> None:
    """
    Setup the collection and index for the document index.
    """
    vector_size = 1024
    model_name = "luminous-base"
    embedding_strategy = SemanticEmbed(
        strategy="semantic_embed",
        model_name=model_name,
        representation="asymmetric",
    )
    index_name = f"asym-{vector_size}"
    try:
        logger.info("Starting collection setup")

        collection_path = CollectionPath(
            namespace=DOCUMENT_INDEX_NAMESPACE, collection=DOCUMENT_INDEX_COLLECTION
        )
        logger.info(
            f"Using collection path: {collection_path.namespace}/{collection_path.collection}"
        )

        index_path = IndexPath(namespace=DOCUMENT_INDEX_NAMESPACE, index=index_name)
        logger.info(f"Using index path: {index_path.namespace}/{index_path.index}")

        logger.info(
            f"Configuring index with chunk size {vector_size} and {model_name} asymmetric embedding"
        )
        index_configuration = IndexConfiguration(
            chunk_size=vector_size,
            chunk_overlap=0,
            embedding=embedding_strategy,
        )

        logger.info(
            f"Creating collection: {collection_path.namespace}/{collection_path.collection}"
        )
        document_index_client.create_collection(collection_path)

        logger.info(f"Creating index: {index_path.namespace}/{index_path.index}")
        document_index_client.create_index(index_path, index_configuration)

        logger.info(f"Assigning index '{index_name}' to collection")
        document_index_client.assign_index_to_collection(collection_path, index_name)

        logger.info("Collection setup completed successfully")
    except Exception as e:
        logger.error(f"Error during collection setup: {e}")
        raise


def get_examples_from_json() -> list[SpiderExample]:
    random.seed(1234)
    parent_dir = Path(__file__).parent.parent
    path_to_data = os.path.join(parent_dir, "data")

    with open(os.path.join(path_to_data, "spider_data", "train_spider.json"), "r") as f:
        train_examples = json.load(f)

    if len(train_examples) > 1000:
        sampled_examples = random.sample(train_examples, 1000)
    else:
        sampled_examples = train_examples
        logger.warning(
            f"Dataset has only {len(train_examples)} examples, using all of them"
        )

    return [SpiderExample.model_validate(ex) for ex in sampled_examples]


if __name__ == "__main__":
    validate_environment()
    # We only need to run this once to setup the collection and index.
    try:
        logger.info("Starting document indexing setup")
        setup_collection()
        logger.info("Document indexing setup completed successfully")
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        raise

    examples = get_examples_from_json()

    for example in tqdm(examples, desc="Indexing documents"):
        document_name = str(uuid4())
        document_path = DocumentPath(
            collection_path=CollectionPath(
                namespace=DOCUMENT_INDEX_NAMESPACE, collection=DOCUMENT_INDEX_COLLECTION
            ),
            document_name=document_name,
        )
        document_index_client.add_document(
            document_path,
            contents=DocumentContents._from_modalities_json(
                {
                    "contents": [{"modality": "text", "text": example.question}],
                    "metadata": {
                        "query": example.query,
                        "db_id": example.db_id,
                    },
                }
            ),
        )
