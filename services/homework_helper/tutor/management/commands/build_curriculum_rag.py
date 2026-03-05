from __future__ import annotations

import logging
import urllib.error

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from ...engine import rag
from ...engine import reference
from ...engine.config_source import helper_getenv
from ...views_chat_helpers import _env_int

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Build/update local curriculum-only pgvector index for Homework Helper."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reference-key",
            action="append",
            dest="reference_keys",
            default=[],
            help="Specific reference key(s) to index. Defaults to all discovered keys.",
        )
        parser.add_argument(
            "--clear-first",
            action="store_true",
            help="Delete existing rows for selected keys before upsert.",
        )

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError("Curriculum RAG requires PostgreSQL + pgvector.")

        reference_dir = (
            helper_getenv("HELPER_REFERENCE_DIR", "/app/tutor/reference") or "/app/tutor/reference"
        ).strip()
        reference_map_raw = (helper_getenv("HELPER_REFERENCE_MAP", "") or "").strip()
        embedding_model = (helper_getenv("HELPER_RAG_EMBED_MODEL", "nomic-embed-text") or "nomic-embed-text").strip()
        embedding_base_url = (
            helper_getenv("HELPER_RAG_EMBED_BASE_URL", "") or helper_getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        ).strip()
        embedding_timeout = max(_env_int("HELPER_RAG_EMBED_TIMEOUT_SECONDS", 12), 1)
        embedding_dimensions = max(_env_int("HELPER_RAG_EMBED_DIMENSIONS", 768), 1)

        inventory = rag.build_reference_inventory(reference_dir, reference_map_raw)
        if not inventory:
            raise CommandError("No curriculum references found. Check HELPER_REFERENCE_DIR / HELPER_REFERENCE_MAP.")

        selected_keys = [
            str(key or "").strip().lower()
            for key in (options.get("reference_keys") or [])
            if str(key or "").strip()
        ]
        if selected_keys:
            unknown = [key for key in selected_keys if key not in inventory]
            if unknown:
                raise CommandError(f"Unknown reference key(s): {', '.join(sorted(unknown))}")
        else:
            selected_keys = sorted(inventory.keys())

        rag.ensure_pgvector_schema(
            connection=connection,
            logger=logger,
            embedding_dimensions=embedding_dimensions,
        )

        total_written = 0
        total_skipped = 0
        total_cleared = 0

        for reference_key in selected_keys:
            reference_path = inventory[reference_key]
            chunks = reference.load_reference_chunks(reference_path, logger=logger)
            if options.get("clear_first"):
                total_cleared += rag.clear_reference_rows(
                    connection=connection,
                    reference_key=reference_key,
                )

            def _embed(text: str) -> list[float]:
                compact = " ".join(str(text or "").split())
                if not compact:
                    return []
                try:
                    return rag.ollama_embed_text(
                        base_url=embedding_base_url,
                        model=embedding_model,
                        text=compact,
                        timeout_seconds=embedding_timeout,
                    )
                except urllib.error.URLError as exc:
                    raise CommandError(f"Ollama embedding call failed for '{reference_key}': {exc}") from exc

            written, skipped = rag.upsert_reference_embeddings(
                connection=connection,
                reference_key=reference_key,
                source_label=reference_key,
                chunks=chunks,
                embedding_dimensions=embedding_dimensions,
                embed_text_fn=_embed,
                logger=logger,
            )
            total_written += written
            total_skipped += skipped
            self.stdout.write(
                self.style.SUCCESS(
                    f"[helper-rag] indexed {reference_key}: {written} chunks written, {skipped} skipped"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                "[helper-rag] complete "
                f"keys={len(selected_keys)} written={total_written} skipped={total_skipped} cleared={total_cleared}"
            )
        )
