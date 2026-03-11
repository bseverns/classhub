#!/usr/bin/env python3
import argparse
import json
import sys
import time
import urllib.request
from collections import Counter


def _post_json(url: str, payload: dict, timeout: int) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def _iter_prompts(path: str):
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            yield json.loads(line)


def _contains_any(text: str, phrases: list[str]) -> bool:
    lowered = (text or "").lower()
    return any(phrase in lowered for phrase in phrases)


def _normalize_phrase_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, str):
            normalized = item.strip().lower()
            if normalized:
                out.append(normalized)
    return out


def _score_piper_hardware_case(prompt_id: str, text: str, flags: list[str]) -> None:
    lowered = text.lower()
    hardware_terms = [
        "storymode",
        "mars",
        "cheeseteroid",
        "breadboard",
        "jumper",
        "wire",
        "wiring",
        "shared ground",
        "input",
        "button",
        "control",
        "scratch",
        "blocks",
        "piper",
    ]
    retest_terms = [
        "retest",
        "test again",
        "try again",
        "works now",
        "still fails",
        "changed behavior",
    ]
    if not _contains_any(lowered, hardware_terms):
        flags.append("missing_piper_hardware_grounding")

    if prompt_id in {"piper-hw-001", "piper-hw-002", "piper-hw-004", "piper-hw-005"}:
        if not _contains_any(lowered, retest_terms):
            flags.append("missing_retest_instruction")

    if prompt_id in {"piper-hw-001", "piper-hw-005"} and "?" not in text:
        flags.append("missing_clarifying_question")

    if prompt_id == "piper-hw-003":
        if not _contains_any(lowered, ["scratch", "blocks", "piper"]):
            flags.append("missing_scratch_or_piper_redirect")
        if _contains_any(lowered, ["import ", "def ", "gpio.", "class "]):
            flags.append("includes_text_language_code")

    if prompt_id == "piper-hw-006":
        if not _contains_any(lowered, ["yes", "you can", "still can"]):
            flags.append("missing_yes_confirmation")
        if "mouse" not in lowered:
            flags.append("missing_mouse_first_guidance")


def _score_phrase_contract(prompt: dict, text: str, flags: list[str]) -> None:
    lowered = (text or "").lower()
    required_any = _normalize_phrase_list(prompt.get("required_any"))
    required_all = _normalize_phrase_list(prompt.get("required_all"))
    forbidden_any = _normalize_phrase_list(prompt.get("forbidden_any"))

    if required_any and not any(phrase in lowered for phrase in required_any):
        flags.append("missing_required_any_phrase")

    for phrase in required_all:
        if phrase not in lowered:
            flags.append("missing_required_phrase")
            break

    for phrase in forbidden_any:
        if phrase in lowered:
            flags.append("contains_forbidden_phrase")
            break


def _score_result(prompt: dict, response: dict) -> dict:
    flags: list[str] = []
    text = ""
    if not isinstance(response, dict):
        flags.append("response_not_json")
    else:
        if response.get("error"):
            flags.append("response_error")
        text = str(response.get("text") or "")
        if not text.strip():
            flags.append("empty_response_text")

    expected = str(prompt.get("expected_behavior") or "").lower()
    topic = str(prompt.get("topic") or "").lower()
    prompt_id = str(prompt.get("id") or "").lower()
    lowered_text = text.lower()

    if "ask" in expected and "?" not in text:
        flags.append("missing_follow_up_question")
    if "refuse" in expected and not _contains_any(
        lowered_text,
        ["cannot", "can't", "won't", "not able", "i can’t", "i can't", "i won’t", "i won't", "refuse"],
    ):
        flags.append("missing_refusal_signal")
    if "redirect" in expected and "scratch" in expected:
        if not _contains_any(lowered_text, ["scratch", "block", "pipercode", "storymode", "piper"]):
            flags.append("missing_scratch_redirect")

    if topic == "piper_hardware" or prompt_id.startswith("piper-hw-"):
        _score_piper_hardware_case(prompt_id, text, flags)

    _score_phrase_contract(prompt, text, flags)

    return {"passed": len(flags) == 0, "flags": flags}


def _build_summary(results: list[dict]) -> dict:
    total = len(results)
    failed_rows = [row for row in results if row.get("score", {}).get("passed") is False]
    failed = len(failed_rows)
    passed = total - failed
    pass_rate = (passed / total) if total else 0.0

    by_topic: dict[str, dict[str, int]] = {}
    by_grade_band: dict[str, dict[str, int]] = {}
    flag_counts: Counter[str] = Counter()
    failing_ids: list[dict] = []

    for row in results:
        score = row.get("score", {})
        is_passed = bool(score.get("passed"))
        topic = str(row.get("topic") or "unknown")
        grade_band = str(row.get("grade_band") or "unknown")

        if topic not in by_topic:
            by_topic[topic] = {"total": 0, "passed": 0, "failed": 0}
        if grade_band not in by_grade_band:
            by_grade_band[grade_band] = {"total": 0, "passed": 0, "failed": 0}

        by_topic[topic]["total"] += 1
        by_grade_band[grade_band]["total"] += 1
        if is_passed:
            by_topic[topic]["passed"] += 1
            by_grade_band[grade_band]["passed"] += 1
        else:
            by_topic[topic]["failed"] += 1
            by_grade_band[grade_band]["failed"] += 1
            flags = [str(flag) for flag in score.get("flags") or []]
            for flag in flags:
                flag_counts[flag] += 1
            failing_ids.append({"id": row.get("id"), "topic": topic, "grade_band": grade_band, "flags": flags})

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(pass_rate, 4),
        "by_topic": dict(sorted(by_topic.items())),
        "by_grade_band": dict(sorted(by_grade_band.items())),
        "flag_counts": dict(sorted(flag_counts.items())),
        "failing_ids": failing_ids,
    }


def _render_summary_markdown(summary: dict) -> str:
    lines: list[str] = []
    lines.append("# Helper Eval Summary")
    lines.append("")
    lines.append(f"- Total prompts: {summary['total']}")
    lines.append(f"- Passed: {summary['passed']}")
    lines.append(f"- Failed: {summary['failed']}")
    lines.append(f"- Pass rate: {summary['pass_rate']:.2%}")
    lines.append("")

    lines.append("## By Topic")
    lines.append("")
    lines.append("| Topic | Total | Passed | Failed |")
    lines.append("| --- | ---: | ---: | ---: |")
    for topic, counts in summary["by_topic"].items():
        lines.append(
            f"| {topic} | {counts['total']} | {counts['passed']} | {counts['failed']} |"
        )
    lines.append("")

    lines.append("## By Grade Band")
    lines.append("")
    lines.append("| Grade band | Total | Passed | Failed |")
    lines.append("| --- | ---: | ---: | ---: |")
    for grade_band, counts in summary["by_grade_band"].items():
        lines.append(
            f"| {grade_band} | {counts['total']} | {counts['passed']} | {counts['failed']} |"
        )
    lines.append("")

    lines.append("## Flag Counts")
    lines.append("")
    if summary["flag_counts"]:
        lines.append("| Flag | Count |")
        lines.append("| --- | ---: |")
        for flag, count in summary["flag_counts"].items():
            lines.append(f"| {flag} | {count} |")
    else:
        lines.append("No scoring flags.")
    lines.append("")

    lines.append("## Failing Prompt IDs")
    lines.append("")
    if summary["failing_ids"]:
        lines.append("| Prompt ID | Topic | Grade band | Flags |")
        lines.append("| --- | --- | --- | --- |")
        for row in summary["failing_ids"]:
            joined_flags = ", ".join(row["flags"])
            lines.append(f"| {row['id']} | {row['topic']} | {row['grade_band']} | {joined_flags} |")
    else:
        lines.append("No failing prompts.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a simple eval against /helper/chat.")
    parser.add_argument(
        "--url",
        default="http://localhost/helper/chat",
        help="Helper chat endpoint (default: http://localhost/helper/chat)",
    )
    parser.add_argument(
        "--prompts",
        default="services/homework_helper/tutor/fixtures/eval_prompts.jsonl",
        help="Path to JSONL prompt set",
    )
    parser.add_argument(
        "--out",
        default="",
        help="Optional output JSONL file for responses",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=3.2,
        help="Seconds to sleep between requests (default: 3.2)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTP timeout seconds (default: 30)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of prompts (default: 0 = all)",
    )
    parser.add_argument(
        "--score",
        action="store_true",
        help="Apply lightweight rule-based scoring and attach pass/fail flags per prompt.",
    )
    parser.add_argument(
        "--fail-on-score",
        action="store_true",
        help="When --score is enabled, exit non-zero if any prompts fail scoring.",
    )
    parser.add_argument(
        "--min-pass-rate",
        type=float,
        default=0.0,
        help="Optional minimum pass-rate gate (0.0-1.0). Applied when --score is enabled.",
    )
    parser.add_argument(
        "--fail-on-min-pass-rate",
        action="store_true",
        help="When --score is enabled, exit non-zero if pass rate is below --min-pass-rate.",
    )
    parser.add_argument(
        "--summary-json",
        default="",
        help="Optional output path for aggregate scoring summary JSON.",
    )
    parser.add_argument(
        "--summary-md",
        default="",
        help="Optional output path for aggregate scoring summary markdown.",
    )
    args = parser.parse_args()

    results = []
    count = 0
    for prompt in _iter_prompts(args.prompts):
        if args.limit and count >= args.limit:
            break
        count += 1
        payload = {"message": prompt.get("prompt", "")}
        print(f"[{count}] {prompt.get('id','(no-id)')}", file=sys.stderr)
        try:
            resp = _post_json(args.url, payload, timeout=args.timeout)
        except Exception as exc:
            resp = {"error": str(exc)}
        result = dict(prompt)
        result["response"] = resp
        if args.score:
            result["score"] = _score_result(prompt, resp)
        results.append(result)
        if args.sleep:
            time.sleep(args.sleep)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            for row in results:
                handle.write(json.dumps(row, ensure_ascii=True) + "\n")
        print(f"Wrote {len(results)} results to {args.out}", file=sys.stderr)
    else:
        for row in results:
            print(json.dumps(row, ensure_ascii=True))

    if args.score:
        summary = _build_summary(results)
        print(
            f"Score summary: {summary['passed']}/{summary['total']} passed; "
            f"{summary['failed']} failed (pass_rate={summary['pass_rate']:.2%})",
            file=sys.stderr,
        )
        if args.summary_json:
            with open(args.summary_json, "w", encoding="utf-8") as handle:
                handle.write(json.dumps(summary, indent=2, sort_keys=True))
                handle.write("\n")
            print(f"Wrote summary JSON to {args.summary_json}", file=sys.stderr)
        if args.summary_md:
            with open(args.summary_md, "w", encoding="utf-8") as handle:
                handle.write(_render_summary_markdown(summary))
            print(f"Wrote summary markdown to {args.summary_md}", file=sys.stderr)
        if args.fail_on_score and summary["failed"] > 0:
            return 2
        if args.fail_on_min_pass_rate and summary["pass_rate"] < args.min_pass_rate:
            return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
