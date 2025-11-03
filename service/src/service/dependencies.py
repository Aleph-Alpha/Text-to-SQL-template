import os
from functools import lru_cache

from fastapi import Header, HTTPException, Request

from service.db_service import SQLiteDatabase
from service.kernel import Kernel
from service.logging_config import logger
from service.settings import Settings


@lru_cache
def with_settings() -> Settings:
    from dotenv import load_dotenv

    load_dotenv(verbose=True)

    # mypy complains about missing named arguments (required attributes without a default)
    loaded_settings = Settings()  # type: ignore
    logger.info(f"Settings loaded: {loaded_settings}")
    return loaded_settings


def get_token(authorization: str = Header(...)) -> str:
    # this enables to run the service locally during development
    if authorization.startswith("Bearer "):
        token = authorization[len("Bearer ") :]
        logger.debug("Token extracted from Authorization header")
        return token
    elif (token := os.environ.get("PHARIA_AI_TOKEN")) is not None:
        logger.debug("Token retrieved from PHARIA_AI_TOKEN environment variable")
        return token
    logger.warning("Invalid authorization header received")
    raise HTTPException(status_code=400, detail="Invalid authorization header")


def with_kernel(request: Request) -> Kernel:
    return request.state.kernel


def with_database(request: Request) -> SQLiteDatabase:
    return request.state.database
