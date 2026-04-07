"""
CodeReviewEnv — Core Environment
Implements OpenEnv interface: reset(), step(), state()
"""

from pydantic import BaseModel
from typing import Any, Dict, Optional
from tasks import TASKS, grade_response


# ── Typed Models (OpenEnv spec) ──────────────────────────────────────────────

class Observation(BaseModel):
    task_name: str
    difficulty: str
    description: str
    code_snippet: str
    step_number: int
    max_steps: int
    done: bool
    last_reward: float
    message: str


class Action(BaseModel):
    review: str  # The agent's code review text


class Reward(BaseModel):
    score: float       # 0.0 – 1.0
    partial: bool      # True if partially correct
    done: bool
    feedback: str


class EnvironmentState(BaseModel):
    task_name: str
    step_number: int
    max_steps: int
    cumulative_reward: float
    done: bool
    history: list


# ── Environment ───────────────────────────────────────────────────────────────

class CodeReviewEnv:
    def __init__(self, task_name: str = "easy_bug"):
        if task_name not in TASKS:
            raise ValueError(f"Unknown task: {task_name}. Choose from {list(TASKS.keys())}")
        self.task_name = task_name
        self.task = TASKS[task_name]
        self._step_number = 0
        self._done = False
        self._cumulative_reward = 0.0
        self._history = []
        self._best_score = 0.0

    def reset(self) -> Observation:
        """Reset environment to initial state."""
        self._step_number = 0
        self._done = False
        self._cumulative_reward = 0.0
        self._history = []
        self._best_score = 0.0

        return Observation(
            task_name=self.task_name,
            difficulty=self.task["difficulty"],
            description=self.task["description"],
            code_snippet=self.task["code_snippet"],
            step_number=0,
            max_steps=self.task["max_steps"],
            done=False,
            last_reward=0.0,
            message="Review the code snippet and identify all bugs, issues, and bad practices."
        )

    def step(self, action: Action) -> tuple[Observation, Reward, bool, Dict[str, Any]]:
        """
        Take a step: agent submits a review.
        Returns (observation, reward, done, info)
        """
        if self._done:
            obs = self._make_observation(0.0)
            reward = Reward(score=0.0, partial=False, done=True, feedback="Episode already done.")
            return obs, reward, True, {"error": "Episode already finished"}

        self._step_number += 1

        # Grade the review
        score = grade_response(self.task_name, action.review)

        # Reward shaping:
        # - Reward improvement over best so far (encourages refinement)
        # - Penalize if same bad answer repeated
        improvement = max(0.0, score - self._best_score)
        step_reward = score if self._step_number == 1 else improvement

        # Small penalty for using all steps without improvement
        if self._step_number > 1 and improvement == 0.0:
            step_reward = -0.05

        step_reward = round(max(-0.1, min(1.0, step_reward)), 2)
        self._cumulative_reward += step_reward
        self._best_score = max(self._best_score, score)

        # Done conditions
        done = False
        if score >= 1.0:
            done = True
            feedback = "Perfect review! All issues identified."
        elif self._step_number >= self.task["max_steps"]:
            done = True
            feedback = f"Max steps reached. Best score: {self._best_score}"
        else:
            if score == 0.0:
                feedback = "No relevant issues found. Look more carefully at the code."
            elif score < 0.5:
                feedback = "Some issues found but missing key problems. Keep looking."
            else:
                feedback = "Good progress! You found some issues. Can you find more?"

        self._done = done
        self._history.append({
            "step": self._step_number,
            "review_snippet": action.review[:100],
            "score": score,
            "step_reward": step_reward
        })

        obs = self._make_observation(step_reward)
        reward = Reward(
            score=score,
            partial=(0.0 < score < 1.0),
            done=done,
            feedback=feedback
        )

        info = {
            "step": self._step_number,
            "score": score,
            "best_score": self._best_score,
            "cumulative_reward": self._cumulative_reward,
        }

        return obs, reward, done, info

    def state(self) -> EnvironmentState:
        """Return current environment state."""
        return EnvironmentState(
            task_name=self.task_name,
            step_number=self._step_number,
            max_steps=self.task["max_steps"],
            cumulative_reward=round(self._cumulative_reward, 2),
            done=self._done,
            history=self._history
        )

    def _make_observation(self, last_reward: float) -> Observation:
        return Observation(
            task_name=self.task_name,
            difficulty=self.task["difficulty"],
            description=self.task["description"],
            code_snippet=self.task["code_snippet"],
            step_number=self._step_number,
            max_steps=self.task["max_steps"],
            done=self._done,
            last_reward=last_reward,
            message="Continue your review or refine your previous answer."
        )
