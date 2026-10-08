"""Single-file web chatbot powered by Groq's Responses API."""

import csv
import json
import os
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import groq
from dotenv import load_dotenv
from groq import Groq
from cache.redis_cache import RedisCache


load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY", "").strip()
DEFAULT_MODEL = "openai/gpt-oss-20b"
configured_model = os.getenv("GROQ_MODEL", "").strip()
MODEL = configured_model if configured_model not in {"", "your_model_name_here"} else DEFAULT_MODEL
SYSTEM_INSTRUCTION = (
    "You are a helpful, concise, and friendly AI assistant. "
    "Provide accurate and easy-to-understand answers."
)

groq_client = Groq(api_key=API_KEY) if API_KEY else None
response_cache = RedisCache()
RESULTS_FILE = "cache_results.csv"


HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LLM Chatbot</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #172033;
      --muted: #667085;
      --line: #e4e7ec;
      --soft: #f8fafc;
      --brand: #2563eb;
      --brand-dark: #1d4ed8;
      --user: #eaf2ff;
      --assistant: #ffffff;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      background: linear-gradient(135deg, #f8fbff 0%, #eef4ff 100%);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    .page {
      width: min(920px, calc(100% - 32px));
      margin: 0 auto;
      padding: 42px 0 32px;
    }

    .header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 20px;
      margin-bottom: 22px;
    }

    .eyebrow {
      margin: 0 0 8px;
      color: var(--brand);
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }

    h1 {
      margin: 0;
      font-size: clamp(1.8rem, 4vw, 2.55rem);
      letter-spacing: -0.04em;
    }

    .subtitle {
      margin: 10px 0 0;
      color: var(--muted);
      font-size: 0.98rem;
    }

    .status {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.8);
      color: var(--muted);
      font-size: 0.82rem;
      padding: 8px 12px;
      white-space: nowrap;
    }

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #22c55e;
    }

    .card {
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.9);
      box-shadow: 0 18px 45px rgba(31, 50, 81, 0.08);
    }

    .chat-window {
      min-height: 470px;
      max-height: 58vh;
      overflow-y: auto;
      padding: 24px;
    }

    .welcome {
      max-width: 620px;
      margin: 42px auto;
      text-align: center;
    }

    .welcome-icon {
      display: grid;
      place-items: center;
      width: 52px;
      height: 52px;
      margin: 0 auto 14px;
      border-radius: 16px;
      background: #eaf2ff;
      color: var(--brand);
      font-size: 1.5rem;
    }

    .welcome h2 { margin: 0; font-size: 1.25rem; }
    .welcome p { color: var(--muted); line-height: 1.6; }

    .message {
      display: flex;
      margin: 14px 0;
    }

    .message.user { justify-content: flex-end; }

    .bubble {
      max-width: min(78%, 680px);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 12px 15px;
      line-height: 1.55;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }

    .message.user .bubble {
      border-color: #c8dcff;
      border-bottom-right-radius: 5px;
      background: var(--user);
    }

    .message.assistant .bubble {
      border-bottom-left-radius: 5px;
      background: var(--assistant);
    }

    .bubble.markdown p { margin: 0 0 10px; }
    .bubble.markdown p:last-child { margin-bottom: 0; }
    .bubble.markdown ul, .bubble.markdown ol {
      margin: 8px 0 10px;
      padding-left: 24px;
    }
    .bubble.markdown li { margin: 5px 0; padding-left: 3px; }
    .bubble.markdown strong { font-weight: 750; color: #111827; }
    .bubble.markdown code {
      border-radius: 5px;
      background: #eef2f7;
      color: #1e3a8a;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.9em;
      padding: 2px 5px;
    }
    .bubble.markdown pre {
      overflow-x: auto;
      border-radius: 9px;
      background: #172033;
      color: #f8fafc;
      padding: 12px;
    }
    .bubble.markdown pre code { background: transparent; color: inherit; padding: 0; }

    .composer {
      display: flex;
      align-items: flex-end;
      gap: 10px;
      border-top: 1px solid var(--line);
      background: var(--soft);
      padding: 16px;
    }

    textarea {
      width: 100%;
      min-height: 48px;
      max-height: 140px;
      resize: vertical;
      border: 1px solid #d0d5dd;
      border-radius: 12px;
      background: white;
      color: var(--ink);
      font: inherit;
      line-height: 1.45;
      outline: none;
      padding: 13px 14px;
    }

    textarea:focus { border-color: var(--brand); box-shadow: 0 0 0 3px #dbeafe; }

    button {
      border: 0;
      border-radius: 11px;
      cursor: pointer;
      font: inherit;
      font-weight: 700;
      transition: transform 0.15s ease, background 0.15s ease;
    }

    button:hover { transform: translateY(-1px); }
    button:disabled { cursor: not-allowed; opacity: 0.55; transform: none; }

    .send {
      min-width: 84px;
      min-height: 48px;
      background: var(--brand);
      color: white;
    }

    .send:hover { background: var(--brand-dark); }

    .toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-top: 14px;
    }

    .examples { display: flex; flex-wrap: wrap; gap: 8px; }

    .example, .clear {
      border: 1px solid var(--line);
      background: white;
      color: var(--muted);
      font-size: 0.82rem;
      padding: 8px 11px;
    }

    .example:hover, .clear:hover { border-color: #b8c5d9; color: var(--ink); }

    .hint {
      margin: 14px 2px 0;
      color: var(--muted);
      font-size: 0.78rem;
    }

    @media (max-width: 640px) {
      .page { width: min(100% - 20px, 920px); padding-top: 24px; }
      .header { display: block; }
      .status { margin-top: 16px; }
      .chat-window { min-height: 52vh; padding: 16px; }
      .bubble { max-width: 88%; }
      .composer { align-items: stretch; flex-direction: column; }
      .send { width: 100%; }
      .toolbar { align-items: flex-start; flex-direction: column; }
    }
  </style>
</head>
<body>
  <main class="page">
    <header class="header">
      <div>
        <p class="eyebrow">API-based conversational AI</p>
        <h1>LLM Chatbot</h1>
        <p class="subtitle">A simple, focused chat experience powered by Groq.</p>
      </div>
      <div class="status"><span class="status-dot"></span>Ready to chat</div>
    </header>

    <section class="card">
      <div id="chatWindow" class="chat-window" aria-live="polite">
        <div id="welcome" class="welcome">
          <div class="welcome-icon">✦</div>
          <h2>How can I help you today?</h2>
          <p>Ask a question, explore an idea, or use one of the examples below to get started.</p>
        </div>
      </div>
      <form id="chatForm" class="composer">
        <textarea id="messageInput" aria-label="Message" placeholder="Type your message..." rows="1" required></textarea>
        <button id="sendButton" class="send" type="submit">Send</button>
      </form>
    </section>

    <div class="toolbar">
      <div class="examples" aria-label="Example prompts">
        <button class="example" type="button">Explain machine learning simply.</button>
        <button class="example" type="button">What is the difference between lists and tuples?</button>
        <button class="example" type="button">Help me understand APIs.</button>
      </div>
      <button id="clearButton" class="clear" type="button">Clear chat</button>
    </div>
    <p class="hint">Your conversation is kept for this browser session and is not stored permanently.</p>
  </main>

  <script>
    const conversationHistory = [];
    const chatWindow = document.getElementById("chatWindow");
    const welcome = document.getElementById("welcome");
    const form = document.getElementById("chatForm");
    const input = document.getElementById("messageInput");
    const sendButton = document.getElementById("sendButton");

    function escapeHtml(value) {
      return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#039;");
    }

    function renderInlineMarkdown(value) {
      let text = escapeHtml(value);
      text = text.replace(/`([^`\n]+)`/g, "<code>$1</code>");
      text = text.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
      text = text.replace(/__(.+?)__/g, "<strong>$1</strong>");
      return text;
    }

    function renderMarkdown(value) {
      const lines = String(value).split(/\r?\n/);
      let html = "";
      let listType = null;
      let inCodeBlock = false;

      function closeList() {
        if (listType) {
          html += `</${listType}>`;
          listType = null;
        }
      }

      for (const line of lines) {
        if (line.trim().startsWith("```")) {
          closeList();
          if (inCodeBlock) {
            html += "</code></pre>";
          } else {
            html += "<pre><code>";
          }
          inCodeBlock = !inCodeBlock;
          continue;
        }

        if (inCodeBlock) {
          html += `${escapeHtml(line)}\n`;
          continue;
        }

        const unordered = line.match(/^\s*[-*]\s+(.+)$/);
        const ordered = line.match(/^\s*\d+[.)]\s+(.+)$/);
        if (unordered || ordered) {
          const nextType = unordered ? "ul" : "ol";
          if (listType !== nextType) {
            closeList();
            html += `<${nextType}>`;
            listType = nextType;
          }
          html += `<li>${renderInlineMarkdown((unordered || ordered)[1])}</li>`;
          continue;
        }

        closeList();
        if (!line.trim()) continue;

        const heading = line.match(/^\s*#{1,3}\s+(.+)$/);
        if (heading) {
          html += `<strong>${renderInlineMarkdown(heading[1])}</strong>`;
        } else {
          html += `<p>${renderInlineMarkdown(line)}</p>`;
        }
      }

      closeList();
      if (inCodeBlock) html += "</code></pre>";
      return html;
    }

    function addMessage(role, content) {
      welcome.hidden = true;
      const row = document.createElement("div");
      row.className = `message ${role}`;
      const bubble = document.createElement("div");
      bubble.className = "bubble";
      if (role === "assistant") {
        bubble.classList.add("markdown");
        bubble.innerHTML = renderMarkdown(content);
      } else {
        bubble.textContent = content;
      }
      row.appendChild(bubble);
      chatWindow.appendChild(row);
      chatWindow.scrollTop = chatWindow.scrollHeight;
      return bubble;
    }

    function setLoading(loading) {
      sendButton.disabled = loading;
      input.disabled = loading;
      sendButton.textContent = loading ? "Thinking..." : "Send";
    }

    async function sendMessage(message) {
      const cleanMessage = message.trim();
      if (!cleanMessage) return;

      addMessage("user", cleanMessage);
      const previousHistory = [...conversationHistory];
      conversationHistory.push({ role: "user", content: cleanMessage });
      input.value = "";
      setLoading(true);
      const assistantBubble = addMessage("assistant", "Thinking...");

      try {
        const response = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: cleanMessage, history: previousHistory })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Request failed");
        assistantBubble.innerHTML = renderMarkdown(data.response);
        const cacheInfo = document.createElement("div");
        cacheInfo.style.cssText =
          "margin-top:8px;font-size:.72rem;color:#667085;";
        cacheInfo.textContent =
          `Cache ${data.cache_status} · ` +
          `${Number(data.response_time).toFixed(3)}s · ` +
          `TTL ${data.ttl}s`;

        assistantBubble.appendChild(cacheInfo);

        conversationHistory.push({
          role: "assistant",
          content: data.response
        });
      } catch (error) {
        assistantBubble.textContent = error.message || "Sorry, something went wrong.";
        conversationHistory.pop();
      } finally {
        setLoading(false);
        input.focus();
        chatWindow.scrollTop = chatWindow.scrollHeight;
      }
    }

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      sendMessage(input.value);
    });

    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        form.requestSubmit();
      }
    });

    document.querySelectorAll(".example").forEach((button) => {
      button.addEventListener("click", () => {
        input.value = button.textContent;
        input.focus();
      });
    });

    document.getElementById("clearButton").addEventListener("click", () => {
      conversationHistory.length = 0;
      chatWindow.querySelectorAll(".message").forEach((message) => message.remove());
      welcome.hidden = false;
      input.value = "";
      input.focus();
    });
  </script>
</body>
</html>"""


def _message_text(content: Any) -> str:
    """Return text from a simple message value."""
    if isinstance(content, str):
        return content.strip()
    return ""


def convert_history(history: Any) -> list[dict[str, str]]:
    """Keep only safe user and assistant text for the Responses API."""
    messages: list[dict[str, str]] = []
    if not isinstance(history, list):
        return messages

    for item in history:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = _message_text(item.get("content"))
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    return messages


def _extract_output_text(response_data: Any) -> str:
    """Extract assistant text from a Responses API result."""
    if isinstance(response_data, dict):
        output_text = response_data.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()
        output_items = response_data.get("output", [])
    else:
        output_items = getattr(response_data, "output", [])

    for item in output_items or []:
        content_items = item.get("content", []) if isinstance(item, dict) else getattr(item, "content", [])
        for content in content_items or []:
            if isinstance(content, dict):
                content_type = content.get("type")
                text = content.get("text")
            else:
                content_type = getattr(content, "type", None)
                text = getattr(content, "text", None)
            if content_type == "output_text" and isinstance(text, str):
                return text.strip()

    return ""


def request_model(messages: list[dict[str, str]]) -> str:
    """Send conversation history to Groq's current Responses API."""
    if groq_client is None:
        raise RuntimeError("missing_api_key")

    response = groq_client.post(
        "/openai/v1/responses",
        # Return the decoded JSON as-is. The Responses API has fields that
        # are not represented by the current high-level Groq SDK models.
        cast_to=object,
        body={
            "model": MODEL,
            "instructions": SYSTEM_INSTRUCTION,
            "input": messages,
        },
    )
    response_text = _extract_output_text(response)
    if not response_text:
        raise ValueError("unexpected_response")
    return response_text


def _record_cache_result(
    query: str,
    cache_status: str,
    response_time: float,
    ttl: int,
    cache_key: str,
) -> None:
    """Append one cache experiment result to CSV."""
    exists = os.path.exists(RESULTS_FILE) and os.path.getsize(RESULTS_FILE) > 0

    with open(RESULTS_FILE, "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        if not exists:
            writer.writerow(
                [
                    "Timestamp",
                    "Query",
                    "Cache Status",
                    "Response Time (s)",
                    "TTL (s)",
                    "Cache Key",
                    "Model",
                ]
            )

        writer.writerow(
            [
                datetime.now(timezone.utc).isoformat(),
                query,
                cache_status,
                f"{response_time:.6f}",
                ttl,
                cache_key,
                MODEL,
            ]
        )


def chat_with_model(message: Any, history: Any) -> tuple[str, str, float, int, str]:
    """Validate input, check Redis, and call Groq only on a cache miss."""
    clean_message = _message_text(message)

    if not clean_message:
        raise ValueError("empty_message")

    messages = convert_history(history)
    messages.append({"role": "user", "content": clean_message})

    # Create a deterministic key from the complete conversation + model.
    cache_key = response_cache.make_key(messages, MODEL)
    print("\n----- CACHE DEBUG -----")
    print("Key:", cache_key)
    print("Redis URL:", response_cache.url)
    print("Exists before GET:", response_cache.exists(cache_key))

    start = time.perf_counter()

    # Check Redis first.
    cached_response = response_cache.get(cache_key)
    print("Cached response found:", cached_response is not None)

    if cached_response is not None:
        elapsed = time.perf_counter() - start
        ttl = response_cache.ttl(cache_key)

        _record_cache_result(
            clean_message,
            "HIT",
            elapsed,
            ttl,
            cache_key,
        )

        return cached_response, "HIT", elapsed, ttl, cache_key

    # Cache MISS → call the existing Groq implementation.
    response = request_model(messages)

    # Store the generated response in Redis.
    response_cache.set(cache_key, response)
    print("SET executed")
    print("Exists after SET:", response_cache.exists(cache_key))
    print("TTL:", response_cache.ttl(cache_key))
    print("-----------------------")

    elapsed = time.perf_counter() - start
    ttl = response_cache.ttl(cache_key)

    _record_cache_result(
        clean_message,
        "MISS",
        elapsed,
        ttl,
        cache_key,
    )

    return response, "MISS", elapsed, ttl, cache_key


def send_json(handler: BaseHTTPRequestHandler, payload: dict[str, str], status: int = 200) -> None:
    """Send a JSON response from the local web server."""
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


class ChatbotHandler(BaseHTTPRequestHandler):
    """Serve the UI and the chat API."""

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path in {"/", "/index.html"}:
            body = HTML_PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        send_json(self, {"error": "Not found."}, status=404)

    def do_POST(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
      if self.path != "/api/chat":
          send_json(self, {"error": "Not found."}, status=404)
          return

      try:
          content_length = int(self.headers.get("Content-Length", "0"))

          if content_length > 1_000_000:
              raise ValueError("request_too_large")

          payload = json.loads(self.rfile.read(content_length))

          if not isinstance(payload, dict):
              raise ValueError("invalid_payload")

          response, cache_status, response_time, ttl, cache_key = chat_with_model(
              payload.get("message"),
              payload.get("history"),
          )

          send_json(
              self,
              {
                  "response": response,
                  "cache_status": cache_status,
                  "response_time": response_time,
                  "ttl": ttl,
                  "cache_key": cache_key,
              },
          )

      except ValueError as error:
          if str(error) == "empty_message":
              send_json(
                  self,
                  {"error": "Please enter a message before sending."},
                  status=400,
              )

          elif str(error) == "request_too_large":
              send_json(
                  self,
                  {"error": "The request is too large."},
                  status=413,
              )

          elif str(error) == "unexpected_response":
              print("Groq returned an unexpected response format.")
              send_json(
                  self,
                  {"error": "The language model returned an unexpected response."},
                  status=502,
              )

          elif str(error) == "invalid_payload":
              send_json(
                  self,
                  {"error": "Invalid request."},
                  status=400,
              )

          else:
              detail = str(error)

              if API_KEY:
                  detail = detail.replace(API_KEY, "[REDACTED]")

              print(
                  f"Request processing failed: "
                  f"{type(error).__name__}: {detail[:300]}"
              )

              send_json(
                  self,
                  {"error": "The request could not be processed."},
                  status=502,
              )

      except RuntimeError as error:
          if str(error) == "missing_api_key":
              send_json(
                  self,
                  {
                      "error": (
                          "API key is not configured. "
                          "Please set GROQ_API_KEY."
                      )
                  },
                  status=503,
              )
          else:
              send_json(
                  self,
                  {
                      "error": (
                          "Sorry, something went wrong while "
                          "contacting the language model."
                      )
                  },
                  status=502,
              )

      except groq.APIConnectionError:
          print(
              "Groq connection failed. Check internet, firewall, "
              "VPN, or proxy settings."
          )
          send_json(
              self,
              {
                  "error": (
                      "Could not connect to Groq. Check your internet, "
                      "firewall, VPN, or proxy settings."
                  )
              },
              status=502,
          )

      except groq.APIStatusError as error:
          print(f"Groq API returned HTTP {error.status_code}.")
          send_json(
              self,
              {
                  "error": (
                      "Groq rejected the request. "
                      "Check your API key and model settings."
                  )
              },
              status=502,
          )

      except Exception as error:  # Keep provider details out of the browser response.
          print(f"Chat request failed: {type(error).__name__}")
          send_json(
              self,
              {
                  "error": (
                      "Sorry, something went wrong while contacting "
                      "the language model."
                  )
              },
              status=502,
          )

    def log_message(self, format_string: str, *args: Any) -> None:
        """Keep request logs concise."""
        print(f"{self.address_string()} - {format_string % args}")

    def do_DELETE(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
      """Delete cached responses."""
      if self.path == "/api/cache":
          try:
              deleted = response_cache.clear()
              send_json(self, {"deleted": deleted})
          except Exception:
              send_json(
                  self,
                  {"error": "Could not clear Redis cache."},
                  status=503,
              )
          return

      if self.path.startswith("/api/cache/"):
          cache_key = self.path[len("/api/cache/"):]

          try:
              deleted = response_cache.delete(cache_key)
              send_json(self, {"deleted": deleted})
          except Exception:
              send_json(
                  self,
                  {"error": "Could not delete cached value."},
                  status=503,
              )
          return

      send_json(self, {"error": "Not found."}, status=404)


def run_server() -> None:
    """Start the local or Render web server."""
    port = int(os.environ.get("PORT", "7860"))
    server = ThreadingHTTPServer(("0.0.0.0", port), ChatbotHandler)
    print(f"Open http://127.0.0.1:{port} in your browser.")
    print(f"Server listening on 0.0.0.0:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
