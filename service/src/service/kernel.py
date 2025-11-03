from typing import NamedTuple, Protocol

import httpx
from httpx import Timeout

from service.logging_config import logger

Json = dict | list | bool | float | int | str | None


class Skill(NamedTuple):
    namespace: str
    name: str

    def as_str(self) -> str:
        return f"{self.namespace}/{self.name}"


class KernelException(Exception):
    def __init__(self, status_code: int, msg: str):
        self.status_code = status_code
        super().__init__(msg)


class Kernel(Protocol):
    async def run(self, skill: Skill, token: str, input: Json) -> Json: ...


class HttpKernel(Kernel):
    """Execute skills in the Kernel.

    Cache connections to the Kernel across skill executions.
    """

    def __init__(self, url: str) -> None:
        self.url = url
        timeout = Timeout(read=120, connect=10, write=10, pool=10)
        self.session = httpx.AsyncClient(timeout=timeout)
        logger.info(f"HttpKernel initialized with URL: {url}")

    async def run(self, skill: Skill, token: str, input: Json) -> Json:
        url = f"{self.url}v1/skills/{skill.namespace}/{skill.name}/run"

        logger.debug(f"Calling skill: {skill.as_str()}")
        logger.debug(
            f"Skill input keys: {list(input.keys()) if isinstance(input, dict) else type(input)}"
        )

        response = await self.session.post(
            url, json=input, headers={"Authorization": f"Bearer {token}"}
        )

        if response.status_code >= 400:
            logger.error(
                f"Skill execution failed: {skill.as_str()} - Status {response.status_code}"
            )
            logger.debug(f"Error response: {response.text[:500]}")
            raise KernelException(response.status_code, response.text)

        logger.info(f"Skill executed successfully: {skill.as_str()}")
        return response.json()

    async def shutdown(self):
        logger.info("Shutting down HttpKernel session")
        await self.session.aclose()
        logger.debug("HttpKernel session closed")
