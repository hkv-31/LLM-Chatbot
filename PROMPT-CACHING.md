# Prompt Caching

## Objective

Measure the effect of Groq prompt caching on repeated LLM requests using the same LLM setup as the token optimization task.

## Setup

- **Provider:** Groq
- **Model:** `openai/gpt-oss-20b`
- **API:** Groq Chat Completions API
- **Temperature:** 0
- **Output limit:** 300 tokens

Groq prompt caching is automatic for supported models. No cache-enable parameter is required. When requests share an identical prompt prefix, Groq can reuse the cached computation.

## Experiment

### Baseline

Each request uses a unique system-prompt marker at the beginning, preventing the requests from sharing an identical prefix.

### Cached

The same static system prompt and repeated user query are used to test cache reuse.

The experiment records:

- Input tokens
- Cached tokens
- Uncached input tokens
- Output tokens
- Total tokens
- Cache hits
- Cache hit rate
- Estimated cost
- Cost savings
- Request latency
- Response consistency

## Results

The experiment successfully observed a cache hit:

    Cached 5: input=1392 | cached=768 | output=300 | total=1692 | latency=12.066s | hit=Yes

### Summary

| Metric | Result |
|---|---:|
| Baseline requests | 5 |
| Cached requests | 5 |
| Cache hits | 1/5 |
| Cached tokens observed | 768 |
| Cache hit rate | 20% |
| Estimated cost savings | 3.97% |
| Average baseline latency | 1.091s |

Cache hits are provider-managed and are not guaranteed for every request. The observed `768` cached tokens confirm that Groq successfully reused part of the repeated prompt prefix.

### Why Were Only 1/5 Requests Cache Hits?

A cache hit was observed on only 1 of the 5 cached requests because Groq prompt caching is **provider-managed**. A matching prompt prefix does not guarantee that every request will use the cache.

The experiment confirmed that caching was working because the fifth request reported:

```text
Cached 5: input=1392 | cached=768 | output=300 | total=1692 | latency=12.066s | hit=Yes
```

The `768` cached tokens show that Groq reused part of the repeated prompt prefix. The other requests returned `cached=0`, meaning no cached tokens were reported for those requests.

## Environment Setup

Create a `.env` file:

    GROQ_API_KEY=your_groq_api_key

Install dependencies:

    pip install -r requirements.txt

Run the experiment:

    python prompt_caching.py

Results are automatically saved to:

    prompt_cache_results.csv