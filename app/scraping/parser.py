from __future__ import annotations

from dataclasses import dataclass, field
from typing import List
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


# ────────────────────────────────────────────────────────────────
@dataclass
class ParsedSection:
    heading: str
    content: str


# ────────────────────────────────────────────────────────────────
@dataclass
class ParsedPage:
    url: str
    title: str
    headings: List[str] = field(default_factory=list)
    paragraphs: List[str] = field(default_factory=list)
    list_items: List[str] = field(default_factory=list)
    internal_links: List[str] = field(default_factory=list)
    sections: List[ParsedSection] = field(default_factory=list)


# ────────────────────────────────────────────────────────────────
class HtmlParser:
    """Parsea HTML y extrae la estructura principal de la página."""

    # ────────────────────────────────────────────────────────────────
    def parse(self, html: str, base_url: str) -> ParsedPage:
        """Parsea el HTML y retorna la estructura de la página."""
        soup = BeautifulSoup(html, "lxml")

        title = self._extract_title(soup)
        headings = self._extract_headings(soup)
        paragraphs = self._extract_paragraphs(soup)
        list_items = self._extract_list_items(soup)
        internal_links = self._extract_internal_links(soup, base_url)
        sections = self._extract_sections(soup)

        return ParsedPage(
            url=base_url,
            title=title,
            headings=headings,
            paragraphs=paragraphs,
            list_items=list_items,
            internal_links=internal_links,
            sections=sections,
        )

    # ────────────────────────────────────────────────────────────────
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extrae el título principal de la página."""
        if soup.title and soup.title.text:
            return self._clean_text(soup.title.get_text(" ", strip=True))

        h1 = soup.find("h1")
        if h1:
            return self._clean_text(h1.get_text(" ", strip=True))

        return "Sin título"

    # ────────────────────────────────────────────────────────────────
    def _extract_headings(self, soup: BeautifulSoup) -> List[str]:
        """Extrae los encabezados h1, h2, h3 de la página."""
        results: List[str] = []

        for tag_name in ["h1", "h2", "h3"]:
            for tag in soup.find_all(tag_name):
                text = self._clean_text(tag.get_text(" ", strip=True))
                if text and text not in results:
                    results.append(text)

        return results

    # ────────────────────────────────────────────────────────────────
    def _extract_paragraphs(self, soup: BeautifulSoup) -> List[str]:
        """Extrae los párrafos principales de la página."""
        results: List[str] = []

        for tag in soup.find_all("p"):
            text = self._clean_text(tag.get_text(" ", strip=True))
            if len(text) >= 30:
                results.append(text)

        return results

    # ────────────────────────────────────────────────────────────────
    def _extract_list_items(self, soup: BeautifulSoup) -> List[str]:
        """Extrae los ítems de listas de la página."""
        results: List[str] = []

        for tag in soup.find_all("li"):
            text = self._clean_text(tag.get_text(" ", strip=True))
            if len(text) >= 10:
                results.append(text)

        return results

    # ────────────────────────────────────────────────────────────────
    def _extract_internal_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extrae los enlaces internos de la página."""
        results: List[str] = []
        base_domain = urlparse(base_url).netloc

        for a_tag in soup.find_all("a", href=True):
            href = a_tag.get("href", "").strip()

            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue

            absolute_url = urljoin(base_url, href)
            parsed = urlparse(absolute_url)

            if parsed.netloc != base_domain:
                continue

            normalized = parsed._replace(fragment="").geturl()

            if normalized not in results:
                results.append(normalized)

        return results

    # ────────────────────────────────────────────────────────────────
    def _extract_sections(self, soup: BeautifulSoup) -> List[ParsedSection]:
        """Extrae secciones agrupadas por encabezados."""
        sections: List[ParsedSection] = []

        for heading_tag in soup.find_all(["h1", "h2", "h3"]):
            heading_text = self._clean_text(heading_tag.get_text(" ", strip=True))
            if not heading_text:
                continue

            collected_parts: List[str] = []
            sibling = heading_tag.find_next_sibling()

            while sibling and sibling.name not in ["h1", "h2", "h3"]:
                if sibling.name in ["p", "li", "ul", "ol", "div", "section"]:
                    text = self._clean_text(sibling.get_text(" ", strip=True))
                    if len(text) >= 20:
                        collected_parts.append(text)

                sibling = sibling.find_next_sibling()

            content = "\n".join(collected_parts).strip()

            if content:
                sections.append(
                    ParsedSection(
                        heading=heading_text,
                        content=content,
                    )
                )

        return sections

    # ────────────────────────────────────────────────────────────────
    def _clean_text(self, value: str) -> str:
        """Limpia y normaliza el texto extraído."""
        return " ".join(value.split())
