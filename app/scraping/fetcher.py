from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


# ────────────────────────────────────────────────────────────────
class FetchError(Exception):
    """Error controlado para problemas al descargar una URL."""


# ────────────────────────────────────────────────────────────────
@dataclass
class FetchResult:
    url: str
    final_url: str
    status_code: int
    content_type: str
    html: str


# ────────────────────────────────────────────────────────────────
class HtmlFetcher:
    """Descarga HTML de una URL con manejo de reintentos y headers personalizados."""

    # ────────────────────────────────────────────────────────────────
    def __init__(
        self,
        timeout: int = 20,
        user_agent: Optional[str] = None,
    ) -> None:
        """Inicializa el fetcher con timeout y user-agent opcional."""
        self.timeout = timeout
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
                "Connection": "keep-alive",
            }
        )

    # ────────────────────────────────────────────────────────────────
    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((requests.RequestException, FetchError)),
    )
    def fetch(self, url: str) -> FetchResult:
        """Descarga el HTML de una URL y valida el tipo de contenido."""
        try:
            response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise FetchError(f"Error al descargar {url}: {exc}") from exc

        content_type = response.headers.get("Content-Type", "").lower()
        if (
            "text/html" not in content_type
            and "application/xhtml+xml" not in content_type
        ):
            raise FetchError(
                f"Contenido no soportado para {url}. Content-Type recibido: {content_type}"
            )

        response.encoding = response.encoding or response.apparent_encoding or "utf-8"

        html = response.text
        if not html.strip():
            raise FetchError(f"La respuesta HTML llegó vacía para {url}")

        return FetchResult(
            url=url,
            final_url=response.url,
            status_code=response.status_code,
            content_type=content_type,
            html=html,
        )
