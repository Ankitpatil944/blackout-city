from __future__ import annotations

import subprocess
import sys

import requests

from blackstart_city.baseline import choose_heuristic_action
from blackstart_city.env import BlackstartCityEnv
from blackstart_city.tasks.catalog import TASK_ORDER


def _status_prefix(success: bool = True) -> str:
    return "[OK]" if success else "[FAIL]"


def print_status(msg: str, success: bool = True) -> None:
    print(f"{_status_prefix(success)} {msg}")


def main() -> None:
    print("=== Blackstart City Submission Validator ===\n")

    try:
        env = BlackstartCityEnv()
        obs = env.reset(task_id=TASK_ORDER[0], seed=0)
        action = choose_heuristic_action(obs, published_status=False)
        if action is None:
            raise RuntimeError("Heuristic produced no action on reset.")
        env.step(action)
        print_status("Internal environment logic functional")
    except Exception as exc:
        print_status(f"Internal environment test failed: {exc}", False)
        sys.exit(1)

    base_url = "http://127.0.0.1:8000"
    try:
        requests.get(f"{base_url}/health", timeout=2)

        manifest_res = requests.get(f"{base_url}/manifest", timeout=2)
        manifest = manifest_res.json()
        if "endpoints" in manifest and "/reset" in manifest["endpoints"]:
            print_status("Server manifest discovered")

        reset_res = requests.post(f"{base_url}/reset", json={"task_id": TASK_ORDER[0], "seed": 0}, timeout=5)
        reset_data = reset_res.json()
        if "observation" in reset_data and "info" in reset_data:
            print_status("Server /reset compliant (returns observation + info)")

        observation_json = reset_data["observation"]
        action_json = {
            "action_type": "start_generator",
            "target_id": observation_json["generators"][0]["id"],
        }
        step_res = requests.post(f"{base_url}/step", json=action_json, timeout=5)
        step_data = step_res.json()
        if all(key in step_data for key in ["observation", "reward", "done", "info"]):
            print_status("Server /step compliant (returns obs, reward, done, info)")

        grader_res = requests.get(f"{base_url}/grader", timeout=2)
        grader_data = grader_res.json()
        if "score" in grader_data and isinstance(grader_data["score"], float):
            print_status("Server /grader compliant")

    except requests.exceptions.ConnectionError:
        print("[WARN] Server not running locally. Skipping live compliance tests.")
        print("   (Run 'python -m server.app' in another terminal to test compliance)")
    except Exception as exc:
        print_status(f"Server compliance check failed: {exc}", False)

    print("\nRunning unit tests...")
    ret = subprocess.call([sys.executable, "-m", "pytest", "tests/", "-q", "--no-header"])
    if ret == 0:
        print_status("All unit tests passed")
    else:
        print_status("Unit tests failed", False)

    print("\nValidation Complete.")


if __name__ == "__main__":
    main()
