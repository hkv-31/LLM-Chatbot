# Prompt Regression Testing

A small, repeatable regression-test harness for a chatbot. It runs a fixed CSV test set, stores a baseline, evaluates later outputs with the same lightweight rubric, and flags regressions.

## Can this be used with `hkv-31/LLM-Chatbot`?

Yes, as a separate test folder alongside the existing project. It does not need to rewrite your chatbot. This harness calls an OpenAI-compatible `/chat/completions` endpoint. If your repository uses a different API or model client, adapt `call_model()` in `run_regression_tests.py` to call that project's existing generation function. Do not assume the repository has an OpenAI-compatible endpoint until you inspect its README/code.

The provided test prompts are starter examples because the Task 1 dataset was not included here. Replace or merge them with 5–10 representative cases from Task 1 before treating results as project-specific evidence.

## Files

- `test_dataset.csv` — fixed test prompts, keyword expectations, formatting expectations and word limits.
- `baseline_results.csv` — baseline output log. Starts with headers; populate it with the baseline command.
- `run_regression_tests.py` — runs baseline and comparison.
- `regression_results.csv` — comparison log. Starts with headers; populated by `compare`.
- `README.md` — instructions and limitations.

## Requirements

Python 3.9+; the script uses only the Python standard library. No package installation is required.

## Step 1 — Put the folder beside your chatbot

Clone the project (if not already cloned):

```powershell
git clone https://github.com/hkv-31/LLM-Chatbot.git
cd LLM-Chatbot
```

Extract/copy this `prompt-regression-testing` folder inside the repository root. Expected layout:

```text
LLM-Chatbot/
├── ... existing chatbot files ...
└── prompt-regression-testing/
    ├── test_dataset.csv
    ├── baseline_results.csv
    ├── run_regression_tests.py
    ├── regression_results.csv
    └── README.md
```

If you want to keep the task separate from the chatbot repository, you can run it from any directory instead.

## Step 2 — Review the dataset

Open `test_dataset.csv`. Replace its starter prompts with 5–10 important prompts from Task 1 or from actual chatbot use. Keep `test_id` stable across runs. `expected_keywords` is a semicolon-separated list; in this simple evaluator, every listed keyword is counted as a required term. This is a heuristic, not a semantic-quality judge.

## Step 3 — Configure the model endpoint

Ensure the project-root `.env` contains your working `GROQ_API_KEY` and optional `GROQ_MODEL`. The runner loads these through the existing `app.py` and `python-dotenv`; no OpenAI-compatible endpoint variables are needed.

```env
GROQ_API_KEY=your_real_groq_key
GROQ_MODEL=openai/gpt-oss-20b
```

For a compatible local service, set `OPENAI_BASE_URL` to its base URL (for example a local server's `/v1` base). Do not commit API keys or place them in source files.

If your chatbot has no compatible endpoint, modify `call_model()` to invoke its existing model/generation code. See Step 7.

## Step 4 — Create a baseline with the original prompt

From inside `prompt-regression-testing`:

```powershell
python .\run_regression_tests.py baseline --prompt-version v1
```

This writes real model outputs to `baseline_results.csv`. The baseline command overwrites the previous baseline, so keep a copy or commit the baseline before regenerating it.

For a no-key pipeline check only:

```powershell
python .\run_regression_tests.py baseline --demo --prompt-version demo-v1
```

`--demo` uses fixed sample responses, not a real LLM. Use it only to verify that the script and CSV logging work.

## Step 5 — Make one deliberate prompt change

The default prompts are defined near the top of `run_regression_tests.py` as `BASELINE_PROMPT` and `CURRENT_PROMPT`. To preserve your original baseline, do not rerun the baseline after changing the prompt. The baseline command uses `BASELINE_PROMPT` by default; comparison uses `CURRENT_PROMPT` by default.

For a custom original prompt:

```powershell
python .\run_regression_tests.py baseline --prompt-version v1 --system-prompt "YOUR ORIGINAL SYSTEM PROMPT"
```

For a custom changed prompt:

```powershell
python .\run_regression_tests.py compare --prompt-version v2 --system-prompt "YOUR CHANGED SYSTEM PROMPT"
```

For multi-line prompts or prompts with quotes, editing the constants in the script is easier than passing the prompt through PowerShell.

## Step 6 — Compare and inspect the log

```powershell
python .\run_regression_tests.py compare --prompt-version v2
```

Inspect `regression_results.csv`. It includes baseline/current output, score, pass/fail, word counts, score delta, regression status and failure reason. The script exits with code `2` if it detects regressions or API errors; `0` means no detected regressions.

Rules used:
- Previously passing case now fails → `REGRESSION`.
- Score drop greater than `0.05` → `REGRESSION`.
- API/runtime failure → `ERROR`.
- Case still fails but already failed in baseline → `BASELINE_FAILURE`.
- Otherwise → `PASS`.

The 0.05 threshold is a demonstration setting, not a universal standard. Adjust it based on your application. A prompt may produce different wording even when quality is unchanged, so this harness does not compare exact text.

## Step 7 — Connect it to `LLM-Chatbot` if needed

First inspect the repository README and locate the function that sends messages to the model. If the project exposes a compatible endpoint, use Step 3. Otherwise, replace the body of `call_model(user_input, system_prompt, demo=False)` with a call to the project's existing generation function. Pass both the system prompt and user input, and return the generated text as a string. Keep the test runner isolated from UI code.

Do not claim integration is complete until you have run the tests against the actual chatbot model path and confirmed that the saved `model` and prompt version correspond to that run.

## Interpretation and limitations

- This is a lightweight demo evaluator based on keyword coverage, formatting and maximum word count; it cannot reliably judge factual correctness, helpfulness or semantic equivalence.
- For better evaluation, add human-reviewed expected answers or a separate LLM-as-judge with its own validation.
- Keep model, sampling settings, endpoint and test dataset constant between baseline and comparison where possible. Hosted models may change behind a stable model name.
- The CSV stores full model outputs. Avoid putting secrets, personal data or confidential prompts in the dataset.
