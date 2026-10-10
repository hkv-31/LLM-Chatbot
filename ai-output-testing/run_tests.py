"""
Dataset-based output test runner for the hkv-31/LLM-Chatbot project.

This repository serves a browser UI from app.py using Python's standard-library
HTTP server; it is not necessarily a FastAPI JSON endpoint. The runner therefore
supports two modes:
  1) HTTP mode: set TEST_API_URL and TEST_REQUEST_FIELD to an existing JSON API.
  2) Direct mode: set TEST_MODE=direct to call Groq via the Groq SDK using the
     same GROQ_API_KEY and optional GROQ_MODEL environment variables.

For the repository as currently documented, direct mode is the simplest reliable
starting point. It tests the configured Groq model but does not exercise the
browser server's HTTP route. See README.md for details.
"""
import csv
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
# Load the chatbot repository's root .env when this folder is nested inside it.
try:
    from dotenv import load_dotenv
    load_dotenv(HERE.parent / ".env")
    load_dotenv(HERE / ".env")
except ImportError:
    pass
DATASET_PATH = Path(os.getenv("TEST_DATASET", HERE / "test_dataset.csv"))
RESULTS_PATH = Path(os.getenv("TEST_RESULTS", HERE / "test_results.csv"))
MODE = os.getenv("TEST_MODE", "direct").strip().lower()
API_URL = os.getenv("TEST_API_URL", "").strip()
REQUEST_FIELD = os.getenv("TEST_REQUEST_FIELD", "prompt").strip()
RESPONSE_FIELD = os.getenv("TEST_RESPONSE_FIELD", "").strip()
API_KEY = os.getenv("TEST_API_KEY", "").strip()
API_KEY_HEADER = os.getenv("TEST_API_KEY_HEADER", "Authorization").strip()
API_KEY_PREFIX = os.getenv("TEST_API_KEY_PREFIX", "Bearer ").strip()
TIMEOUT = float(os.getenv("TEST_TIMEOUT_SECONDS", "60"))


def word_count(text):
    return len(re.findall(r"\b[\w'-]+\b", text))


def extract_response(payload):
    """Extract likely text fields from a JSON response, or stringify the payload."""
    if RESPONSE_FIELD:
        value = payload
        for part in RESPONSE_FIELD.split("."):
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = None
                break
        if isinstance(value, str):
            return value
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        for key in ("response", "answer", "reply", "message", "output", "content", "text"):
            value = payload.get(key)
            if isinstance(value, str):
                return value
        # A valid JSON response without a conventional answer field is still retained.
        return json.dumps(payload, ensure_ascii=False)
    return str(payload)



def call_direct(prompt):
    """Call Groq using the Chat Completions API."""
    from groq import Groq

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing. Check your repository's .env file."
        )

    client = Groq(api_key=api_key)
    model = os.getenv("GROQ_MODEL", "").strip() or "openai/gpt-oss-20b"

    result = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    response = result.choices[0].message.content
    return response or ""


def call_http(prompt):
    if not API_URL:
        raise RuntimeError("TEST_API_URL is required when TEST_MODE=http.")
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers[API_KEY_HEADER] = f"{API_KEY_PREFIX}{API_KEY}"
    response = requests.post(API_URL, headers=headers, json={REQUEST_FIELD: prompt}, timeout=TIMEOUT)
    if not response.ok:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text[:500]}")
    try:
        payload = response.json()
    except ValueError:
        return response.text
    return extract_response(payload)


def evaluate(row, response, error=None):
    checks = set(filter(None, (row.get("checks") or "").split(";")))
    failures = []
    if error:
        return False, f"request_error: {error}"
    if "invalid_input" in checks:
        # The blank-input case is intentionally tested locally; do not send it to an LLM.
        return False, "invalid_input test should be handled by runner, not evaluated as model output"
    if "non_empty" in checks and not response.strip():
        failures.append("empty_response")
    keywords = [k.strip().lower() for k in (row.get("expected_keywords") or "").split(",") if k.strip()]
    if "keywords" in checks and keywords and not any(k in response.lower() for k in keywords):
        failures.append("none_of_expected_keywords_found: " + ", ".join(keywords))
    fmt = (row.get("expected_format") or "").strip().lower()
    if "format" in checks:
        if fmt == "bullet" and not re.search(r"(?m)^\s*([-*•]|\d+[.)])\s+", response):
            failures.append("expected_bullet_or_list_format")
        elif fmt == "numbered_list":
            numbers = re.findall(r"(?m)^\s*\d+[.)]\s+", response)
            if len(numbers) != 3:
                failures.append(f"expected_3_numbered_items_found_{len(numbers)}")
        elif fmt == "json":
            try:
                obj = json.loads(response.strip())
                if not isinstance(obj, dict) or obj.get("name") != "Ada" or obj.get("language") != "Python":
                    failures.append("json_keys_or_values_mismatch")
            except Exception:
                failures.append("invalid_json_output")
        elif fmt == "number_only" and response.strip() != "4":
            failures.append("expected_exact_output_4")
    if "max_words" in checks:
        limit = int(row.get("max_words") or row.get("max_response_words") or 0)
        if limit and word_count(response) > limit:
            failures.append(f"too_long_{word_count(response)}_words_limit_{limit}")
    return not failures, "; ".join(failures)


def main():
    if not DATASET_PATH.exists():
        raise SystemExit(f"Dataset not found: {DATASET_PATH}")
    with DATASET_PATH.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    results = []
    for row in rows:
        test_id = row.get("test_id", "")
        prompt = row.get("prompt", "")
        start = time.perf_counter()
        response_text = ""
        error = ""
        # Empty-input case tests local validation and intentionally makes no network call.
        if "invalid_input" in (row.get("checks") or ""):
            passed = not prompt.strip()
            failure_reason = "" if passed else "blank_input_case_not_blank"
            response_text = "[Not sent to model: blank input rejected locally]"
        else:
            try:
                if MODE == "direct":
                    response_text = call_direct(prompt)
                elif MODE == "http":
                    response_text = call_http(prompt)
                else:
                    raise RuntimeError("TEST_MODE must be 'direct' or 'http'.")
                passed, failure_reason = evaluate(row, response_text)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                passed, failure_reason = False, "request_error: " + error
        elapsed = round(time.perf_counter() - start, 3)
        results.append({
            "test_id": test_id,
            "prompt": prompt,
            "actual_response": response_text,
            "result": "PASS" if passed else "FAIL",
            "failure_reason": failure_reason,
            "execution_time_seconds": elapsed,
            "category": row.get("category", ""),
            "run_timestamp_utc": datetime.now(timezone.utc).astimezone(
                                    timezone(__import__("datetime").timedelta(hours=5, minutes=30))
                                ).isoformat()
        })
        print(f"{test_id}: {'PASS' if passed else 'FAIL'} ({elapsed:.2f}s)" +
              (f" — {failure_reason}" if failure_reason else ""))

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "test_id", "prompt", "actual_response", "result", "failure_reason",
            "execution_time_seconds", "category", "run_timestamp_utc"
        ])
        writer.writeheader()
        writer.writerows(results)

    total = len(results)
    passed_count = sum(r["result"] == "PASS" for r in results)
    failed_count = total - passed_count
    print(f"\nSummary: {passed_count}/{total} passed ({(passed_count / total * 100 if total else 0):.1f}%).")
    print(f"Results saved to: {RESULTS_PATH.resolve()}")


if __name__ == "__main__":
    main()
