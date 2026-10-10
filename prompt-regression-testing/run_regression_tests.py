"""Prompt regression tests for the sibling LLM-Chatbot app.py (Groq Responses API)."""
import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))

DATASET = ROOT / "test_dataset.csv"
BASELINE = ROOT / "baseline_results.csv"
RESULTS = ROOT / "regression_results.csv"

BASELINE_FIELDS = ["run_timestamp_ist","test_id","model","prompt_version","system_prompt","user_input","output","score","passed","word_count","error"]
RESULT_FIELDS = ["run_timestamp_ist","test_id","model","baseline_prompt_version","current_prompt_version","baseline_output","current_output","baseline_score","current_score","baseline_passed","current_passed","score_delta","baseline_word_count","current_word_count","regression_status","failure_reason","error"]

BASELINE_PROMPT = (
    "You are a helpful, concise, and friendly AI assistant. "
    "Provide accurate and easy-to-understand answers."
)

CURRENT_PROMPT = (
"You are a helpful AI assistant. Answer accurately and concisely. "
"Follow the requested output format exactly. "
"Respect the word limit and include the key concepts relevant to the question. "
"For comparison questions, use bullet points to compare the requested items and include examples when asked. Apply this comparison format only to comparison questions. "
"For coding questions, provide minimal working code. "
"For calculations, show the calculation and final answer. "
"For password security advice, provide concise bullet points covering unique passwords, a password manager, and multi-factor authentication. "
"Avoid unnecessary introductions and conclusions."
)


def now():
    return datetime.now(timezone.utc).astimezone(
    timezone(__import__("datetime").timedelta(hours=5, minutes=30))
    ).isoformat()

def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def write_csv(path, fields, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

def call_model(user_input, system_prompt, demo=False):
    if demo:
        # Offline fixture for verifying the harness only; not a real model evaluation.
        lower = user_input.lower()
        if "machine learning" in lower:
            return "Machine learning is a part of artificial intelligence where systems learn patterns from data to make predictions or decisions."
        if "difference between ai" in lower:
            return "- Artificial intelligence is the broader field of building systems that perform intelligent tasks.\n- Machine learning is a subset of artificial intelligence that learns patterns from data.\n- Example: a rule-based chess program uses AI; a spam classifier trained on emails uses machine learning."
        if "python function" in lower:
            return "```python\ndef square(number):\n    return number * number\n```"
        if "software testing" in lower:
            return "Software testing helps find bugs and improve reliability before software reaches users."
        if "three benefits" in lower:
            return "- Detects defects early\n- Supports safer changes\n- Improves collaboration"
        if "sequential requests" in lower:
            return "Five sequential requests take 5 × 2 = 10 seconds, ignoring overhead."
        if "password" in lower:
            return "- Use a long, unique password for every account.\n- Store passwords in a reputable password manager.\n- Enable multi-factor authentication."
        return "Python is a readable, general-purpose programming language used for automation, web development, data analysis, and machine learning."

    try:
        import app  # app.py is in the parent LLM-Chatbot folder
    except Exception as exc:
        raise RuntimeError(f"Could not import project app.py: {type(exc).__name__}: {exc}") from exc
    if app.groq_client is None:
        raise RuntimeError("GROQ_API_KEY is missing. Check the project-root .env file.")
    # Reuse the exact Groq Responses API implementation from the application.
    app.SYSTEM_INSTRUCTION = system_prompt
    return app.chat_with_model(user_input, history=[])


def evaluate(output, row):
    import re

    lower = (output or "").lower()
    test_id = row["test_id"]

    keywords = [
        k.strip().lower()
        for k in row.get("expected_keywords", "").split(";")
        if k.strip()
    ]

    hits = sum(1 for k in keywords if k in lower)
    keyword_score = hits / len(keywords) if keywords else 1.0

    # TC06
    if test_id == "TC06":
        normalized = lower.replace(",", "")
        correct_result = bool(
            re.search(r"\b10\s+seconds?\b", normalized)
        )
        keyword_score = 1.0 if correct_result else 0.0

    max_words = int(row.get("max_words") or 0)
    word_count = len((output or "").split())

    fmt = row.get("format_expectation", "").lower()
    format_ok = True

    
    if fmt == "bullets":
        format_ok = any(
            re.match(r"^\s*(?:[-*•]|\d+[.)])\s+", line)
            for line in (output or "").splitlines()
        )
    elif fmt == "code":
        format_ok = "def " in (output or "") and "return" in (output or "")

    length_ok = not max_words or word_count <= max_words

    score = round(
        0.7 * keyword_score
        + 0.2 * float(format_ok)
        + 0.1 * float(length_ok),
        3,
    )

    passed = score >= 0.65 and format_ok and length_ok

    reasons = []
    if keyword_score < 0.5:
        reasons.append(f"keyword/result coverage {hits}/{len(keywords)}"
                       if test_id != "TC06"
                       else "correct result '10 seconds' not found")
    if not format_ok:
        reasons.append("format requirement not met")
    if not length_ok:
        reasons.append(f"output exceeds {max_words} words")

    return score, passed, word_count, "; ".join(reasons)

def get_model_name(demo):
    if demo:
        return "demo-fixture"
    import app
    return app.MODEL

def run_baseline(args):
    tests = read_csv(DATASET)
    model = get_model_name(args.demo)
    results = []
    for row in tests:
        output, error = "", ""
        try:
            output = call_model(row["user_input"], args.system_prompt, args.demo)
        except Exception as exc:
            error = str(exc)
        score, passed, words, _ = evaluate(output, row) if not error else (0.0, False, 0, error)
        results.append({"run_timestamp_ist":now(),"test_id":row["test_id"],"model":model,
            "prompt_version":args.prompt_version,"system_prompt":args.system_prompt,
            "user_input":row["user_input"],"output":output,"score":score,
            "passed":str(passed).lower(),"word_count":words,"error":error})
        print(f'{row["test_id"]}: {"PASS" if passed else "FAIL"} score={score:.3f}' + (f" | {error}" if error else ""))
    write_csv(BASELINE, BASELINE_FIELDS, results)
    count = sum(r["passed"] == "true" for r in results)
    print(f"\nBaseline saved: {count}/{len(results)} passed -> {BASELINE.name}")
    if any(r["error"] for r in results):
        sys.exit(1)

def run_compare(args):
    baseline = read_csv(BASELINE)
    if not baseline:
        raise SystemExit("Baseline is empty. Run the baseline command first.")
    base_by_id = {r["test_id"]:r for r in baseline}
    tests = read_csv(DATASET)
    model = get_model_name(args.demo)
    results = []
    for row in tests:
        old = base_by_id.get(row["test_id"])
        if old is None:
            print(f'{row["test_id"]}: ERROR no matching baseline')
            continue
        output, error = "", ""
        try:
            output = call_model(row["user_input"], args.system_prompt, args.demo)
        except Exception as exc:
            error = str(exc)
        score, passed, words, reason = evaluate(output, row) if not error else (0.0, False, 0, error)
        old_passed = old["passed"].lower() == "true"
        old_score = float(old["score"])
        if error:
            status, reason = "ERROR", error
        elif old_passed and not passed:
            status, reason = "REGRESSION", reason or "Previously passing test now fails"
        elif old_score - score > args.max_score_drop:
            status, reason = "REGRESSION", reason or f"Score dropped by more than {args.max_score_drop:.2f}"
        elif not old_passed:
            status, reason = "BASELINE_FAILURE", reason or "Test already failed in baseline"
        else:
            status, reason = "PASS", "No regression detected"
        results.append({"run_timestamp_ist":now(),"test_id":row["test_id"],"model":model,
            "baseline_prompt_version":old["prompt_version"],"current_prompt_version":args.prompt_version,
            "baseline_output":old["output"],"current_output":output,"baseline_score":old_score,
            "current_score":score,"baseline_passed":str(old_passed).lower(),
            "current_passed":str(passed).lower(),"score_delta":round(score-old_score,3),
            "baseline_word_count":old["word_count"],"current_word_count":words,
            "regression_status":status,"failure_reason":reason,"error":error})
        print(f'{row["test_id"]}: {status} score {old_score:.3f} -> {score:.3f}' + (f" | {reason}" if status in ("REGRESSION","ERROR") else ""))
    write_csv(RESULTS, RESULT_FIELDS, results)
    regressions = sum(r["regression_status"] == "REGRESSION" for r in results)
    errors = sum(r["regression_status"] == "ERROR" for r in results)
    passed_count = sum(r["current_passed"] == "true" for r in results)
    print(f"\nSaved {RESULTS.name}; current pass rate {passed_count}/{len(results)}; regressions={regressions}; errors={errors}.")
    if regressions or errors:
        sys.exit(2)

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("baseline")
    b.add_argument("--demo", action="store_true")
    b.add_argument("--prompt-version", default="v1")
    b.add_argument("--system-prompt", default=BASELINE_PROMPT)
    c = sub.add_parser("compare")
    c.add_argument("--demo", action="store_true")
    c.add_argument("--prompt-version", default="v2")
    c.add_argument("--system-prompt", default=CURRENT_PROMPT)
    c.add_argument("--max-score-drop", type=float, default=0.05)
    args = parser.parse_args()
    run_baseline(args) if args.command == "baseline" else run_compare(args)

if __name__ == "__main__":
    main()
