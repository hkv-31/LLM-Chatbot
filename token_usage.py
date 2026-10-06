import pandas as pd
from pathlib import Path

# ------------------------------------------------------------
# Token Usage Analysis
# Reads:
#   token_usage_comparison.csv
#
# Produces:
#   token_usage_final_comparison.csv
#   token_usage_optimization_summary.csv
#   token_usage_quality_template.csv
# ------------------------------------------------------------

INPUT_FILE = Path("token_usage_comparison.csv")
FINAL_FILE = Path("token_usage_final_comparison.csv")
SUMMARY_FILE = Path("token_usage_optimization_summary.csv")
QUALITY_FILE = Path("token_usage_quality_template.csv")

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"Could not find {INPUT_FILE}. "
        "Put this script in the same folder as token_usage_comparison.csv."
    )

df = pd.read_csv(INPUT_FILE)

required_columns = {
    "Query",
    "Version",
    "Input Tokens",
    "Output Tokens",
    "Total Tokens",
}

missing = required_columns - set(df.columns)
if missing:
    raise ValueError(f"Missing required columns: {sorted(missing)}")

# Clean column values
df["Query"] = df["Query"].astype(str).str.strip()
df["Version"] = df["Version"].astype(str).str.strip()

token_columns = ["Input Tokens", "Output Tokens", "Total Tokens"]
for col in token_columns:
    df[col] = pd.to_numeric(df[col], errors="coerce")

if df[token_columns].isna().any().any():
    bad_rows = df[df[token_columns].isna().any(axis=1)]
    raise ValueError(
        "Some token values are missing or non-numeric.\n"
        f"{bad_rows.to_string(index=False)}"
    )

# If the same Query + Version appears more than once, keep the latest
# occurrence in the CSV. This protects the analysis from accidental
# duplicate/retry entries.
df = df.drop_duplicates(subset=["Query", "Version"], keep="last")

baseline = (
    df[df["Version"].eq("Baseline")]
    [["Query", "Input Tokens", "Output Tokens", "Total Tokens"]]
    .rename(columns={
        "Input Tokens": "Before Input",
        "Output Tokens": "Before Output",
        "Total Tokens": "Before Total",
    })
)

optimized = (
    df[df["Version"].eq("Output Optimized")]
    [["Query", "Input Tokens", "Output Tokens", "Total Tokens"]]
    .rename(columns={
        "Input Tokens": "After Input",
        "Output Tokens": "After Output",
        "Total Tokens": "After Total",
    })
)

final = baseline.merge(optimized, on="Query", how="inner")

if final.empty:
    raise ValueError(
        "No matching Baseline and Output Optimized queries were found."
    )

# Required assignment formula
final["Savings %"] = (
    (final["Before Total"] - final["After Total"])
    / final["Before Total"]
    * 100
).round(2)

# Put columns in exactly the order required by the assignment
final = final[
    [
        "Query",
        "Before Input",
        "Before Output",
        "Before Total",
        "After Input",
        "After Output",
        "After Total",
        "Savings %",
    ]
]

final.to_csv(FINAL_FILE, index=False)

before_total = final["Before Total"].sum()
after_total = final["After Total"].sum()
tokens_saved = before_total - after_total
overall_savings = (
    tokens_saved / before_total * 100
    if before_total
    else 0
)

print("\n" + "=" * 60)
print("TOKEN USAGE OPTIMIZATION RESULTS")
print("=" * 60)

print(f"Queries compared:       {len(final)}")
print(f"Baseline total tokens:  {before_total}")
print(f"Optimized total tokens: {after_total}")
print(f"Tokens saved:           {tokens_saved}")
print(f"Overall savings:        {overall_savings:.2f}%")

print("\nPer-query results:")
print(final.to_string(index=False))

versions = [
    "Baseline",
    "System Prompt Optimized",
    "History Optimized",
    "Output Optimized",
]

summary_rows = []

for version in versions:
    subset = df[df["Version"].eq(version)]

    if subset.empty:
        continue

    total_input = subset["Input Tokens"].sum()
    total_output = subset["Output Tokens"].sum()
    total_tokens = subset["Total Tokens"].sum()

    summary_rows.append({
        "Version": version,
        "Queries": len(subset),
        "Total Input Tokens": int(total_input),
        "Total Output Tokens": int(total_output),
        "Total Tokens": int(total_tokens),
    })

summary = pd.DataFrame(summary_rows)

if not summary.empty:
    baseline_stage_total = summary.loc[
        summary["Version"].eq("Baseline"), "Total Tokens"
    ]

    if not baseline_stage_total.empty:
        baseline_stage_total = baseline_stage_total.iloc[0]
        summary["Savings vs Baseline %"] = (
            (baseline_stage_total - summary["Total Tokens"])
            / baseline_stage_total
            * 100
        ).round(2)

    summary.to_csv(SUMMARY_FILE, index=False)

quality = final[["Query"]].copy()
quality["Quality"] = ""
quality["Notes"] = ""
quality.to_csv(QUALITY_FILE, index=False)

print("\nFiles generated:")
print(f"1. {FINAL_FILE}")
print(f"2. {SUMMARY_FILE}")
print(f"3. {QUALITY_FILE}")

print("\nQuality options:")
print("Good       = correct, relevant, and sufficiently complete")
print("Acceptable = mostly correct but somewhat incomplete")
print("Poor       = incorrect, misses important information, or loses context")
print("=" * 60)
