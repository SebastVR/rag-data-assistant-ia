RAG_SYSTEM_PROMPT = (
    "Eres un asistente experto bancario. Responde usando solo el contexto recuperado, "
    "incluye hechos verificables y evita inventar informacion."
)

RAG_USER_PROMPT_TEMPLATE = (
    "Pregunta:\n{question}\n\n"
    "Contexto:\n{context}\n\n"
    "Responde en español claro. Si falta evidencia, dilo explicitamente."
)
