from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from app.models.scraped_document import ScrapedDocument


# ────────────────────────────────────────────────────────────────
class ScrapingStorage:
    """Gestiona el almacenamiento local de HTMLs y documentos procesados."""

    # ────────────────────────────────────────────────────────────────
    def __init__(self, raw_dir: str, processed_dir: str) -> None:
        """Inicializa los directorios de almacenamiento."""
        self.raw_dir = Path(raw_dir)
        self.processed_dir = Path(processed_dir)

        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    # ────────────────────────────────────────────────────────────────
    def save_raw_html(self, url: str, html: str) -> str:
        """Guarda el HTML crudo de una URL en disco."""
        file_name = self._build_safe_name(url, extension="html")
        file_path = self.raw_dir / file_name
        file_path.write_text(html, encoding="utf-8")
        return str(file_path)

    # ────────────────────────────────────────────────────────────────
    def save_processed_document(self, document: ScrapedDocument) -> str:
        """Guarda un documento procesado en formato JSON."""
        file_name = self._build_safe_name(document.url, extension="json")
        file_path = self.processed_dir / file_name
        file_path.write_text(
            json.dumps(document.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(file_path)

    # ────────────────────────────────────────────────────────────────
    def _build_safe_name(self, url: str, extension: str) -> str:
        """Genera un nombre de archivo seguro a partir de la URL."""
        parsed = urlparse(url)
        domain = parsed.netloc.replace(".", "_")
        path = parsed.path.strip("/").replace("/", "_") or "home"
        return f"{domain}__{path}.{extension}"
