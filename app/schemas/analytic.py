from pydantic import BaseModel


class AnalyticsKpiResponse(BaseModel):
    window_days: int
    total_conversations: int
    total_messages: int
    llm_calls_window: int
    total_cost_window: float
    avg_latency_ms_window: float
    vectorized_documents: int
    vectorized_pdf_documents: int
    vectorized_chunks: int


class DailyCostPoint(BaseModel):
    day: str
    total_cost: float
    total_tokens: int
    calls: int


class DailyLatencyPoint(BaseModel):
    day: str
    avg_latency_ms: float
    max_latency_ms: int
    calls: int


class CostBreakdownItem(BaseModel):
    provider: str
    model: str
    total_cost: float
    total_tokens: int
    calls: int
