from typing import List, Optional

from pydantic import BaseModel, Field


class DocumentFileItem(BaseModel):
    id: int
    scraped_document_id: int
    doc_id: str
    source_url: Optional[str] = None
    file_url: Optional[str] = None
    file_type: Optional[str] = None
    file_path: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    status: Optional[str] = None
    error_message: Optional[str] = None
    processed_at: Optional[str] = None
    created_at: Optional[str] = None


class ScrapedDocumentDetail(BaseModel):
    id: int
    doc_id: str
    source_name: Optional[str] = None
    url: Optional[str] = None
    source_url: Optional[str] = None
    title: Optional[str] = None
    category: Optional[str] = None
    headings: Optional[list] = None
    text: Optional[str] = None
    status: Optional[str] = None
    error_message: Optional[str] = None
    scraped_at: Optional[str] = None
    created_at: Optional[str] = None
    files: Optional[List[DocumentFileItem]] = None


class ListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list
