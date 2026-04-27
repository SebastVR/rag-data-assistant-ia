from pydantic import BaseModel, Field


class ActivateModelRequest(BaseModel):
    provider: str = Field(
        ...,
        description="llama_cpp | ollama | chatgpt | openai | claude | bedrock",
    )
    model_name: str = Field(..., min_length=1)
    model_path: str | None = Field(
        default=None,
        description=("Opcional. Requerido solo si no se puede inferir para llama_cpp"),
    )
    set_as_active: bool = True


class ActivateModelByIdRequest(BaseModel):
    language_model_id: int = Field(..., ge=1)
    set_as_active: bool = True
