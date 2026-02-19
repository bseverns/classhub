#!/usr/bin/env python3
import argparse
import json
import sys
import time
import urllib.request


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

    return {"passed": len(flags) == 0, "flags": flags}


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
        result = {
            "id": prompt.get("id"),
            "grade_band": prompt.get("grade_band"),
            "topic": prompt.get("topic"),
            "prompt": prompt.get("prompt"),
            "expected_behavior": prompt.get("expected_behavior"),
            "response": resp,
        }
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
        total = len(results)
        failed = sum(1 for row in results if not row.get("score", {}).get("passed", False))
        passed = total - failed
        print(f"Score summary: {passed}/{total} passed; {failed} failed", file=sys.stderr)
        if args.fail_on_score and failed > 0:
            return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
