from pydantic import BaseModel, Field


# --- Schemas para creación de conversación ---
class ConversationCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=80)
    session_id: str | None = Field(default=None, min_length=3)


class ConversationCreateResponse(BaseModel):
    id: int
    session_id: str
    title: str
    channel: str
    created_at: str
    updated_at: str


from pydantic import BaseModel, Field


class RagQuestionRequest(BaseModel):
    question: str = Field(..., min_length=3)
    use_rerank: bool = True


class RagChatRequest(BaseModel):
    question: str = Field(..., min_length=3)
    conversation_id: int | None = Field(
        default=None,
        description="ID numerico de la conversacion existente",
    )
    session_id: str | None = Field(
        default=None,
        min_length=3,
        description="ID de sesion externo; si no existe, se crea conversacion",
    )
    history_messages: int = Field(
        default=6,
        ge=0,
        le=50,
        description="Cantidad de mensajes previos usados como contexto",
    )
    use_rerank: bool = True
