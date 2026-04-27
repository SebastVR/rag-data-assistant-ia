from __future__ import annotations

from typing import Dict, List

from app.rag.chunking.base import BaseChunker, ChunkedText


# ────────────────────────────────────────────────────────────────
class RecursiveTextChunker(BaseChunker):
    """Chunker recursivo que divide texto en fragmentos con solapamiento."""

    # ────────────────────────────────────────────────────────────────
    def __init__(self, chunk_size: int = 900, chunk_overlap: int = 150):
        """Inicializa el chunker con tamaño y solapamiento configurables."""
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    # ────────────────────────────────────────────────────────────────
    def _split_recursive(self, text: str, separators: List[str]) -> List[str]:
        """Divide recursivamente el texto usando los separadores dados."""
        if len(text) <= self.chunk_size or not separators:
            return [text]

        sep = separators[0]
        if sep:
            parts = text.split(sep)
            candidate_chunks: List[str] = []
            buffer = ""
            joiner = sep

            for part in parts:
                piece = part.strip()
                if not piece:
                    continue

                tentative = f"{buffer}{joiner if buffer else ''}{piece}"
                if len(tentative) <= self.chunk_size:
                    buffer = tentative
                else:
                    if buffer:
                        candidate_chunks.append(buffer)
                    buffer = piece

            if buffer:
                candidate_chunks.append(buffer)
        else:
            candidate_chunks = [
                text[i : i + self.chunk_size]
                for i in range(0, len(text), self.chunk_size)
            ]

        output: List[str] = []
        for chunk in candidate_chunks:
            if len(chunk) <= self.chunk_size:
                output.append(chunk)
            else:
                output.extend(self._split_recursive(chunk, separators[1:]))
        return output

    # ────────────────────────────────────────────────────────────────
    def _apply_overlap(self, chunks: List[str]) -> List[str]:
        """Aplica solapamiento entre los chunks generados."""
        if not chunks or self.chunk_overlap <= 0:
            return chunks

        with_overlap: List[str] = []
        for idx, chunk in enumerate(chunks):
            if idx == 0:
                with_overlap.append(chunk)
                continue

            prev_tail = chunks[idx - 1][-self.chunk_overlap :]
            merged = f"{prev_tail} {chunk}".strip()
            with_overlap.append(merged)

        return with_overlap

    # ────────────────────────────────────────────────────────────────
    def chunk(self, text: str, metadata: Dict[str, object]) -> List[ChunkedText]:
        """Divide un texto largo en chunks con metadatos y solapamiento."""
        separators = ["\n\n", "\n", ". ", " ", ""]
        raw_chunks = self._split_recursive(text, separators)
        raw_chunks = self._apply_overlap(raw_chunks)
        chunks: List[ChunkedText] = []

        for idx, content in enumerate(raw_chunks, start=1):
            clean_content = content.strip()
            if not clean_content:
                continue

            chunk_metadata = dict(metadata)
            chunk_metadata["chunk_index"] = idx
            chunks.append(
                ChunkedText(
                    content=clean_content,
                    index=idx,
                    metadata=chunk_metadata,
                )
            )

        return chunks
