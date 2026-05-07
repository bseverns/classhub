#!/usr/bin/env python3
"""Capture unattended remote-compute operator evidence and optional alerts."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib import error, request

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = ROOT_DIR / "compose" / ".env"


def parse_args() -> argparse.Namespace:
    stamp = datetime.now(UTC)
    default_out_dir = ROOT_DIR / "artifacts" / "stability" / stamp.strftime("%Y-%m-%d")
    default_out_dir /= f"remote_compute_watch_{stamp.strftime('%H%M%SZ')}"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compose-mode", default=os.environ.get("COMPOSE_MODE", "prod"))
    parser.add_argument("--out-dir", default=os.environ.get("REMOTE_COMPUTE_WATCH_OUT_DIR", str(default_out_dir)))
    parser.add_argument("--alert-webhook-url", default=os.environ.get("REMOTE_COMPUTE_ALERT_WEBHOOK_URL", ""))
    parser.add_argument(
        "--command-timeout-seconds",
        type=int,
        default=int(os.environ.get("REMOTE_COMPUTE_WATCH_TIMEOUT_SECONDS", "30") or 30),
    )
    parser.add_argument("--alert-on-success", action="store_true")
    parser.add_argument("--fail-on-watch", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.alert_on_success = args.alert_on_success or env_flag("REMOTE_COMPUTE_ALERT_ON_SUCCESS")
    args.fail_on_watch = args.fail_on_watch or env_flag("REMOTE_COMPUTE_FAIL_ON_WATCH")
    ensure_runtime_prereqs(compose_mode=args.compose_mode)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stdout_text, stderr_text, snapshot = run_snapshot_capture(
        compose_mode=args.compose_mode,
        timeout_seconds=max(args.command_timeout_seconds, 5),
    )
    report = build_report(
        compose_mode=args.compose_mode,
        out_dir=out_dir,
        snapshot=snapshot,
        stderr_text=stderr_text,
        fail_on_watch=args.fail_on_watch,
    )
    write_artifacts(
        out_dir=out_dir,
        stdout_text=stdout_text,
        stderr_text=stderr_text,
        snapshot=snapshot,
        report=report,
    )
    maybe_notify(report=report, webhook_url=args.alert_webhook_url, alert_on_success=args.alert_on_success)
    print(report["message"])
    return int(report["exit_code"])


def env_flag(name: str) -> bool:
    return str(os.environ.get(name, "0") or "0").strip().lower() in {"1", "true", "yes", "on"}


def ensure_runtime_prereqs(*, compose_mode: str) -> None:
    if compose_mode not in {"prod", "dev"}:
        raise SystemExit("[remote-compute-watch] --compose-mode must be prod or dev")
    if not DEFAULT_ENV_FILE.exists():
        raise SystemExit("[remote-compute-watch] missing compose/.env (copy from compose/.env.example first)")
    if not shutil_which("docker"):
        raise SystemExit("[remote-compute-watch] docker is required")


def shutil_which(binary: str) -> str:
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(entry) / binary
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return ""


def run_snapshot_capture(*, compose_mode: str, timeout_seconds: int) -> tuple[str, str, dict]:
    command = compose_command(compose_mode=compose_mode)
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT_DIR,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise SystemExit(
            f"[remote-compute-watch] timed out waiting for classhub_web snapshot export after {timeout_seconds}s"
        ) from exc
    stdout_text = completed.stdout or ""
    stderr_text = completed.stderr or ""
    if completed.returncode != 0:
        return stdout_text, stderr_text, {"status": "error", "error_code": "compose_exec_failed"}
    try:
        snapshot = json.loads(stdout_text or "{}")
    except json.JSONDecodeError:
        snapshot = {"status": "error", "error_code": "invalid_snapshot_json"}
    if not isinstance(snapshot, dict):
        snapshot = {"status": "error", "error_code": "invalid_snapshot_json"}
    return stdout_text, stderr_text, snapshot


def compose_command(*, compose_mode: str) -> list[str]:
    command = [
        "docker",
        "compose",
        "-f",
        str(ROOT_DIR / "compose" / "docker-compose.yml"),
    ]
    if compose_mode == "dev":
        command.extend(["-f", str(ROOT_DIR / "compose" / "docker-compose.override.yml")])
    command.extend(
        [
            "exec",
            "-T",
            "classhub_web",
            "python",
            "manage.py",
            "export_remote_compute_operator_snapshot",
        ]
    )
    return command


def build_report(*, compose_mode: str, out_dir: Path, snapshot: dict, stderr_text: str, fail_on_watch: bool) -> dict:
    captured_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    snapshot_status = str(snapshot.get("status") or "error")
    aggregate_signal = snapshot.get("aggregate_signal") if isinstance(snapshot.get("aggregate_signal"), dict) else {}
    recent_classes = snapshot.get("recent_classes") if isinstance(snapshot.get("recent_classes"), list) else []
    attention_ids = class_ids_for_level(recent_classes=recent_classes, level="attention")
    watch_ids = class_ids_for_level(recent_classes=recent_classes, level="watch")

    overall_state = "pass"
    if snapshot_status != "ok":
        overall_state = "fail"
    elif str(aggregate_signal.get("level") or "") == "attention" or attention_ids:
        overall_state = "fail"
    elif str(aggregate_signal.get("level") or "") == "watch" or watch_ids:
        overall_state = "watch"

    exit_code = 1 if overall_state == "fail" or (overall_state == "watch" and fail_on_watch) else 0
    active_lease = snapshot.get("active_lease") if isinstance(snapshot.get("active_lease"), dict) else {}
    message = build_message(
        out_dir=out_dir,
        overall_state=overall_state,
        snapshot_status=snapshot_status,
        aggregate_signal=aggregate_signal,
        attention_ids=attention_ids,
        watch_ids=watch_ids,
        active_lease=active_lease,
    )
    return {
        "captured_at_utc": captured_at,
        "compose_mode": compose_mode,
        "overall_state": overall_state,
        "snapshot_status": snapshot_status,
        "aggregate_signal": aggregate_signal,
        "attention_class_ids": attention_ids,
        "watch_class_ids": watch_ids,
        "active_lease": active_lease,
        "stderr_present": bool(stderr_text.strip()),
        "message": message,
        "exit_code": exit_code,
    }


def class_ids_for_level(*, recent_classes: list[dict], level: str) -> list[int]:
    class_ids: list[int] = []
    for row in recent_classes:
        signal = row.get("signal") if isinstance(row.get("signal"), dict) else {}
        if str(signal.get("level") or "") != level:
            continue
        try:
            class_id = int(row.get("class_id") or 0)
        except Exception:
            class_id = 0
        if class_id > 0:
            class_ids.append(class_id)
    return class_ids


def build_message(
    *,
    out_dir: Path,
    overall_state: str,
    snapshot_status: str,
    aggregate_signal: dict,
    attention_ids: list[int],
    watch_ids: list[int],
    active_lease: dict,
) -> str:
    label = {"pass": "PASS", "watch": "WATCH", "fail": "FAIL"}.get(overall_state, "FAIL")
    parts = [f"[remote-compute-watch] {label}: snapshot={snapshot_status}"]
    summary = str(aggregate_signal.get("summary") or "").strip()
    if summary:
        parts.append(summary)
    if attention_ids:
        parts.append(f"attention class ids={','.join(str(value) for value in attention_ids)}")
    elif watch_ids:
        parts.append(f"watch class ids={','.join(str(value) for value in watch_ids)}")
    active_class_id = safe_int(active_lease.get("class_id"))
    active_state = str(active_lease.get("state") or "").strip()
    if active_class_id > 0 and active_state:
        parts.append(f"active lease class={active_class_id} state={active_state}")
    parts.append(f"artifacts={out_dir}")
    return "; ".join(parts)


def write_artifacts(*, out_dir: Path, stdout_text: str, stderr_text: str, snapshot: dict, report: dict) -> None:
    snapshot_path = out_dir / "remote_compute_operator_snapshot.json"
    report_path = out_dir / "remote_compute_operator_report.json"
    summary_path = out_dir / "remote_compute_operator_summary.md"
    log_path = out_dir / "remote_compute_operator_watch.log"
    snapshot_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary_path.write_text(render_summary(report=report), encoding="utf-8")
    log_path.write_text(render_log(stdout_text=stdout_text, stderr_text=stderr_text), encoding="utf-8")


def render_summary(*, report: dict) -> str:
    aggregate_signal = report.get("aggregate_signal") if isinstance(report.get("aggregate_signal"), dict) else {}
    active_lease = report.get("active_lease") if isinstance(report.get("active_lease"), dict) else {}
    lines = [
        "### Remote Compute Operator Watch",
        f"- Captured (UTC): {report.get('captured_at_utc')}",
        f"- Compose mode: {report.get('compose_mode')}",
        f"- Overall state: {str(report.get('overall_state') or '').upper()}",
        f"- Snapshot status: {report.get('snapshot_status')}",
        f"- Aggregate signal level: {aggregate_signal.get('level', '')}",
        f"- Aggregate signal summary: {aggregate_signal.get('summary', '')}",
        f"- Aggregate signal detail: {aggregate_signal.get('detail', '')}",
        f"- Attention class ids: {csv_or_none(report.get('attention_class_ids'))}",
        f"- Watch class ids: {csv_or_none(report.get('watch_class_ids'))}",
        f"- Active lease class id: {active_lease.get('class_id', 0)}",
        f"- Active lease state: {active_lease.get('state', '')}",
        f"- Active lease remaining minutes: {active_lease.get('remaining_minutes', 0)}",
        f"- stderr present: {'yes' if report.get('stderr_present') else 'no'}",
        f"- Message: {report.get('message')}",
    ]
    return "\n".join(lines) + "\n"


def csv_or_none(values) -> str:
    if not values:
        return "none"
    return ",".join(str(value) for value in values)


def render_log(*, stdout_text: str, stderr_text: str) -> str:
    return "\n".join(
        [
            "### stdout",
            stdout_text.rstrip(),
            "",
            "### stderr",
            stderr_text.rstrip(),
            "",
        ]
    )


def maybe_notify(*, report: dict, webhook_url: str, alert_on_success: bool) -> None:
    overall_state = str(report.get("overall_state") or "fail")
    should_notify = overall_state != "pass" or alert_on_success
    if not should_notify or not webhook_url:
        return
    status = {"pass": "success", "watch": "warning", "fail": "failure"}.get(overall_state, "failure")
    payload = json.dumps({"status": status, "text": str(report.get("message") or "")}).encode("utf-8")
    req = request.Request(
        webhook_url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with request.urlopen(req, timeout=5):  # nosec B310
            return
    except (error.URLError, TimeoutError):
        return


def safe_int(value) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
