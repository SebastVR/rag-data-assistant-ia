from __future__ import annotations

import os
from uuid import uuid4

import httpx
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

API_BASE_URL = os.getenv("RAG_API_URL", "http://localhost")
DEFAULT_HISTORY_MESSAGES = int(os.getenv("CHAT_HISTORY_MESSAGES", "6"))
REQUEST_TIMEOUT = float(os.getenv("STREAMLIT_HTTP_TIMEOUT", "45"))


# ─────────────────────────────────────────────────────────────
def _api_url(path: str) -> str:
    """Construye la URL completa para la API."""
    base = API_BASE_URL.rstrip("/")
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"{base}{normalized_path}"


# ─────────────────────────────────────────────────────────────
def _get(path: str, params: dict | None = None) -> dict:
    """Realiza una petición GET a la API."""
    with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
        response = client.get(_api_url(path), params=params)
        response.raise_for_status()
        return response.json()


# ─────────────────────────────────────────────────────────────
def _post(path: str, payload: dict) -> dict:
    """Realiza una petición POST a la API."""
    with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
        response = client.post(_api_url(path), json=payload)
        response.raise_for_status()
        return response.json()


# ─────────────────────────────────────────────────────────────
def fetch_overview(days: int) -> dict:
    """Obtiene el resumen de analítica para los días indicados."""
    return _get("/api/v1/analytics/overview", params={"days": days})


# ─────────────────────────────────────────────────────────────
def fetch_recent_conversations(search: str, limit: int = 30) -> list[dict]:
    """Obtiene conversaciones recientes según búsqueda y límite."""
    params = {"limit": limit}
    if search.strip():
        params["q"] = search.strip()
    data = _get("/api/v1/analytics/conversations/recent", params=params)
    return data.get("items", [])


# ─────────────────────────────────────────────────────────────
def create_conversation(
    title: str | None = None, session_id: str | None = None
) -> dict:
    """Crea una nueva conversación en el backend."""
    payload = {}
    if title:
        payload["title"] = title
    if session_id:
        payload["session_id"] = session_id
    return _post("/api/v1/rag/conversations", payload)


# ─────────────────────────────────────────────────────────────
def fetch_messages(conversation_id: int, limit: int = 100) -> list[dict]:
    """Obtiene los mensajes de una conversación por ID."""
    data = _get(f"/api/v1/rag/chat/{conversation_id}/messages", params={"limit": limit})
    return data.get("items", [])


# ─────────────────────────────────────────────────────────────
def ask_chat(question: str, conversation_id: int | None, history_messages: int) -> dict:
    """Envía una pregunta al chat RAG con historial."""
    payload = {
        "question": question,
        "history_messages": history_messages,
        "use_rerank": True,
    }
    if conversation_id is not None:
        payload["conversation_id"] = conversation_id
    else:
        payload["session_id"] = st.session_state.chat_session_id
    return _post("/api/v1/rag/chat", payload)


# ─────────────────────────────────────────────────────────────
def ask_open_question(question: str) -> dict:
    """Envía una pregunta abierta (sin historial) al índice RAG."""
    payload = {
        "question": question,
        "use_rerank": True,
    }
    return _post("/api/v1/rag/query", payload)


# ─────────────────────────────────────────────────────────────
def ensure_state() -> None:
    """Inicializa el estado de sesión de Streamlit si es necesario."""
    st.session_state.setdefault("selected_conversation_id", None)
    st.session_state.setdefault("chat_session_id", str(uuid4()))
    st.session_state.setdefault("open_answer", None)


# ─────────────────────────────────────────────────────────────
def render_sidebar(left_col) -> None:
    """Renderiza la barra lateral de conversaciones."""
    with left_col:
        st.subheader("Conversaciones")
        search_term = st.text_input("Buscar", placeholder="Titulo o session_id")

        if st.button("+ Nueva conversacion", use_container_width=True):
            try:
                # Puedes personalizar el título si lo deseas, aquí se deja vacío
                response = create_conversation()
                st.session_state.selected_conversation_id = response.get("id")
                st.session_state.chat_session_id = response.get("session_id")
                st.session_state.open_answer = None
                st.rerun()
            except Exception as exc:
                st.error(f"No se pudo crear la conversación: {exc}")
                return

        try:
            conversations = fetch_recent_conversations(search=search_term)
        except Exception as exc:
            st.error(f"No se pudo cargar el historial: {exc}")
            return

        if not conversations:
            st.caption("Sin conversaciones registradas")
            return

        for row in conversations:
            title = row.get("title") or "Chat"
            msg_count = row.get("message_count", 0)
            label = f"#{row['id']} {title[:45]} ({msg_count})"
            if st.button(label, key=f"conv_{row['id']}", use_container_width=True):
                st.session_state.selected_conversation_id = row["id"]
                st.session_state.chat_session_id = row.get("session_id") or str(uuid4())


# ─────────────────────────────────────────────────────────────
def render_chat(center_col) -> None:
    """Renderiza la interfaz de chat principal."""
    with center_col:
        st.subheader("Chat RAG")
        conversation_id = st.session_state.selected_conversation_id

        if conversation_id is None:
            st.caption("Conversacion nueva")
            messages = []
        else:
            st.caption(f"Conversacion ID: {conversation_id}")
            try:
                messages = fetch_messages(conversation_id=conversation_id)
            except Exception as exc:
                st.error(f"No se pudieron cargar los mensajes: {exc}")
                messages = []

        chat_box = st.container(height=560, border=True)
        with chat_box:
            if not messages:
                st.caption("Escribe tu primera pregunta para iniciar la conversacion.")
            for msg in messages:
                role = (
                    "assistant"
                    if (msg.get("role") or "").lower() == "assistant"
                    else "user"
                )
                with st.chat_message(role):
                    st.markdown(msg.get("content") or "")

        question = st.chat_input("Escribe tu pregunta...")
        if question:
            try:
                response = ask_chat(
                    question=question,
                    conversation_id=conversation_id,
                    history_messages=DEFAULT_HISTORY_MESSAGES,
                )
                st.session_state.selected_conversation_id = response.get(
                    "conversation_id"
                )
                st.session_state.chat_session_id = (
                    response.get("session_id") or st.session_state.chat_session_id
                )
                st.rerun()
            except Exception as exc:
                st.error(f"Error consultando /chat: {exc}")

        with st.expander("Pregunta abierta (sin historial de conversacion)"):
            open_question = st.text_area(
                "Consulta directa al indice vectorial",
                placeholder="Ej: Resume que dice BBVA sobre creditos empresariales",
                height=110,
            )
            if st.button("Consultar", key="open_query_button"):
                if not open_question.strip():
                    st.warning("Escribe una pregunta antes de consultar")
                else:
                    try:
                        st.session_state.open_answer = ask_open_question(
                            open_question.strip()
                        )
                    except Exception as exc:
                        st.error(f"Error en /query: {exc}")

            if st.session_state.open_answer:
                answer = st.session_state.open_answer.get("answer") or "Sin respuesta"
                st.markdown("**Respuesta:**")
                st.write(answer)


# ─────────────────────────────────────────────────────────────
def render_analytics(right_col) -> None:
    """Renderiza el panel de analítica y métricas."""
    with right_col:
        st.subheader("Analitica")
        days = st.slider("Ventana (dias)", min_value=7, max_value=90, value=30, step=1)

        try:
            overview = fetch_overview(days=days)
        except Exception as exc:
            st.error(f"No se pudo cargar analitica: {exc}")
            return

        kpis = overview.get("kpis", {})
        daily_cost = overview.get("daily_cost", [])
        daily_latency = overview.get("daily_latency", [])
        by_model = overview.get("cost_by_model", [])

        st.metric("# documentos", int(kpis.get("vectorized_documents", 0)))
        st.metric("# PDFs vectorizados", int(kpis.get("vectorized_pdf_documents", 0)))
        st.metric("# chunks", int(kpis.get("vectorized_chunks", 0)))
        st.metric("# mensajes", int(kpis.get("total_messages", 0)))
        st.metric("Costo total", f"{float(kpis.get('total_cost_window', 0)):.4f}")
        st.metric(
            "Latencia prom.", f"{float(kpis.get('avg_latency_ms_window', 0)):.0f} ms"
        )

        if daily_cost:
            cost_df = pd.DataFrame(daily_cost)
            cost_df["total_cost"] = pd.to_numeric(
                cost_df["total_cost"], errors="coerce"
            ).fillna(0)
            cost_df["calls"] = pd.to_numeric(cost_df["calls"], errors="coerce").fillna(
                0
            )
            fig_cost = px.line(
                cost_df,
                x="day",
                y="total_cost",
                markers=True,
                title="Costo diario",
            )
            st.plotly_chart(fig_cost, use_container_width=True)

        if daily_latency:
            latency_df = pd.DataFrame(daily_latency)
            latency_df["avg_latency_ms"] = pd.to_numeric(
                latency_df["avg_latency_ms"], errors="coerce"
            ).fillna(0)
            latency_df["max_latency_ms"] = pd.to_numeric(
                latency_df["max_latency_ms"], errors="coerce"
            ).fillna(0)
            fig_latency = px.line(
                latency_df,
                x="day",
                y=["avg_latency_ms", "max_latency_ms"],
                title="Latencia diaria",
            )
            st.plotly_chart(fig_latency, use_container_width=True)

        if by_model:
            model_df = pd.DataFrame(by_model)
            model_df["total_cost"] = pd.to_numeric(
                model_df["total_cost"], errors="coerce"
            ).fillna(0)
            model_df = model_df.sort_values("total_cost", ascending=False).head(10)
            if not model_df.empty:
                model_df["label"] = model_df["provider"] + " / " + model_df["model"]
                model_df["total_cost"] = np.round(model_df["total_cost"], 6)
                fig_model = px.bar(
                    model_df,
                    x="total_cost",
                    y="label",
                    orientation="h",
                    title="Costo por modelo",
                )
                st.plotly_chart(fig_model, use_container_width=True)


# ─────────────────────────────────────────────────────────────
def main() -> None:
    """Función principal: configura y renderiza la app Streamlit."""
    st.set_page_config(
        page_title="RAG Bank Assistant",
        page_icon="\U0001f4ca",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    ensure_state()

    st.title("RAG Bank Assistant - Chat + Analitica")
    st.caption("Layout 3 columnas: historial | chat grande | panel de metricas")

    left_col, center_col, right_col = st.columns([1, 3, 1.4], gap="medium")
    render_sidebar(left_col)
    render_chat(center_col)
    render_analytics(right_col)


if __name__ == "__main__":
    main()
