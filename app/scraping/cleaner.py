from __future__ import annotations

import re
from typing import Optional

import trafilatura
from bs4 import BeautifulSoup

from app.scraping.parser import ParsedPage


# ────────────────────────────────────────────────────────────────
class HtmlCleaner:
    """Limpia HTML y contenido parseado para extraer el texto útil."""

    NOISE_SELECTORS = [
        "script",
        "style",
        "noscript",
        "svg",
        "iframe",
        "header",
        "footer",
        "nav",
        "form",
        "aside",
    ]

    # ────────────────────────────────────────────────────────────────
    def clean_html(self, html: str) -> str:
        """Elimina ruido y etiquetas innecesarias del HTML."""
        soup = BeautifulSoup(html, "lxml")

        for selector in self.NOISE_SELECTORS:
            for tag in soup.find_all(selector):
                tag.decompose()

        # Intenta quitar bloques comunes de ruido por clase o id.
        noise_keywords = [
            "cookie",
            "cookies",
            "navbar",
            "menu",
            "footer",
            "header",
            "breadcrumb",
            "banner",
            "modal",
            "popup",
        ]

        from bs4.element import Tag

        for tag in soup.find_all(True):
            if not isinstance(tag, Tag) or not isinstance(tag.attrs, dict):
                continue
            classes = tag.get("class")
            if classes is None:
                class_names = ""
            else:
                class_names = " ".join(classes)
            element_id = tag.get("id")
            if element_id is None:
                element_id = ""
            combined = f"{class_names} {element_id}".lower()

            if any(keyword in combined for keyword in noise_keywords):
                tag.decompose()

        return str(soup)

    # ────────────────────────────────────────────────────────────────
    def extract_main_text_with_trafilatura(self, html: str) -> Optional[str]:
        """Extrae el texto principal usando trafilatura."""
        try:
            extracted = trafilatura.extract(
                html,
                include_links=False,
                include_images=False,
                include_tables=True,
                favor_precision=True,
                deduplicate=True,
            )
            if extracted:
                return self.normalize_text(extracted)
        except Exception:
            return None
        return None

    # ────────────────────────────────────────────────────────────────
    def clean_parsed_page(self, parsed_page: ParsedPage, cleaned_html: str) -> str:
        """Limpia y normaliza el contenido de una página parseada."""
        trafilatura_text = self.extract_main_text_with_trafilatura(cleaned_html)
        if trafilatura_text and len(trafilatura_text) >= 100:
            return trafilatura_text

        # Fallback: usar contenido parseado.
        parts = []

        if parsed_page.title:
            parts.append(parsed_page.title)

        if parsed_page.headings:
            parts.extend(parsed_page.headings)

        if parsed_page.paragraphs:
            parts.extend(parsed_page.paragraphs)

        if parsed_page.list_items:
            parts.extend(parsed_page.list_items)

        combined = "\n".join(parts)
        return self.normalize_text(combined)

    # ────────────────────────────────────────────────────────────────
    def normalize_text(self, text: str) -> str:
        """Normaliza espacios y saltos de línea en el texto."""
        text = text.replace("\xa0", " ")
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\n\s*\n", "\n\n", text)
        return text.strip()
