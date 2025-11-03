from pydantic import BaseModel


class ExpectedOutput(BaseModel):
    answer: str


class SQLEvaluation(BaseModel):
    query_is_correct: bool
    duration: float


class SQLAggregatedEvaluation(BaseModel):
    correct_percentage: float
    mean_duration: float
