"""Auth/session boundary helpers for helper requests."""

from __future__ import annotations

from django.db.utils import DatabaseError


def table_exists(*, connection, transaction_module, table_name: str) -> bool:
    try:
        with connection.cursor() as cursor:
            return table_name in set(connection.introspection.table_names(cursor))
    except DatabaseError:
        if connection.in_atomic_block:
            try:
                transaction_module.set_rollback(False)
            except Exception:
                pass
        return False


def student_session_exists(
    *,
    connection,
    transaction_module,
    settings,
    student_id: int,
    class_id: int,
    table_exists_fn,
) -> bool:
    if not table_exists_fn("hub_studentidentity"):
        if bool(getattr(settings, "HELPER_REQUIRE_CLASSHUB_TABLE", False)):
            return False
        return True
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM hub_studentidentity WHERE id = %s AND classroom_id = %s LIMIT 1",
                [student_id, class_id],
            )
            return cursor.fetchone() is not None
    except DatabaseError:
        # Postgres marks the transaction as aborted after SQL errors; clear the
        # rollback flag so this best-effort check doesn't poison the request.
        if connection.in_atomic_block:
            try:
                transaction_module.set_rollback(False)
            except Exception:
                pass
        # MVP default is fail-open for local/demo setups; production can force
        # fail-closed by enabling HELPER_REQUIRE_CLASSHUB_TABLE.
        if bool(getattr(settings, "HELPER_REQUIRE_CLASSHUB_TABLE", False)):
            return False
        return True


def actor_key(*, request, build_actor_key_fn, student_session_exists_fn) -> str:
    key = build_actor_key_fn(request)
    if not key:
        return ""
    if key.startswith("student:"):
        student_id = request.session.get("student_id")
        class_id = request.session.get("class_id")
        if not (student_id and class_id):
            return ""
        if not student_session_exists_fn(student_id, class_id):
            return ""
    return key

