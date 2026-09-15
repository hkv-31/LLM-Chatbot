# LLM Chatbot

## Overview

LLM Chatbot is a small API-powered conversational chatbot built with Python and the Groq API. It sends the current conversation to Groq's Responses API, displays the generated answer in a clean browser UI, and keeps follow-up questions in context. The HTML, CSS, JavaScript, and Python server are kept together in `app.py` for easy review.

## Features

- Conversational AI
- Multi-turn conversation
- Groq Responses API integration
- Simple light-mode browser UI
- Environment-variable API key management
- Friendly error handling
- GitHub-ready
- Render-ready

## Tech Stack

- Python 3.10+
- Groq Python SDK
- Groq Responses API
- python-dotenv
- Python standard library HTTP server
- Git/GitHub
- Render

## Project Structure

```text
llm-chatbot/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── .env.example
└── assets/
    └── .gitkeep
```

## Prerequisites

You need Python 3.10 or newer, a Groq API key, Git, and an internet connection.

## Local Setup

Clone the repository and enter the project directory:

```bash
git clone <repository-url>
cd llm-chatbot
```

Create and activate a virtual environment.

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create `.env` from `.env.example`, then replace the placeholder with your real Groq key. Do not commit `.env`.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

The optional `GROQ_MODEL` variable can be set to any model available to your Groq account. If omitted, the app uses `openai/gpt-oss-20b`.

## Run the Application

```bash
python app.py
```

Open `http://127.0.0.1:7860` in your browser. The app binds to `0.0.0.0` for hosting and reads `PORT` so it can run on Render.

## Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| `GROQ_API_KEY` | Yes | Your Groq API key. |
| `GROQ_MODEL` | No | Model name; defaults to `openai/gpt-oss-20b`. |
| `PORT` | No | Port supplied by Render; defaults locally to `7860`. |

## GitHub Setup

After reviewing the files and testing locally:

```bash
git init
git add .
git commit -m "Initial commit: add LLM chatbot"
git branch -M main
git remote add origin <repository-url>
git push -u origin main
```

Replace `<repository-url>` with your own GitHub repository URL.

## Deployment on Render

1. Push the project to GitHub.
2. Create a Render Web Service.
3. Connect the GitHub repository.
4. Select a Python runtime.
5. Set the install command to `pip install -r requirements.txt`.
6. Set the start command to `python app.py`.

The app uses `server_name="0.0.0.0"` and the `PORT` environment variable supplied by Render.

7. Add `GROQ_API_KEY` as a Render environment variable.
8. Optionally add `GROQ_MODEL`.
9. Deploy the service.
10. Open the generated Render URL.

## Security

- Never commit `.env`.
- Never expose API keys in source code.
- Never upload API keys to GitHub.
- Use Render environment variables for deployment.

## Example Prompts

- Explain machine learning in simple terms.
- What is the difference between Python lists and tuples?
- Help me understand neural networks.
- Give me a beginner-friendly explanation of APIs.
- Write a short study plan for learning Python.

## Future Improvements

These are ideas for future versions, not implemented features:

- Streaming responses
- Conversation export
- Custom system prompts
- Model selection
- Chat history persistence
- Authentication
- RAG/document question answering

## Learning Outcomes

This project demonstrates:

- Calling an LLM API
- Prompt handling
- Conversation history
- Python application development
- Environment-variable security
- Git/GitHub workflow
- Cloud deployment
