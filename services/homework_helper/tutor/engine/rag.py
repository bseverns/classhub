"""Curriculum-only local RAG helpers backed by pgvector in Postgres."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

from psycopg import sql

from .reference import SAFE_REF_KEY_RE

RAG_TABLE_NAME = "tutor_curriculum_rag_chunks"
_IDENTIFIER_PART_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def build_reference_inventory(reference_dir: str, reference_map_raw: str) -> dict[str, str]:
    """Return a safe map of reference key -> markdown path within reference_dir."""
    root = Path(reference_dir or "").resolve()
    if not root.exists() or not root.is_dir():
        return {}
    inventory: dict[str, str] = {}

    if reference_map_raw:
        try:
            reference_map = json.loads(reference_map_raw)
        except Exception:
            reference_map = {}
        if isinstance(reference_map, dict):
            for key_raw, rel_raw in reference_map.items():
                key = str(key_raw or "").strip().lower()
                rel = str(rel_raw or "").strip()
                if not SAFE_REF_KEY_RE.fullmatch(key) or not rel:
                    continue
                candidate = (root / rel).resolve()
                if not _is_child_path(candidate, root):
                    continue
                if candidate.is_file() and candidate.suffix.lower() == ".md":
                    inventory[key] = str(candidate)

    for candidate in sorted(root.glob("*.md")):
        key = candidate.stem.strip().lower()
        if not SAFE_REF_KEY_RE.fullmatch(key):
            continue
        inventory.setdefault(key, str(candidate.resolve()))
    return inventory


def ensure_pgvector_schema(
    *,
    connection,
    logger: logging.Logger,
    embedding_dimensions: int,
    table_name: str = RAG_TABLE_NAME,
) -> bool:
    """Create extension/table for curriculum-only RAG storage (Postgres only)."""
    if connection.vendor != "postgresql":
        return False
    safe_table_name = _safe_table_name(table_name)
    quoted_table_name = connection.ops.quote_name(safe_table_name)
    safe_index_name = _safe_table_name(f"{safe_table_name}_reference_key_idx")
    quoted_index_name = connection.ops.quote_name(safe_index_name)
    dims = max(int(embedding_dimensions or 0), 1)
    table_ident = _sql_table_identifier(table_name)
    table_parts = _relation_identifier_parts(table_name)
    index_ident = _sql_index_identifier(table_name, suffix="reference_key_idx")
    with connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cursor.execute(
            sql.SQL(
                """
                CREATE TABLE IF NOT EXISTS {table} (
                    id BIGSERIAL PRIMARY KEY,
                    reference_key VARCHAR(128) NOT NULL,
                    source_label VARCHAR(128) NOT NULL,
                    chunk_id VARCHAR(64) NOT NULL,
                    chunk_order INTEGER NOT NULL,
                    chunk_text TEXT NOT NULL,
                    embedding vector({dims}) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE(reference_key, chunk_id)
                )
                """
            ).format(
                table=table_ident,
                dims=sql.Literal(dims),
            )
        )
        cursor.execute(
            sql.SQL(
                """
                CREATE INDEX IF NOT EXISTS {index}
                ON {table}(reference_key)
                """
            ).format(
                index=index_ident,
                table=table_ident,
            )
        )
    logger.info("helper_rag_schema_ready table=%s dims=%s", ".".join(table_parts), dims)
    return True


def clear_reference_rows(*, connection, reference_key: str, table_name: str = RAG_TABLE_NAME) -> int:
    if connection.vendor != "postgresql":
        return 0
    table_ident = _sql_table_identifier(table_name)
    with connection.cursor() as cursor:
        cursor.execute(
            sql.SQL("DELETE FROM {table} WHERE reference_key = %s").format(
                table=table_ident,
            ),
            [reference_key],
        )
        return int(cursor.rowcount or 0)


def upsert_reference_embeddings(
    *,
    connection,
    reference_key: str,
    source_label: str,
    chunks: tuple[str, ...],
    embedding_dimensions: int,
    embed_text_fn: Callable[[str], list[float]],
    logger: logging.Logger,
    table_name: str = RAG_TABLE_NAME,
) -> tuple[int, int]:
    """Upsert chunk embeddings for a single curriculum reference key."""
    if connection.vendor != "postgresql":
        return 0, len(chunks)
    quoted_table_name = connection.ops.quote_name(_safe_table_name(table_name))
    dims = max(int(embedding_dimensions or 0), 1)
    table_ident = _sql_table_identifier(table_name)
    written = 0
    skipped = 0
    with connection.cursor() as cursor:
        for order, chunk in enumerate(chunks):
            text = str(chunk or "").strip()
            if not text:
                skipped += 1
                continue
            vector = embed_text_fn(text)
            if len(vector) != dims:
                logger.warning(
                    "helper_rag_embedding_dim_mismatch reference=%s expected=%s got=%s",
                    reference_key,
                    dims,
                    len(vector),
                )
                skipped += 1
                continue
            chunk_id = hashlib.sha256(text.encode("utf-8")).hexdigest()[:64]
            cursor.execute(
                sql.SQL(
                    """
                    INSERT INTO {table} (
                        reference_key,
                        source_label,
                        chunk_id,
                        chunk_order,
                        chunk_text,
                        embedding,
                        updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s::vector, NOW())
                    ON CONFLICT (reference_key, chunk_id)
                    DO UPDATE
                    SET
                        source_label = EXCLUDED.source_label,
                        chunk_order = EXCLUDED.chunk_order,
                        chunk_text = EXCLUDED.chunk_text,
                        embedding = EXCLUDED.embedding,
                        updated_at = NOW()
                    """
                ).format(table=table_ident),
                [
                    reference_key,
                    source_label,
                    chunk_id,
                    order,
                    text,
                    _vector_literal(vector),
                ],
            )
            written += 1
    return written, skipped


def retrieve_curriculum_citations(
    *,
    connection,
    logger: logging.Logger,
    query_text: str,
    reference_key: str,
    max_items: int,
    max_cosine_distance: float,
    embedding_dimensions: int,
    embed_text_fn: Callable[[str], list[float]],
    table_name: str = RAG_TABLE_NAME,
) -> list[dict]:
    """Fetch nearest curriculum chunks from local pgvector index."""
    if connection.vendor != "postgresql":
        return []
    safe_table_name = _safe_table_name(table_name)
    quoted_table_name = connection.ops.quote_name(safe_table_name)
    ref = str(reference_key or "").strip().lower()
    if not SAFE_REF_KEY_RE.fullmatch(ref):
        return []
    if not _table_exists(connection=connection, table_name=safe_table_name):
        return []
    table_ident = _sql_table_identifier(table_name)
    dims = max(int(embedding_dimensions or 0), 1)
    query_vec = embed_text_fn(" ".join(str(query_text or "").split()))
    if len(query_vec) != dims:
        logger.warning("helper_rag_query_embedding_dim_mismatch expected=%s got=%s", dims, len(query_vec))
        return []
    vector = _vector_literal(query_vec)
    limit = max(int(max_items or 0), 1)
    max_distance = max(float(max_cosine_distance or 0.0), 0.0)
    with connection.cursor() as cursor:
        cursor.execute(
            sql.SQL(
                """
                SELECT
                    chunk_text,
                    source_label,
                    (embedding <=> %s::vector) AS distance
                FROM {table}
                WHERE reference_key = %s
                ORDER BY embedding <=> %s::vector ASC
                LIMIT %s
                """
            ).format(table=table_ident),
            [vector, ref, vector, limit],
        )
        rows = list(cursor.fetchall() or [])
    citations: list[dict] = []
    for idx, row in enumerate(rows, start=1):
        chunk_text = str(row[0] or "").strip()
        source_label = str(row[1] or ref).strip() or ref
        distance = float(row[2] if row[2] is not None else 9.9)
        if not chunk_text:
            continue
        if distance > max_distance:
            continue
        citations.append(
            {
                "id": f"L{idx}",
                "source": source_label,
                "text": chunk_text,
            }
        )
    return citations


def ollama_embed_text(
    *,
    base_url: str,
    model: str,
    text: str,
    timeout_seconds: int,
) -> list[float]:
    """Return a local embedding vector from Ollama (/api/embeddings or /api/embed)."""
    payload = {"model": model, "prompt": text}
    try:
        response = _post_json(
            url=f"{base_url.rstrip('/')}/api/embeddings",
            payload=payload,
            timeout_seconds=timeout_seconds,
        )
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
        response = _post_json(
            url=f"{base_url.rstrip('/')}/api/embed",
            payload={"model": model, "input": text},
            timeout_seconds=timeout_seconds,
        )
    raw = response.get("embedding")
    if raw is None and isinstance(response.get("embeddings"), list):
        embeddings = response.get("embeddings") or []
        raw = embeddings[0] if embeddings else []
    if not isinstance(raw, list):
        return []
    values: list[float] = []
    for item in raw:
        try:
            values.append(float(item))
        except (TypeError, ValueError):
            return []
    return values


def _post_json(*, url: str, payload: dict, timeout_seconds: int) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=max(int(timeout_seconds or 0), 1)) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    parsed = json.loads(raw or "{}")
    if not isinstance(parsed, dict):
        return {}
    return parsed


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


def _safe_table_name(table_name: str) -> str:
    token = str(table_name or "").strip().lower()
    if not _SAFE_TABLE_NAME_RE.fullmatch(token):
        raise ValueError("invalid_rag_table_name")
    return token


def _table_exists(*, connection, table_name: str) -> bool:
    _relation_identifier_parts(table_name)
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass(%s)", [table_name])
        row = cursor.fetchone()
    return bool(row and row[0])


def _relation_identifier_parts(table_name: str) -> tuple[str, ...]:
    raw = str(table_name or "").strip()
    parts = [part.strip() for part in raw.split(".")]
    if not raw or any(not part for part in parts):
        raise ValueError("invalid_rag_table_name")
    if len(parts) > 2:
        raise ValueError("invalid_rag_table_name")
    if not all(_IDENTIFIER_PART_RE.fullmatch(part) for part in parts):
        raise ValueError("invalid_rag_table_name")
    return tuple(parts)


def _sql_table_identifier(table_name: str) -> sql.SQL:
    return sql.Identifier(*_relation_identifier_parts(table_name))


def _sql_index_identifier(table_name: str, *, suffix: str) -> sql.SQL:
    parts = _relation_identifier_parts(table_name)
    index_name = f"{parts[-1]}_{suffix}"
    if len(parts) == 2:
        return sql.Identifier(parts[0], index_name)
    return sql.Identifier(index_name)


def _is_child_path(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


__all__ = [
    "RAG_TABLE_NAME",
    "build_reference_inventory",
    "clear_reference_rows",
    "ensure_pgvector_schema",
    "ollama_embed_text",
    "retrieve_curriculum_citations",
    "upsert_reference_embeddings",
]
