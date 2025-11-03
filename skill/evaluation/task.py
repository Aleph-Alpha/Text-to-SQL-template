import os

import requests
from pharia_inference_sdk.core import NoOpTracer, Task, TaskSpan
from pydantic import BaseModel
from qa import Input, Output


class QATask(Task[Input, Output]):
    def __init__(self) -> None:
        self.token = os.getenv("PHARIA_AI_TOKEN")
        self.kernel_url = os.getenv("PHARIA_KERNEL_ADDRESS")
        self.skill_namespace = "playground"
        self.skill_name = "sql-generator"

    def do_run(self, input: Input, task_span: TaskSpan) -> Output:
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            url = f"{self.kernel_url}/v1/skills/{self.skill_namespace}/{self.skill_name}/run"
            response = requests.post(
                url,
                json=input.model_dump() if isinstance(input, BaseModel) else input,
                headers=headers,
            )
            response = response.json()
            return Output(answer=response["answer"])
        except Exception as e:
            print(e)
            return Output(answer=None)


if __name__ == "__main__":
    task = QATask()
    input = Input(question="Total number of customers from Germany?")
    output = task.run(input, NoOpTracer())
    print(output)
