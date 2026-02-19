"""Cross-service student event hooks written into Class Hub tables.

This helper service shares the same database in deployment, so it can append
`helper_chat_access` rows into `hub_studentevent` using a best-effort insert.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache

from django.db import connection, transaction
from django.db.utils import DatabaseError

logger = logging.getLogger(__name__)


@lru_cache(maxsize=8)
def _table_exists(table_name: str) -> bool:
    try:
        with connection.cursor() as cursor:
            return table_name in set(connection.introspection.table_names(cursor))
    except DatabaseError:
        if connection.in_atomic_block:
            try:
                transaction.set_rollback(False)
            except Exception:
                pass
        return False


def emit_helper_chat_access_event(
    *,
    classroom_id: int | None,
    student_id: int | None,
    ip_address: str,
    details: dict,
) -> None:
    """Best-effort append into classhub student events table."""
    if not classroom_id and not student_id:
        return
    if not _table_exists("hub_studentevent"):
        return
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO hub_studentevent
                    (classroom_id, student_id, event_type, source, details, ip_address, created_at)
                VALUES
                    (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """,
                [
                    classroom_id or None,
                    student_id or None,
                    "helper_chat_access",
                    "homework_helper.chat",
                    json.dumps(details or {}),
                    ip_address or None,
                ],
            )
    except DatabaseError as exc:
        # This write is explicitly best-effort; do not let missing classhub tables
        # poison the caller's transaction state during tests or local-only runs.
        if connection.in_atomic_block:
            try:
                transaction.set_rollback(False)
            except Exception:
                pass
        logger.warning("helper_chat_student_event_write_failed: %s", exc.__class__.__name__)
