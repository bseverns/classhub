#!/usr/bin/env python3
"""Render telemetry Slice 7 SLO summary markdown from explicit measurements."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class SignalAssessment:
    label: str
    baseline_label: str
    observed_label: str
    status: str
    detail: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="Markdown output path.")
    parser.add_argument("--release-date", default="")
    parser.add_argument("--window-days", type=int, default=7)
    parser.add_argument("--student-home-p95-ms", type=float, default=None)
    parser.add_argument("--student-home-p95-baseline-ms", type=float, default=None)
    parser.add_argument("--student-upload-success-rate-pct", type=float, default=None)
    parser.add_argument("--student-upload-success-rate-baseline-pct", type=float, default=None)
    parser.add_argument("--helper-chat-5xx-rate-pct", type=float, default=None)
    parser.add_argument("--helper-chat-5xx-rate-baseline-pct", type=float, default=None)
    parser.add_argument("--parity-threshold-label", default="strict zero drift")
    parser.add_argument("--steady-write-mode-label", default="remain `dual`")
    parser.add_argument("--gate-d-label", default="deferred to next cycle")
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    assessments = build_assessments(args)
    overall_status = summarize_status(assessments)
    output = render_markdown(args=args, assessments=assessments, overall_status=overall_status)
    Path(args.out).write_text(output, encoding="utf-8")
    if args.require_complete and overall_status == "pending":
        return 1
    if args.require_pass and overall_status != "pass":
        return 1
    return 0


def build_assessments(args: argparse.Namespace) -> list[SignalAssessment]:
    return [
        assess_student_home_latency(
            baseline_ms=args.student_home_p95_baseline_ms,
            observed_ms=args.student_home_p95_ms,
        ),
        assess_upload_success(
            baseline_pct=args.student_upload_success_rate_baseline_pct,
            observed_pct=args.student_upload_success_rate_pct,
        ),
        assess_helper_5xx_rate(
            baseline_pct=args.helper_chat_5xx_rate_baseline_pct,
            observed_pct=args.helper_chat_5xx_rate_pct,
        ),
    ]


def assess_student_home_latency(*, baseline_ms: float | None, observed_ms: float | None) -> SignalAssessment:
    if baseline_ms is None or observed_ms is None:
        return SignalAssessment(
            label="Student home p95 latency",
            baseline_label=format_value(baseline_ms, suffix=" ms"),
            observed_label=format_value(observed_ms, suffix=" ms"),
            status="pending",
            detail="Need both pre-cutover baseline and observed 7-day p95.",
        )
    threshold_ms = baseline_ms * 1.10
    if observed_ms <= threshold_ms:
        return SignalAssessment(
            label="Student home p95 latency",
            baseline_label=format_value(baseline_ms, suffix=" ms"),
            observed_label=format_value(observed_ms, suffix=" ms"),
            status="pass",
            detail=f"Observed p95 stays within +10% of the {baseline_ms:.1f} ms baseline.",
        )
    return SignalAssessment(
        label="Student home p95 latency",
        baseline_label=format_value(baseline_ms, suffix=" ms"),
        observed_label=format_value(observed_ms, suffix=" ms"),
        status="fail",
        detail=f"Observed p95 exceeds the +10% guardrail ({threshold_ms:.1f} ms).",
    )


def assess_upload_success(*, baseline_pct: float | None, observed_pct: float | None) -> SignalAssessment:
    if baseline_pct is None or observed_pct is None:
        return SignalAssessment(
            label="Student upload success rate",
            baseline_label=format_value(baseline_pct, suffix="%"),
            observed_label=format_value(observed_pct, suffix="%"),
            status="pending",
            detail="Need both 30-day pre-cutover baseline and observed release-window success rate.",
        )
    floor = max(99.0, baseline_pct - 0.5)
    if observed_pct >= floor:
        return SignalAssessment(
            label="Student upload success rate",
            baseline_label=format_value(baseline_pct, suffix="%"),
            observed_label=format_value(observed_pct, suffix="%"),
            status="pass",
            detail=f"Observed success stays above the required floor ({floor:.2f}%).",
        )
    return SignalAssessment(
        label="Student upload success rate",
        baseline_label=format_value(baseline_pct, suffix="%"),
        observed_label=format_value(observed_pct, suffix="%"),
        status="fail",
        detail=f"Observed success falls below the required floor ({floor:.2f}%).",
    )


def assess_helper_5xx_rate(*, baseline_pct: float | None, observed_pct: float | None) -> SignalAssessment:
    if baseline_pct is None or observed_pct is None:
        return SignalAssessment(
            label="Helper chat 5xx rate",
            baseline_label=format_value(baseline_pct, suffix="%"),
            observed_label=format_value(observed_pct, suffix="%"),
            status="pending",
            detail="Need both 30-day pre-cutover baseline and observed release-window 5xx rate.",
        )
    ceiling = min(1.0, baseline_pct + 0.5)
    if observed_pct <= ceiling:
        return SignalAssessment(
            label="Helper chat 5xx rate",
            baseline_label=format_value(baseline_pct, suffix="%"),
            observed_label=format_value(observed_pct, suffix="%"),
            status="pass",
            detail=f"Observed 5xx rate stays below the required ceiling ({ceiling:.2f}%).",
        )
    return SignalAssessment(
        label="Helper chat 5xx rate",
        baseline_label=format_value(baseline_pct, suffix="%"),
        observed_label=format_value(observed_pct, suffix="%"),
        status="fail",
        detail=f"Observed 5xx rate exceeds the required ceiling ({ceiling:.2f}%).",
    )


def summarize_status(assessments: list[SignalAssessment]) -> str:
    statuses = {assessment.status for assessment in assessments}
    if "fail" in statuses:
        return "fail"
    if "pending" in statuses:
        return "pending"
    return "pass"


def render_markdown(*, args: argparse.Namespace, assessments: list[SignalAssessment], overall_status: str) -> str:
    lines = [
        "# Telemetry Slice 7 SLO Summary",
        "",
        f"- Generated at (UTC): {datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"- Release date: {args.release_date or 'n/a'}",
        f"- Window days: {args.window_days}",
        f"- Overall status: {overall_status.upper()}",
        "",
        "## Signal Review",
        "",
        "| Signal | Baseline | Observed | Status | Detail |",
        "| --- | --- | --- | --- | --- |",
    ]
    for assessment in assessments:
        lines.append(
            f"| {assessment.label} | {assessment.baseline_label} | {assessment.observed_label} | "
            f"{assessment.status.upper()} | {assessment.detail} |"
        )
    lines.extend(
        [
            "",
            "## Policy",
            "",
            f"- Parity threshold for this cycle: {args.parity_threshold_label}.",
            f"- Steady-state write mode decision for this cycle: {args.steady_write_mode_label}.",
            f"- Gate D (`telemetry_only`) decision: {args.gate_d_label}.",
        ]
    )
    if overall_status == "pending":
        lines.extend(
            [
                "",
                "## Follow-up",
                "",
                "- Populate the missing baseline/observed values before telemetry closeout sign-off.",
            ]
        )
    return "\n".join(lines) + "\n"


def format_value(value: float | None, *, suffix: str) -> str:
    if value is None:
        return "pending"
    return f"{value:.2f}{suffix}"


if __name__ == "__main__":
    raise SystemExit(main())
