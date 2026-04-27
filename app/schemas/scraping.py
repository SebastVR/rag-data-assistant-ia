from typing import Any, Dict, List

from pydantic import BaseModel, Field


class CrawlRequest(BaseModel):
    base_url: str | None = Field(default=None)
    max_pages: int | None = Field(default=None, ge=1, le=500)
    timeout: int | None = Field(default=None, ge=5, le=120)
