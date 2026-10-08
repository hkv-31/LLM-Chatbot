# Redis Cache Layer- LLM Chatbot

## Architecture

```text
Browser -> POST /api/chat -> Cache Key -> Redis GET
                                      /       \\
                                    HIT       MISS
                                     |          |
                                  return     Groq API
                                                |
                                             Redis SET
                                                |
                                      -> return response
```

## Why the cache key includes conversation history

The chatbot is multi-turn. The same current question can produce a different answer depending on earlier messages. The cache key therefore uses the complete normalized model request plus the selected model.

## Redis setup on Windows

Use Docker:

```powershell
docker run -d --name redis -p 6379:6379 redis:latest
docker exec -it redis redis-cli ping
```

Expected: `PONG`.

## Python setup

```powershell
python -m venv .venv
.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
```

Add to the existing `.env`:

```text
REDIS_URL=redis://127.0.0.1:6379/0
CACHE_TTL=60
```

## Applying the integration

From the existing repository root:

```powershell
git apply cache_integration.patch
```

If your local `app.py` differs from the inspected GitHub version, use the patch as the manual change guide.

## Results

`cache_results.csv` records timestamp, query, cache status, response time, remaining TTL, cache key, and model.
