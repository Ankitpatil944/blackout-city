from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from blackstart_city.baseline import choose_greedy_action, choose_heuristic_action, run_policy_rollout
from blackstart_city.env import BlackstartCityEnv
from blackstart_city.tasks.catalog import TASK_ORDER, TASK_SPECS
from blackstart_city.tier_router import tier_router
from server.web_ui import render_web_ui

# Metadata for the OpenEnv bot to discover environment capabilities.
MANIFEST = {
    "spec_version": 1,
    "name": "blackstart_city",
    "type": "space",
    "tasks": [
        {
            "id": spec.task_id,
            "difficulty": spec.difficulty.value,
            "description": spec.description,
            "max_steps": spec.max_steps,
        }
        for spec in TASK_SPECS.values()
    ],
    "endpoints": ["/reset", "/step", "/state", "/tasks", "/grader", "/baseline", "/baseline/next", "/baseline/step", "/command/brief", "/compare", "/health", "/schema", "/web", "/manifest"]
}


app = FastAPI(
    title="Blackstart City",
    description=(
        "OpenEnv-compliant benchmark for city-scale blackout recovery. "
        "An AI agent must restart generation, energize substations, restore hospitals, "
        "telecom, water, and emergency services without triggering a second collapse."
    ),
    version="0.1.0",
    license_info={"name": "MIT"},
    contact={"name": "meta-hack-submission"},
)

# Allow all origins so HF Spaces, Colab bots, and evaluation harnesses can call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tier_router)

ENV = BlackstartCityEnv()
LAST_INFO: dict[str, Any] = {}
HEURISTIC_STATE = {"published": False, "seen_signatures": set()}


class ResetRequest(BaseModel):
    task_id: str | None = None
    seed: int | None = None


class CompareRequest(BaseModel):
    task_id: str
    seed: int = 0


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tasks")
def tasks() -> dict[str, list[dict[str, Any]]]:
    return {
        "tasks": [
            {
                "task_id": spec.task_id,
                "difficulty": spec.difficulty.value,
                "description": spec.description,
                "max_steps": spec.max_steps,
            }
            for spec in TASK_SPECS.values()
        ]
    }


@app.get("/schema")
def schema() -> dict[str, Any]:
    return {
        "task_ids": TASK_ORDER,
        "action_model": "blackstart_city.models.BlackstartAction",
        "observation_model": "blackstart_city.models.BlackstartObservation",
        "state_model": "blackstart_city.models.BlackstartState",
    }


@app.get("/manifest")
def manifest() -> dict[str, Any]:
    return MANIFEST


@app.post("/reset")
def reset(payload: ResetRequest):
    global LAST_INFO, HEURISTIC_STATE
    observation = ENV.reset(task_id=payload.task_id, seed=payload.seed)
    # Use the detailed info helper from the environment.
    LAST_INFO = ENV._info()
    HEURISTIC_STATE = {"published": False, "seen_signatures": set()}
    return {
        "observation": observation.model_dump(mode="json"),
        "info": LAST_INFO
    }


@app.post("/step")
def step(payload: dict[str, Any]):
    global LAST_INFO, HEURISTIC_STATE
    from blackstart_city.models import BlackstartAction

    action = BlackstartAction.model_validate(payload)
    observation, reward, done, info = ENV.step(action)
    LAST_INFO = info
    HEURISTIC_STATE["seen_signatures"].add(_signature(action))
    if action.action_type.value == "publish_status":
        HEURISTIC_STATE["published"] = True
    return {
        "observation": observation.model_dump(mode="json"),
        "reward": float(reward),
        "done": bool(done),
        "info": info
    }


@app.get("/state")
def state():
    return ENV.state.model_dump(mode="json")


@app.get("/grader")
def grader() -> dict[str, Any]:
    # Returns the score and status from the LAST step executed in this session.
    # OpenEnv bots call this at the end of an episode.
    res = LAST_INFO or {"score": 0.01, "resolved": False, "hospital_failures": 0}
    return {
        "score": float(res.get("score", 0.01)),
        "resolved": bool(res.get("resolved", False)),
        "hospital_failures": int(res.get("hospital_failures", 0)),
        "catastrophe": bool(res.get("catastrophe_triggered", False)),
        "constraint_violations": int(res.get("constraint_violations", 0)),
        "news_events_revealed": int(res.get("news_count", 0)),
        "rubric": res.get("rubric", {
            "safety": 0.0,
            "triage_quality": 0.0,
            "communication_clarity": 0.0,
            "resource_efficiency": 0.0,
            "overall": 0.0,
        }),
    }


@app.get("/baseline")
def baseline() -> dict[str, Any]:
    scores = {}
    for task_id in TASK_ORDER:
        env = BlackstartCityEnv()
        observation = env.reset(task_id=task_id, seed=0)
        result = run_policy_rollout(env, observation, choose_heuristic_action)
        scores[task_id] = result["info"]
    return scores


@app.get("/baseline/next")
def baseline_next() -> dict[str, Any]:
    observation = ENV._build_observation(0.0)  # type: ignore[attr-defined]
    action = choose_heuristic_action(
        observation,
        published_status=bool(HEURISTIC_STATE["published"]),
        seen_signatures=set(HEURISTIC_STATE["seen_signatures"]),
    )
    return {"action": action.model_dump(mode="json", exclude_none=True) if action is not None else None}


@app.get("/command/brief")
def command_brief() -> dict[str, Any]:
    observation = ENV._build_observation(0.0)  # type: ignore[attr-defined]
    return observation.command_center.model_dump(mode="json")


@app.post("/baseline/step")
def baseline_step() -> dict[str, Any]:
    observation = ENV._build_observation(0.0)  # type: ignore[attr-defined]
    action = choose_heuristic_action(
        observation,
        published_status=bool(HEURISTIC_STATE["published"]),
        seen_signatures=set(HEURISTIC_STATE["seen_signatures"]),
    )
    if action is None:
        return {"done": True, "action": None, "observation": observation.model_dump(mode="json")}
    # Call step() and extract the observation from the wrapped response.
    result = step(action.model_dump(mode="json", exclude_none=True))
    return {
        "done": result["done"],
        "action": action.model_dump(mode="json", exclude_none=True),
        "observation": result["observation"],  # unwrap from {obs, reward, done, info}
    }


@app.post("/compare")
def compare(payload: CompareRequest) -> dict[str, Any]:
    results = {}
    for name, chooser in {"greedy": choose_greedy_action, "heuristic": choose_heuristic_action}.items():
        env = BlackstartCityEnv()
        observation = env.reset(task_id=payload.task_id, seed=payload.seed)
        result = run_policy_rollout(env, observation, chooser)
        final_observation = result["final_observation"]
        info = result["info"]
        results[name] = {
            "task_id": payload.task_id,
            "seed": payload.seed,
            "steps": result["steps"],
            "score": float(info["score"]),
            "resolved": bool(info["resolved"]),
            "catastrophe_triggered": bool(info["catastrophe_triggered"]),
            "hospital_failures": int(info["hospital_failures"]),
            "frequency_hz": final_observation.frequency_hz,
            "reserve_margin_mw": final_observation.reserve_margin_mw,
            "served_load_mw": final_observation.served_load_mw,
            "public_trust": final_observation.command_center.public_trust,
            "coordination_score": final_observation.command_center.coordination_score,
            "command_phase": final_observation.command_center.command_phase,
            "log": result["log"],
        }
    return results


@app.get("/web", response_class=HTMLResponse)
def web():
    return render_web_ui()


def _signature(action) -> str:
    return f"{action.action_type.value}|{action.target_id or ''}|{action.requested_mw or 0}"


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
