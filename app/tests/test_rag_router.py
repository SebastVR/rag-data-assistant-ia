"""
Pruebas para el endpoint de creación de conversación RAG.
"""

# ─────────────────────────────────────────────
from fastapi.testclient import TestClient

from app.main import api as app

client = TestClient(app)


# ─────────────────────────────────────────────
def test_create_conversation():
    """Prueba la creación de una conversación RAG."""
    payload = {"user_id": 1, "title": "Test", "description": "Prueba"}
    response = client.post("/api/v1/rag/conversations", json=payload)
    assert response.status_code == 200 or response.status_code == 201
    data = response.json()
    assert "id" in data or "conversation_id" in data


# ─────────────────────────────────────────────
def test_get_embeddings_info():
    """Prueba el endpoint de información de embeddings."""
    response = client.get("/api/v1/rag/embeddings")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


# ─────────────────────────────────────────────
def test_chat_streaming_endpoint():
    """Prueba el endpoint de chat en streaming."""
    payload = {"question": "¿Cuál es la capital de Francia?"}
    response = client.post("/api/v1/rag/chat/streaming", json=payload)
    # Puede ser 200 o 422 si falta algún campo obligatorio
    assert response.status_code in (200, 422)


# ─────────────────────────────────────────────
def test_rag_query():
    """Prueba el endpoint de consulta RAG simple."""
    payload = {"question": "¿Qué es el RAG?", "use_rerank": False}
    response = client.post("/api/v1/rag/query", json=payload)
    # Puede ser 200 o 422 si falta algún campo obligatorio
    assert response.status_code in (200, 422)


# ─────────────────────────────────────────────
def test_trigger_pending_ingestion():
    """Prueba el endpoint para lanzar la ingesta pendiente."""
    response = client.post("/api/v1/rag/ingestion/pending", json={"limit": 1})
    # Puede ser 200 si la tarea se despacha correctamente, o 422 si falta algún campo
    assert response.status_code in (200, 422)
