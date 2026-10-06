import csv
import os
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

#Loading environment variables
load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY is missing. Add it to your .env file."
    )


#Loading model configuration
MODEL = "openai/gpt-oss-20b"
RESULTS_FILE = Path("prompt_cache_results.csv")
SYSTEM_PROMPT_FILE = Path("system_prompt.txt")

#Groq pricing configuration
NORMAL_INPUT_COST_PER_MILLION = 0.075
CACHED_INPUT_COST_PER_MILLION = 0.037
OUTPUT_COST_PER_MILLION = 0.30


#Loading system prompt
if not SYSTEM_PROMPT_FILE.exists():
    raise FileNotFoundError(
        "system_prompt.txt was not found. "
        "Place it in the same folder as prompt_caching.py."
    )

STATIC_SYSTEM_PROMPT = SYSTEM_PROMPT_FILE.read_text(
    encoding="utf-8"
).strip()


#Test queries
QUERIES = [
    "Explain how retrieval-augmented generation works.",
    "Explain how retrieval-augmented generation works.",
    "Explain how retrieval-augmented generation works.",
    "Explain how retrieval-augmented generation works.",
    "Explain how retrieval-augmented generation works.",
]


#Extracting token usage
def extract_usage(response):
    usage = response.usage

    input_tokens = getattr(
        usage,
        "prompt_tokens",
        0,
    ) or 0

    output_tokens = getattr(
        usage,
        "completion_tokens",
        0,
    ) or 0

    total_tokens = getattr(
        usage,
        "total_tokens",
        0,
    ) or 0

    details = getattr(
        usage,
        "prompt_tokens_details",
        None,
    )

    cached_tokens = 0

    if details:
        cached_tokens = (
            getattr(
                details,
                "cached_tokens",
                0,
            )
            or 0
        )

    return {
        "input_tokens": int(input_tokens),
        "output_tokens": int(output_tokens),
        "total_tokens": int(total_tokens),
        "cached_tokens": int(cached_tokens),
    }


#Calculating request cost
def calculate_cost(
    input_tokens,
    cached_tokens,
    output_tokens,
):
    uncached_input_tokens = max(
        input_tokens - cached_tokens,
        0,
    )

    normal_input_cost = (
        uncached_input_tokens
        / 1_000_000
        * NORMAL_INPUT_COST_PER_MILLION
    )

    cached_input_cost = (
        cached_tokens
        / 1_000_000
        * CACHED_INPUT_COST_PER_MILLION
    )

    output_cost = (
        output_tokens
        / 1_000_000
        * OUTPUT_COST_PER_MILLION
    )

    total_cost = (
        normal_input_cost
        + cached_input_cost
        + output_cost
    )

    normal_equivalent_cost = (
        input_tokens
        / 1_000_000
        * NORMAL_INPUT_COST_PER_MILLION
    )

    normal_equivalent_cost += output_cost

    cost_savings_percent = (
        (
            normal_equivalent_cost
            - total_cost
        )
        / normal_equivalent_cost
        * 100
        if normal_equivalent_cost
        else 0
    )

    return {
        "normal_input_cost": normal_input_cost,
        "cached_input_cost": cached_input_cost,
        "output_cost": output_cost,
        "total_cost": total_cost,
        "cost_savings_percent": cost_savings_percent,
    }


#Sending request to Groq
def run_request(
    system_prompt,
    query,
):
    client = Groq(
        api_key=API_KEY
    )

    start = time.perf_counter()

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": query,
            },
        ],
        temperature=0,
        max_tokens=300,
    )

    elapsed = time.perf_counter() - start

    usage = extract_usage(response)

    answer = (
        response.choices[0].message.content
        or ""
    )

    return (
        usage,
        answer,
        elapsed,
    )


#Saving experiment results
def save_results(rows):

    fieldnames = [
        "Run",
        "Mode",
        "Query",
        "Input Tokens",
        "Cached Tokens",
        "Uncached Input Tokens",
        "Output Tokens",
        "Total Tokens",
        "Cache Hit",
        "Cache Hit Rate %",
        "Normal Input Cost USD",
        "Cached Input Cost USD",
        "Output Cost USD",
        "Estimated Total Cost USD",
        "Estimated Cost Savings %",
        "Latency Seconds",
        "Response Length",
        "Response Consistent",
    ]

    with RESULTS_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)


#Running experiment
def main():

    rows = []

    print("=" * 65)
    print("GROQ PROMPT CACHING EXPERIMENT")
    print("=" * 65)
    print(f"Model: {MODEL}")
    print(
        f"System prompt: {SYSTEM_PROMPT_FILE}"
    )
    print()

    #Running baseline requests
    print(
        "Running baseline requests...\n"
    )

    baseline_answers = {}

    for index, query in enumerate(
        QUERIES,
        start=1,
    ):

        unique_marker = str(
            uuid.uuid4()
        )

        baseline_prompt = (
            f"Experiment marker: "
            f"{unique_marker}\n\n"
            + STATIC_SYSTEM_PROMPT
        )

        (
            usage,
            answer,
            latency,
        ) = run_request(
            baseline_prompt,
            query,
        )

        baseline_answers[query] = answer

        cost = calculate_cost(
            usage["input_tokens"],
            usage["cached_tokens"],
            usage["output_tokens"],
        )

        cache_hit_rate = (
            usage["cached_tokens"]
            / usage["input_tokens"]
            * 100
            if usage["input_tokens"]
            else 0
        )

        rows.append(
            {
                "Run": index,
                "Mode": "Baseline",
                "Query": query,
                "Input Tokens": usage["input_tokens"],
                "Cached Tokens": usage["cached_tokens"],
                "Uncached Input Tokens": (
                    usage["input_tokens"]
                    - usage["cached_tokens"]
                ),
                "Output Tokens": usage["output_tokens"],
                "Total Tokens": usage["total_tokens"],
                "Cache Hit": (
                    "Yes"
                    if usage["cached_tokens"] > 0
                    else "No"
                ),
                "Cache Hit Rate %": round(
                    cache_hit_rate,
                    2,
                ),
                "Normal Input Cost USD": round(
                    cost["normal_input_cost"],
                    8,
                ),
                "Cached Input Cost USD": round(
                    cost["cached_input_cost"],
                    8,
                ),
                "Output Cost USD": round(
                    cost["output_cost"],
                    8,
                ),
                "Estimated Total Cost USD": round(
                    cost["total_cost"],
                    8,
                ),
                "Estimated Cost Savings %": 0,
                "Latency Seconds": round(
                    latency,
                    3,
                ),
                "Response Length": len(answer),
                "Response Consistent": "",
            }
        )

        print(
            f"Baseline {index}: "
            f"input={usage['input_tokens']} | "
            f"cached={usage['cached_tokens']} | "
            f"output={usage['output_tokens']} | "
            f"total={usage['total_tokens']} | "
            f"latency={latency:.3f}s"
        )

        time.sleep(1)

    #Warming up prompt cache
    print(
        "\nWarming up prompt cache...\n"
    )

    run_request(
        STATIC_SYSTEM_PROMPT,
        QUERIES[0],
    )

    time.sleep(2)

    #Running repeated cached requests
    print(
        "Running cached requests...\n"
    )

    cached_answers = {}

    for index, query in enumerate(
        QUERIES,
        start=1,
    ):

        (
            usage,
            answer,
            latency,
        ) = run_request(
            STATIC_SYSTEM_PROMPT,
            query,
        )

        cached_answers[index] = answer

        cost = calculate_cost(
            usage["input_tokens"],
            usage["cached_tokens"],
            usage["output_tokens"],
        )

        cache_hit_rate = (
            usage["cached_tokens"]
            / usage["input_tokens"]
            * 100
            if usage["input_tokens"]
            else 0
        )

        consistent = (
            "Yes"
            if answer.strip()
            == baseline_answers[query].strip()
            else "No"
        )

        rows.append(
            {
                "Run": index,
                "Mode": "Prompt Cached",
                "Query": query,
                "Input Tokens": usage["input_tokens"],
                "Cached Tokens": usage["cached_tokens"],
                "Uncached Input Tokens": (
                    usage["input_tokens"]
                    - usage["cached_tokens"]
                ),
                "Output Tokens": usage["output_tokens"],
                "Total Tokens": usage["total_tokens"],
                "Cache Hit": (
                    "Yes"
                    if usage["cached_tokens"] > 0
                    else "No"
                ),
                "Cache Hit Rate %": round(
                    cache_hit_rate,
                    2,
                ),
                "Normal Input Cost USD": round(
                    cost["normal_input_cost"],
                    8,
                ),
                "Cached Input Cost USD": round(
                    cost["cached_input_cost"],
                    8,
                ),
                "Output Cost USD": round(
                    cost["output_cost"],
                    8,
                ),
                "Estimated Total Cost USD": round(
                    cost["total_cost"],
                    8,
                ),
                "Estimated Cost Savings %": round(
                    cost["cost_savings_percent"],
                    2,
                ),
                "Latency Seconds": round(
                    latency,
                    3,
                ),
                "Response Length": len(answer),
                "Response Consistent": consistent,
            }
        )

        print(
            f"Cached {index}: "
            f"input={usage['input_tokens']} | "
            f"cached={usage['cached_tokens']} | "
            f"output={usage['output_tokens']} | "
            f"total={usage['total_tokens']} | "
            f"latency={latency:.3f}s | "
            f"hit="
            f"{'Yes' if usage['cached_tokens'] > 0 else 'No'}"
        )

        time.sleep(1)

    #Saving results
    save_results(rows)

    #Separating baseline and cached results
    baseline_rows = [
        row
        for row in rows
        if row["Mode"] == "Baseline"
    ]

    cached_rows = [
        row
        for row in rows
        if row["Mode"] == "Prompt Cached"
    ]

    #Calculating token metrics
    baseline_input = sum(
        row["Input Tokens"]
        for row in baseline_rows
    )

    cached_input = sum(
        row["Input Tokens"]
        for row in cached_rows
    )

    total_cached_tokens = sum(
        row["Cached Tokens"]
        for row in cached_rows
    )

    cache_hits = sum(
        row["Cache Hit"] == "Yes"
        for row in cached_rows
    )

    #Calculating latency metrics
    baseline_latency = (
        sum(
            row["Latency Seconds"]
            for row in baseline_rows
        )
        / len(baseline_rows)
    )

    cached_latency = (
        sum(
            row["Latency Seconds"]
            for row in cached_rows
        )
        / len(cached_rows)
    )

    #Calculating input reduction
    input_reduction = (
        (
            baseline_input
            - cached_input
        )
        / baseline_input
        * 100
        if baseline_input
        else 0
    )

    #Calculating total cost
    baseline_cost = sum(
        float(
            row["Estimated Total Cost USD"]
        )
        for row in baseline_rows
    )

    cached_cost = sum(
        float(
            row["Estimated Total Cost USD"]
        )
        for row in cached_rows
    )

    cost_savings = (
        (
            baseline_cost
            - cached_cost
        )
        / baseline_cost
        * 100
        if baseline_cost
        else 0
    )

    #Printing experiment results
    print()
    print("=" * 65)
    print("RESULTS")
    print("=" * 65)

    print(
        f"Baseline input tokens:     "
        f"{baseline_input}"
    )

    print(
        f"Cached-test input tokens:  "
        f"{cached_input}"
    )

    print(
        f"Cached tokens observed:    "
        f"{total_cached_tokens}"
    )

    print(
        f"Cache hits:                "
        f"{cache_hits}/{len(cached_rows)}"
    )

    print(
        f"Input token reduction:     "
        f"{input_reduction:.2f}%"
    )

    print(
        f"Baseline estimated cost:   "
        f"${baseline_cost:.8f}"
    )

    print(
        f"Cached estimated cost:     "
        f"${cached_cost:.8f}"
    )

    print(
        f"Estimated cost savings:    "
        f"{cost_savings:.2f}%"
    )

    print(
        f"Average baseline latency:  "
        f"{baseline_latency:.3f}s"
    )

    print(
        f"Average cached latency:    "
        f"{cached_latency:.3f}s"
    )

    print(
        f"\nResults saved to: "
        f"{RESULTS_FILE}"
    )

    print("=" * 65)


#Running main function
if __name__ == "__main__":
    main()