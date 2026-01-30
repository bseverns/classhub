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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
