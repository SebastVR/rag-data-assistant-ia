from typing import List, Optional

from pydantic import BaseModel


class RerankRequest(BaseModel):
    query: str
    texts: List[str]
    limit: Optional[int] = None


class RerankResult(BaseModel):
    text: str
    score: float
    index: int
    rank: int
