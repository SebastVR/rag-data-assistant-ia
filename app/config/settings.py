# Límite de chunks por consulta
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración principal de la aplicación RAG Bank Assistant."""

    model_config = SettingsConfigDict(env_file="app/.env", extra="ignore")

    # ─────────────── GENERAL ───────────────
    app_name: str = "rag-data-assistant-ia"  # Nombre de la app
    app_env: str = "dev"  # "dev" para local/dev, "prod" para producción
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # ─────────────── ALMACENAMIENTO LOCAL ───────────────
    raw_data_path: str = "data/raw"
    processed_data_path: str = "data/processed"

    # ─────────────── MINIO (local/dev) ───────────────
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket_name: str

    # ─────────────── AWS S3 (producción) ───────────────
    # aws_region_name: str
    # aws_s3_access_key_id: str
    # aws_s3_secret_access_key: str
    # aws_s3_bucket_name: str

    # ─────────────── POSTGRES ───────────────
    postgres_db: str
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_port: int = 5432

    # ─────────────── SUPABASE (opcional) ───────────────
    # supabase_url: str | None = None
    # supabase_service_key: str | None = None
    # supabase_attachment_bucket: str | None = None

    # ─────────────── QDRANT (vector store) ───────────────
    qdrant_host: str  # Host del contenedor Qdrant
    qdrant_port: int  # Puerto HTTP
    qdrant_grpc_port: int  # Puerto gRPC
    qdrant_collection_name: str
    qdrant_max_chunks_retrieved: int  # Límite de chunks por consulta
    qdrant_max_chunks_reranked: int  # Límite de chunks por reordenamiento

    # ─────────────── RAG (chunking/embeddings/reranker) ───────────────
    rag_chunk_size: int = 900
    rag_chunk_overlap: int = 150
    rag_embedding_model: str = (
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    rag_reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # ─────────────── LLM runtime (local/API) ───────────────
    llm_provider: str = (
        "ollama"  # llama_cpp | ollama | openai | chatgpt | claude | bedrock
    )
    llm_model_name: str = "llama3.2"
    llm_model_path: str = "app/rag/llama-2-7b-chat.Q4_K_M.gguf"
    ollama_base_url: str = "http://localhost:11434"
    openai_api_key: str | None = None
    # bedrock_model_id: str
    bedrock_max_new_tokens: int = 5000
    bedrock_temperature: float = 0.0

    # ─────────────── CELERY ───────────────
    celery_broker_url: str
    celery_backend_url: str
    rabbitmq_default_user: str
    rabbitmq_default_pass: str

    # ─────────────── SCRAPING ───────────────
    scraper_base_url: str
    scraper_allowed_domain: str
    scraper_max_pages: int = 10
    scraper_timeout: int = 20
    scraper_user_agent: str


settings = Settings()
