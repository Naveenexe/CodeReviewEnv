---
title: CodeReviewEnv
emoji: 🐛
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
tags:
  - openenv
---

# 🐛 CodeReviewEnv

An **OpenEnv** environment where AI agents act as code reviewers. The agent reads code snippets and must identify bugs, security vulnerabilities, bad practices, and logic errors.

## Why This Environment?

Code review is a critical real-world software engineering task. Training AI agents to review code effectively can:
- Help catch bugs before they reach production
- Identify security vulnerabilities automatically
- Teach agents software engineering best practices

## Tasks

| Task | Difficulty | Description | Max Steps |
|------|-----------|-------------|-----------|
| `easy_bug` | Easy | Division-by-zero in average calculator | 3 |
| `medium_bug` | Medium | Uninitialized variable + bad boolean comparison + missing else | 5 |
| `hard_bug` | Hard | SQL injection + resource leak + duplicate-finder logic bug | 8 |

## Observation Space

```json
{
  "task_name": "string",
  "difficulty": "string",
  "description": "string",
  "code_snippet": "string",
  "step_number": "int",
  "max_steps": "int",
  "done": "bool",
  "last_reward": "float",
  "message": "string"
}
```

## Action Space

```json
{
  "review": "string — the agent's code review text"
}
```

## Reward

- **0.0** — No relevant issues found
- **0.1–0.9** — Partial credit for finding some issues
- **1.0** — All key issues identified

Reward is shaped across steps: improvement over previous best score is rewarded, repeated bad answers get a small penalty.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/reset` | POST | Start a new episode |
| `/step` | POST | Submit a code review |
| `/state` | GET | Get current environment state |
| `/tasks` | GET | List all tasks |
| `/health` | GET | Health check |

## Setup & Usage

### Local (no Docker needed)

```bash
pip install -r requirements.txt
python app.py
```

Then in another terminal:

```bash
# Reset
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task_name": "easy_bug"}'

# Step
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"task_name": "easy_bug", "review": "The function will crash with division by zero when the list is empty."}'
```

### Run Inference Script

```bash
export HF_TOKEN=hf_your_token_here
python inference.py
```

### Docker

```bash
docker build -t code-review-env .
docker run -p 7860:7860 code-review-env
```

## Baseline Scores

| Task | Model | Score | Steps |
|------|-------|-------|-------|
| easy_bug | Qwen2.5-72B-Instruct | 1.00 | 1 |
| medium_bug | Qwen2.5-72B-Instruct | 0.67 | 2 |
| hard_bug | Qwen2.5-72B-Instruct | 0.67 | 3 |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HF_TOKEN` | Hugging Face API token | required |
| `API_BASE_URL` | LLM API base URL | `https://router.huggingface.co/v1` |
| `MODEL_NAME` | Model to use | `Qwen/Qwen2.5-72B-Instruct` |
| `ENV_BASE_URL` | Environment server URL | `http://localhost:7860` |
