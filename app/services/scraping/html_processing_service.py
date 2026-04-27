import hashlib
import json
import os
import re
from typing import Any, Dict

from app.config.settings import settings
from app.scraping.cleaner import HtmlCleaner
from app.scraping.parser import HtmlParser
from app.services.s3_storage import S3Storage


# ────────────────────────────────────────────────────────────────
def process_all_html_and_return_json(prefix: str) -> Dict[str, Any]:
    """
    Procesa todos los HTMLs scrapeados bajo el prefijo dado, deduplica y devuelve un dict con los documentos únicos.
    Además, guarda el JSON en MinIO/AWS S3 y en debug/json si es desarrollo.
    """
    # Leer HTMLs desde MinIO/AWS
    s3 = S3Storage()
    parser = HtmlParser()
    cleaner = HtmlCleaner()
    unique_hashes = set()
    unique_docs = {}
    # Listar todos los objetos HTML en la carpeta correspondiente
    html_keys = s3.list_objects(prefix, suffix=".html")
    for key in html_keys:
        object_name = key.replace(f"{prefix}/", "", 1)
        html = s3.read_file(prefix, object_name).decode("utf-8")
        # Extraer la URL real de la página web (og:url o canonical)
        source_url = None
        og_url_match = re.search(
            r'<meta[^>]+property=["\']og:url["\'][^>]+content=["\']([^"\']+)["\']', html
        )
        if og_url_match:
            source_url = og_url_match.group(1)
        else:
            canonical_match = re.search(
                r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', html
            )
            if canonical_match:
                source_url = canonical_match.group(1)
        base_url = f"s3://{s3.bucket_name}/{key}"
        parsed_page = parser.parse(html, base_url=base_url)
        cleaned_html = cleaner.clean_html(html)
        clean_text = cleaner.clean_parsed_page(parsed_page, cleaned_html)
        if not clean_text or len(clean_text.strip()) < 100:
            continue
        doc_hash = hashlib.md5(clean_text.encode("utf-8")).hexdigest()
        if doc_hash not in unique_hashes:
            unique_hashes.add(doc_hash)
            file_key = os.path.splitext(os.path.basename(key))[0]
            unique_docs[file_key] = {
                "file": os.path.basename(key),
                "title": parsed_page.title,
                "headings": parsed_page.headings,
                "text": clean_text,
                "url": getattr(parsed_page, "url", base_url),
                "source_url": source_url,
            }
    # Guardar en debug/json si es dev
    json_data = json.dumps(unique_docs, ensure_ascii=False, indent=2)
    if settings.app_env.lower() in ("dev", "development"):
        json_dir = None
        candidates = ["/app/debug/json", "app/debug/json"]
        for path in candidates:
            if os.path.isdir(path):
                json_dir = path
                break
        if not json_dir:
            os.makedirs(candidates[1], exist_ok=True)
            json_dir = candidates[1]
        output_path = os.path.join(json_dir, "html_docs_unicos.json")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(json_data)
    # Guardar en MinIO/AWS S3 en carpeta dinámica
    json_prefix = prefix.replace("_html", "_json")
    s3.write_file(json_prefix, "html_docs_unicos.json", json_data.encode("utf-8"))
    return unique_docs
