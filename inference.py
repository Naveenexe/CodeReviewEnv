"""
Inference Script — CodeReviewEnv
===================================
Runs an LLM agent against all 3 tasks and emits structured stdout logs.

STDOUT FORMAT:
    [START] task=<task_name> env=<benchmark> model=<model_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>

Usage:
    HF_TOKEN=hf_xxx python inference.py
"""

import os
import sys
import json
import requests
from openai import OpenAI

# ── Config ────────────────────────────────────────────────────────────────────
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:7860")
BENCHMARK = "code-review-env"
MAX_STEPS = 5
TEMPERATURE = 0.3
MAX_TOKENS = 512
SUCCESS_THRESHOLD = 0.7

TASKS = ["easy_bug", "medium_bug", "hard_bug"]

SYSTEM_PROMPT = """You are an expert software engineer performing a code review.
Your job is to carefully read the provided code snippet and identify ALL bugs, issues, and bad practices.

Be specific and thorough. Include:
- Logic errors and bugs
- Security vulnerabilities (e.g. SQL injection)
- Uninitialized variables or missing checks
- Bad coding practices (e.g. comparing with == True)
- Resource leaks (e.g. unclosed connections)
- Performance issues

Write your review clearly, naming each issue explicitly.
"""

# ── OpenAI Client (pointed at HF router) ─────────────────────────────────────
client = None
if API_KEY and API_KEY != "":
    try:
        client = OpenAI(
            api_key=API_KEY,
            base_url=API_BASE_URL
        )
    except Exception as e:
        print(f"Warning: Failed to initialize OpenAI client: {e}", file=sys.stderr)


def call_env(endpoint: str, method: str = "GET", payload: dict = None) -> dict:
    """Call the local environment server."""
    url = f"{ENV_BASE_URL}{endpoint}"
    try:
        if method == "POST":
            resp = requests.post(url, json=payload, timeout=30)
        else:
            resp = requests.get(url, params=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def get_llm_review(code_snippet: str, description: str, history: list) -> str:
    """Call the LLM to get a code review. Falls back to mock if no API key."""
    if not API_KEY or API_KEY == "":
        return "[MOCK REVIEW] This code looks mostly fine, but I should check for potential issues like division by zero or security leaks."

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add history for multi-turn refinement
    for h in history:
        messages.append({"role": "assistant", "content": h["review"]})
        messages.append({"role": "user", "content": f"Feedback: {h['feedback']}. Please refine your review."})

    user_msg = f"""Task: {description}

Code to review:
{code_snippet}

Please identify all bugs, security issues, and bad practices in this code."""

    messages.append({"role": "user", "content": user_msg})

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Warning: LLM call failed ({e}). Falling back to mock.", file=sys.stderr)
        return "[MOCK REVIEW] I identified some potential issues in the code snippet."


def run_task(task_name: str) -> dict:
    """Run a single task episode and return results."""
    # Reset environment
    reset_data = call_env("/reset", method="POST", payload={"task_name": task_name})
    if "error" in reset_data:
        return {"error": reset_data["error"], "task": task_name}

    obs = reset_data
    code_snippet = obs.get("code_snippet", "")
    description = obs.get("description", "")
    max_steps = obs.get("max_steps", MAX_STEPS)

    print(f"[START] task={task_name} env={BENCHMARK} model={MODEL_NAME}", flush=True)

    step_rewards = []
    history = []
    final_score = 0.0
    done = False
    step_num = 0
    last_error = None

    for step_num in range(1, max_steps + 1):
        if done:
            break

        # Get LLM review
        review = get_llm_review(code_snippet, description, history)

        # Submit to environment
        step_data = call_env("/step", method="POST", payload={
            "task_name": task_name,
            "review": review
        })

        if "error" in step_data and "observation" not in step_data:
            last_error = step_data["error"]
            print(f"[STEP] step={step_num} reward=0.00 done=false", flush=True)
            break

        reward_info = step_data.get("reward", {})
        score = reward_info.get("score", 0.0)
        step_reward = step_data.get("info", {}).get("step_reward", score) if step_num == 1 else score
        done = step_data.get("done", False)
        feedback = reward_info.get("feedback", "")
        last_error = None

        step_rewards.append(round(score, 2))
        final_score = step_data.get("info", {}).get("best_score", score)

        print(
            f"[STEP] step={step_num} reward={score:.2f} done={'true' if done else 'false'}",
            flush=True
        )

        history.append({"review": review, "feedback": feedback})

        if done:
            break

    success = final_score >= SUCCESS_THRESHOLD
    rewards_str = ",".join(f"{r:.2f}" for r in step_rewards)

    print(
        f"[END] success={'true' if success else 'false'} steps={step_num} score={final_score:.2f} rewards={rewards_str}",
        flush=True
    )

    return {
        "task": task_name,
        "score": final_score,
        "steps": step_num,
        "success": success,
        "rewards": step_rewards
    }


def main():
    print(f"Starting CodeReviewEnv inference with model: {MODEL_NAME}", file=sys.stderr)
    print(f"Environment URL: {ENV_BASE_URL}", file=sys.stderr)
    print("-" * 60, file=sys.stderr)

    results = []
    for task_name in TASKS:
        result = run_task(task_name)
        results.append(result)
        print("-" * 60, file=sys.stderr)

    # Summary
    print("\n=== SUMMARY ===", file=sys.stderr)
    total_score = 0.0
    for r in results:
        score = r.get("score", 0.0)
        total_score += score
        print(f"  {r['task']}: score={score:.2f} steps={r.get('steps', 0)} success={r.get('success', False)}", file=sys.stderr)

    avg_score = total_score / len(TASKS)
    print(f"\n  Average score: {avg_score:.2f}", file=sys.stderr)


if __name__ == "__main__":
    main()
