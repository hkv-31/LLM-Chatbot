# Dataset-Based AI Output Testing

## Purpose
This test suite runs a fixed dataset of 15 prompts, applies deterministic checks, and writes `test_results.csv`. It checks non-empty output, keywords, basic output formats, concise-answer limits, and local handling of blank input.

## Files
- `test_dataset.csv`: 15 test cases and evaluation metadata.
- `run_tests.py`: executes prompts, checks responses, times each case, and writes results.
- `test_results.csv`: generated each time the runner executes; it is not a pre-filled report.
- `README.md`: setup, execution, and limitations.

## What the checks mean
- `non_empty`: output contains text.
- `keywords`: at least one listed keyword appears (a deliberately simple heuristic, not semantic evaluation).
- `format`: checks for a bullet list, exactly three numbered list markers, valid JSON with specified values, or exact output `4`.
- `max_words`: output must not exceed the row's word limit.
- `invalid_input`: blank prompt is rejected locally without calling the model.

## How to review failures
1. Open `test_results.csv` in Excel or VS Code.
2. Check `failure_reason` and compare `actual_response` with the prompt.
3. Classify failures as API/configuration errors, model-output issues, or overly strict evaluation rules.
4. If a check is too brittle, revise `expected_keywords` or its evaluator in `run_tests.py`, then rerun.
5. Run the suite more than once before concluding that a prompt is consistently failing; LLM outputs vary.

## Limitations
- Keyword checks can miss semantically correct paraphrases and can pass an irrelevant answer that happens to include a keyword.
- Format checks are intentionally basic and are not a substitute for schema validation or human review.
- The RAG prompts test general knowledge about RAG; this chatbot's current README lists document question answering/RAG as a future improvement, not an implemented feature.
- Direct mode tests the configured Groq model, not the app's HTTP server, UI, or conversation history. HTTP mode is preferable once the app exposes a JSON API endpoint.
- The suite is a smoke/regression test, not a benchmark of factual correctness or safety.

## Acceptance criteria
- [x] 15 test cases in CSV.
- [x] Automated execution and timing.
- [x] PASS/FAIL and failure reason recorded.
- [x] Results exported to CSV.
