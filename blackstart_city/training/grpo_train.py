import argparse
import json
import os
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import torch
from datasets import load_dataset
from unsloth import FastLanguageModel, PatchFastRL, is_bfloat16_supported

PatchFastRL("GRPO", FastLanguageModel)

from trl import GRPOConfig, GRPOTrainer
from transformers import TrainerCallback, TrainerControl, TrainerState, TrainingArguments
from blackstart_city.training.model_utils import parse_action_text
from blackstart_city.training.build_dataset import observation_to_prompt
from blackstart_city.env import BlackstartCityEnv
from blackstart_city.models import (
    ActionType,
    BlackstartAction,
    Constraint,
    StatusUpdate,
)
from blackstart_city.tasks.catalog import TASK_ORDER
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

console = Console()

BASE_REWARD_KEYS = [
    "env_step_reward_func",
    "format_reward_func",
    "alignment_reward_func",
    "action_quality_reward_func",
    "constraint_reward_func",
    "failure_context_reward_func",
]
REWARD_LABELS = [
    ("Env Step",        "#FFFFFF"),
    ("Format",          "#FF00FF"),
    ("Alignment",       "#00CCFF"),
    ("Tact. Quality",   "#00FF66"),
    ("Constraint",      "#FFD700"),
    ("Fail. Avoid",     "#FF6B6B"),
]

# Weights: env_step gets 0.30 (ground truth); remaining 5 share 0.70 equally.
REWARD_WEIGHTS = [0.30, 0.14, 0.14, 0.14, 0.14, 0.14]


def _print_banner(model_name: str, max_steps: int, output_dir: str, report_to: str) -> None:
    banner = Text()
    banner.append("  ██████╗ ██╗      █████╗  ██████╗██╗  ██╗\n", style="bold #00FFCC")
    banner.append("  ██╔══██╗██║     ██╔══██╗██╔════╝██║ ██╔╝\n", style="bold #00FFCC")
    banner.append("  ██████╔╝██║     ███████║██║     █████╔╝ \n", style="bold #00FFCC")
    banner.append("  ██╔══██╗██║     ██╔══██║██║     ██╔═██╗ \n", style="bold #00FFCC")
    banner.append("  ██████╔╝███████╗██║  ██║╚██████╗██║  ██╗\n", style="bold #00FFCC")
    banner.append("  ╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝\n", style="bold #00FFCC")
    banner.append("       BLACKSTART CITY  ·  GRPO TRAINING", style="bold white")
    console.print(Panel(banner, border_style="#00FFCC", padding=(0, 2)))

    cfg = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    cfg.add_column(style="bold #888888")
    cfg.add_column(style="bold white")
    cfg.add_row("Model",       model_name)
    cfg.add_row("Max Steps",   str(max_steps))
    cfg.add_row("Output Dir",  output_dir)
    cfg.add_row("Rewards",     "6 signals  ·  env_step(0.30) + 5×proxy(0.14)")
    cfg.add_row("Tracking",    report_to.upper())
    console.print(Panel(cfg, title="[bold #00FFCC]Config[/]", border_style="#333333"))


def _resolve_base_and_adapter(
    model_name: str, adapter_path: str | None
) -> tuple[str, str | None]:
    """Resolve base-model + optional LoRA adapter path."""
    if adapter_path:
        return model_name, adapter_path

    maybe_dir = Path(model_name)
    adapter_cfg = maybe_dir / "adapter_config.json"
    full_cfg = maybe_dir / "config.json"

    if maybe_dir.is_dir() and adapter_cfg.exists() and not full_cfg.exists():
        with adapter_cfg.open("r", encoding="utf-8") as f:
            cfg = json.load(f)
        base_model = cfg.get("base_model_name_or_path")
        if not base_model:
            raise ValueError(
                f"Adapter config found at {adapter_cfg}, but base_model_name_or_path is missing."
            )
        return base_model, str(maybe_dir)

    return model_name, None


def _restore_env_state_from_obs(env: BlackstartCityEnv, obs_data: dict) -> None:
    """
    Patch a freshly-reset env's state with asset fields from an observation dict.

    This is the bridge between offline dataset observations and live env dynamics:
    it lets env.step() produce a ground-truth reward for any serialised state,
    closing the RL loop without requiring the model to have generated that state
    on-policy.
    """
    state = env._state
    if state is None:
        return

    # ── Generators ────────────────────────────────────────────────────────────
    for gen_obs in obs_data.get("generators", []):
        for gen in state.generators:
            if gen.id == gen_obs["id"]:
                gen.online = gen_obs.get("online", gen.online)
                gen.current_output_mw = gen_obs.get("current_output_mw", gen.current_output_mw)
                gen.startup_steps_remaining = gen_obs.get(
                    "startup_steps_remaining", gen.startup_steps_remaining
                )
                break

    # ── Substations ───────────────────────────────────────────────────────────
    for sub_obs in obs_data.get("substations", []):
        for sub in state.substations:
            if sub.id == sub_obs["id"]:
                sub.energized = sub_obs.get("energized", sub.energized)
                break

    # ── Lines ─────────────────────────────────────────────────────────────────
    for line_obs in obs_data.get("lines", []):
        for line in state.lines:
            if line.id == line_obs["id"]:
                line.closed = line_obs.get("closed", line.closed)
                line.damaged = line_obs.get("damaged", line.damaged)
                line.tripped = line_obs.get("tripped", line.tripped)
                line.inspected = line_obs.get("inspected", line.inspected)
                break

    # ── Critical nodes ────────────────────────────────────────────────────────
    for node_obs in obs_data.get("critical_nodes", []):
        for node in state.critical_nodes:
            if node.id == node_obs["id"]:
                node.powered = node_obs.get("powered", node.powered)
                node.backup_minutes_remaining = node_obs.get(
                    "backup_minutes_remaining", node.backup_minutes_remaining
                )
                break

    # ── Zones ─────────────────────────────────────────────────────────────────
    for zone_obs in obs_data.get("zones", []):
        for zone in state.zones:
            if zone.id == zone_obs["id"]:
                zone.restored_pct = zone_obs.get("restored_pct", zone.restored_pct)
                break

    # ── Scalar grid metrics ───────────────────────────────────────────────────
    state.frequency_hz = obs_data.get("frequency_hz", state.frequency_hz)
    state.available_generation_mw = obs_data.get(
        "available_generation_mw", state.available_generation_mw
    )
    state.served_load_mw = obs_data.get("served_load_mw", state.served_load_mw)
    state.reserve_margin_mw = obs_data.get("reserve_margin_mw", state.reserve_margin_mw)
    state.step_count = obs_data.get("step", state.step_count)

    # ── Active constraints ────────────────────────────────────────────────────
    if obs_data.get("active_constraints"):
        try:
            state.active_constraints = [
                Constraint.model_validate(c) for c in obs_data["active_constraints"]
            ]
        except Exception:
            pass

    # ── News feed ─────────────────────────────────────────────────────────────
    if obs_data.get("news_feed"):
        from blackstart_city.models import NewsEvent
        try:
            state.news_feed = [NewsEvent.model_validate(n) for n in obs_data["news_feed"]]
        except Exception:
            pass

    env._recompute_state()


# ─────────────────────────────────────────────────────────────────────────────
# Reward functions
# ─────────────────────────────────────────────────────────────────────────────

def env_step_reward_func(prompts, completions, **kwargs) -> list[float]:
    """
    Ground-truth reward signal: restores env state from the serialised
    observation JSON and calls env.step(action) to obtain the real environment
    reward.  This closes the RL loop — model outputs are evaluated against live
    grid dynamics, not proxy heuristics alone.

    Reward is normalised to [-1, 1] (env step rewards are typically in [-2, 2]).
    """
    rewards = []
    for prompt, comp in zip(prompts, completions):
        try:
            prompt_text = prompt[-1]["content"] if isinstance(prompt, list) else prompt
            obs_json_str = prompt_text.split("Observation:\n")[-1]
            obs_data = json.loads(obs_json_str)
            comp_text = comp[0]["content"] if isinstance(comp, list) else comp
            action = parse_action_text(comp_text)

            if action is None:
                rewards.append(-0.5)
                continue

            task_id = obs_data.get("task_id", TASK_ORDER[0])
            env = BlackstartCityEnv()
            env.reset(task_id=task_id, seed=0)
            _restore_env_state_from_obs(env, obs_data)

            _, raw_reward, _, _ = env.step(action)

            # Normalise: env rewards are roughly in [-2, 2]; map to [-1, 1].
            normalized = max(-1.0, min(1.0, raw_reward / 2.0))
            rewards.append(normalized)

        except Exception:
            rewards.append(0.0)
    return rewards


def format_reward_func(completions, **kwargs) -> list[float]:
    """Gate reward — valid JSON action = 1.0, with partial credit for structure."""
    rewards = []
    for comp in completions:
        try:
            text = comp[0]["content"] if isinstance(comp, list) else comp
            reward = 0.0
            if "{" in text and "}" in text:
                reward += 0.2
            if '"action_type"' in text:
                reward += 0.3
            action = parse_action_text(text)
            if action is not None:
                reward = 1.0
            rewards.append(reward)
        except Exception:
            rewards.append(0.0)
    return rewards


def alignment_reward_func(prompts, completions, **kwargs) -> list[float]:
    """Rewards alignment with command-center role recommendations.

    When the obs has no recommendations (rare — build_dataset always emits
    them), reward is 0. We deliberately do NOT add a heuristic proxy here:
    a proxy would conflict with the constraint and action_quality signals
    and add noise to the learning signal.
    """
    rewards = []
    for prompt, comp in zip(prompts, completions):
        try:
            prompt_text = prompt[-1]["content"] if isinstance(prompt, list) else prompt
            obs_json_str = prompt_text.split("Observation:\n")[-1]
            obs = json.loads(obs_json_str)
            comp_text = comp[0]["content"] if isinstance(comp, list) else comp
            action = parse_action_text(comp_text)

            if action is None:
                rewards.append(-0.2)
                continue

            recs = obs.get("command_center", {}).get("role_recommendations", [])
            if not recs:
                rewards.append(0.0)
                continue

            reward = 0.0
            for rec in recs:
                rec_action = rec.get("proposed_action")
                if rec_action and rec_action.get("action_type") == action.action_type.value:
                    if rec_action.get("target_id") == action.target_id:
                        reward = 1.0
                        break
            rewards.append(reward)
        except Exception:
            rewards.append(0.0)
    return rewards


def action_quality_reward_func(prompts, completions, **kwargs) -> list[float]:
    """Graded reward from observation state."""
    rewards = []
    for prompt, comp in zip(prompts, completions):
        try:
            prompt_text = prompt[-1]["content"] if isinstance(prompt, list) else prompt
            obs_json_str = prompt_text.split("Observation:\n")[-1]
            obs_data = json.loads(obs_json_str)
            comp_text = comp[0]["content"] if isinstance(comp, list) else comp
            action = parse_action_text(comp_text)

            if action is None:
                rewards.append(-0.5)
                continue

            score = 0.0
            critical_nodes = obs_data.get("critical_nodes", [])
            generators = obs_data.get("generators", [])
            freq = obs_data.get("frequency_hz", 60.0)
            unpowered_critical = [n for n in critical_nodes if not n.get("powered")]

            for node in critical_nodes:
                if not node.get("powered") and action.target_id == node.get("id"):
                    backup = node.get("backup_minutes_remaining", 999)
                    score += 1.0 if backup < 15 else 0.5 if backup < 30 else 0.2

            online_count = sum(1 for g in generators if g.get("online"))
            if online_count == 0 and action.action_type.value == "start_generator":
                score += 1.0

            if freq < 59.5 and action.action_type.value == "shed_zone":
                score += 0.8

            if unpowered_critical and action.action_type.value == "restore_zone":
                unpowered_ids = {n.get("id") for n in unpowered_critical}
                if action.target_id not in unpowered_ids:
                    score -= 0.5

            rewards.append(max(-1.0, min(1.0, score)))
        except Exception:
            rewards.append(0.0)
    return rewards


def constraint_reward_func(prompts, completions, **kwargs) -> list[float]:
    """Penalizes actions that violate scenario constraints visible in the observation."""
    rewards = []
    for prompt, comp in zip(prompts, completions):
        try:
            prompt_text = prompt[-1]["content"] if isinstance(prompt, list) else prompt
            obs_json_str = prompt_text.split("Observation:\n")[-1]
            obs_data = json.loads(obs_json_str)
            comp_text = comp[0]["content"] if isinstance(comp, list) else comp
            action = parse_action_text(comp_text)

            if action is None:
                rewards.append(-0.5)
                continue

            score = 0.5

            constraints = obs_data.get("active_constraints", [])
            if constraints:
                for c in constraints:
                    if not c.get("active", True):
                        continue
                    ct = c.get("constraint_type", "")

                    if ct == "forbidden_target":
                        if (action.action_type.value == c.get("forbidden_action_type")
                                and action.target_id == c.get("forbidden_target_id")):
                            score -= 1.0

                    if ct == "conditional_limit":
                        if (action.action_type.value == "restore_zone"
                                and action.target_id == c.get("limit_target_id")
                                and action.requested_mw is not None
                                and c.get("limit_mw") is not None
                                and action.requested_mw > c["limit_mw"]):
                            score -= 0.8

                    if ct == "priority_order":
                        if (action.action_type.value == "restore_zone"
                                and action.target_id == c.get("before_restoring")):
                            first_id = c.get("must_restore_first")
                            nodes = obs_data.get("critical_nodes", [])
                            first_node = next(
                                (n for n in nodes if n.get("id") == first_id), None
                            )
                            if first_node and not first_node.get("powered"):
                                score -= 0.7
            else:
                freq = obs_data.get("frequency_hz", 60.0)
                reserve = obs_data.get("reserve_margin_mw", 0)

                if freq < 59.5:
                    if action.action_type.value == "shed_zone":
                        score += 0.3
                    elif action.action_type.value in ("restore_zone", "restore_critical_node",
                                                      "energize_substation"):
                        score -= 0.3

                if reserve < 5 and action.action_type.value == "restore_zone":
                    score -= 0.4

                if reserve > 20 and action.action_type.value == "shed_zone":
                    score -= 0.2

            news = obs_data.get("news_feed", [])
            if news and any(n.get("impact_level") == "critical" for n in news):
                for n in news:
                    if n.get("reduces_backup_node") and action.target_id == n["reduces_backup_node"]:
                        score += 0.5

            rewards.append(max(-1.0, min(1.0, score)))
        except Exception:
            rewards.append(0.0)
    return rewards


def failure_context_reward_func(prompts, completions, **kwargs) -> list[float]:
    """
    Theory-of-Mind reward: rewards the model for NOT repeating actions that
    failed in previous tiers (visible in `failure_context`).

    When `failure_context` is absent (the dataset only injects failures on
    every 3rd episode) reward is 0 — there is no signal to give. We
    intentionally do NOT add a heuristic anti-pattern check here; that
    overlaps with `constraint_reward_func` and `action_quality_reward_func`
    and would distort the gradient on most rows.
    """
    rewards = []
    for prompt, comp in zip(prompts, completions):
        try:
            prompt_text = prompt[-1]["content"] if isinstance(prompt, list) else prompt
            obs_json_str = prompt_text.split("Observation:\n")[-1]
            obs_data = json.loads(obs_json_str)
            comp_text = comp[0]["content"] if isinstance(comp, list) else comp
            action = parse_action_text(comp_text)

            if action is None:
                rewards.append(-0.2)
                continue

            failure_ctx = obs_data.get("failure_context", [])
            if not failure_ctx:
                rewards.append(0.0)
                continue

            was_failure = False
            for fail in failure_ctx:
                for failed_action in fail.get("failed_actions", []):
                    if (failed_action.get("action_type") == action.action_type.value
                            and failed_action.get("target_id") == action.target_id):
                        was_failure = True
                        break
                if was_failure:
                    break
            rewards.append(-1.0 if was_failure else 0.5)
        except Exception:
            rewards.append(0.0)
    return rewards


# ─────────────────────────────────────────────────────────────────────────────
# Callbacks
# ─────────────────────────────────────────────────────────────────────────────

class RichGRPOCallback(TrainerCallback):
    """Prints a pretty reward table to the terminal every `log_every` steps."""

    def __init__(self, log_every: int = 5):
        self.log_every = log_every
        self._step = 0

    def on_log(self, args: TrainingArguments, state: TrainerState,
               control: TrainerControl, logs=None, **kwargs):
        if logs is None:
            return
        self._step += 1
        if self._step % self.log_every != 0:
            return

        step = int(logs.get("step", state.global_step))
        loss = logs.get("loss", logs.get("train_loss", None))
        lr   = logs.get("learning_rate", None)

        tbl = Table(
            title=f"[bold #00FFCC]Step {step}/{args.max_steps}[/]",
            box=box.ROUNDED,
            border_style="#333333",
            show_header=True,
            header_style="bold white",
            padding=(0, 1),
        )
        tbl.add_column("Reward Signal",  style="bold",  min_width=16)
        tbl.add_column("Value",           justify="right", min_width=8)
        tbl.add_column("Bar",             min_width=20)

        for base_key, (label, color) in zip(BASE_REWARD_KEYS, REWARD_LABELS):
            val = None
            for k, v in logs.items():
                if base_key in k:
                    val = v
                    break
            if val is None:
                continue
            bar_len = int(min(max((val + 1) / 2, 0), 1) * 20)
            bar = f"[{color}]{'█' * bar_len}{'░' * (20 - bar_len)}[/{color}]"
            val_str = f"[{color}]{val:+.4f}[/{color}]"
            tbl.add_row(f"[{color}]{label}[/{color}]", val_str, bar)

        extras = []
        if loss is not None:
            extras.append(f"loss [bold white]{loss:.4f}[/]")
        if lr is not None:
            extras.append(f"lr [bold white]{lr:.2e}[/]")
        footer = "  ·  ".join(extras) if extras else ""

        console.print(tbl)
        if footer:
            console.print(f"  [dim]{footer}[/dim]\n")


_FALLBACK_STATUS = StatusUpdate(
    summary="Recovery operations are in progress across the grid.",
    critical_services="Teams are working to restore critical services.",
    next_action="Continue coordinated restoration efforts.",
    owner="city restoration commander",
)


class EnvEvalCallback(TrainerCallback):
    """
    Runs held-out evaluation episodes in the live environment every N training
    steps and logs episode-level metrics (score, catastrophe rate, hospital
    failures) to W&B.

    The agent under test is the GRPO-trained model itself: this callback
    formats the observation with the same prompt template used during
    training, generates one action, parses it, and steps the env. If the
    model emits malformed output we fall back to a status publish so the
    episode keeps running and the failure shows up as a low score.
    """

    EVAL_SEED = 999  # held-out seed never seen during dataset construction

    def __init__(self, eval_every: int = 50, n_tasks: int = 2, max_episode_steps: int = 40):
        self.eval_every = eval_every
        self.n_tasks = n_tasks
        self.max_episode_steps = max_episode_steps
        self._last_eval_step = -1

    def _generate_action(self, model, tokenizer, obs) -> BlackstartAction:
        prompt_text = observation_to_prompt(obs)
        messages = [
            {"role": "system", "content": (
                "You are a city blackout restoration policy. "
                "Return exactly one valid JSON action object and nothing else."
            )},
            {"role": "user", "content": "Observation:\n" + prompt_text},
        ]
        try:
            inputs = tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                return_tensors="pt",
            ).to(model.device)
            with torch.no_grad():
                output_ids = model.generate(
                    inputs,
                    max_new_tokens=150,
                    do_sample=False,
                    pad_token_id=tokenizer.eos_token_id,
                )
            generated = output_ids[0][inputs.shape[1]:]
            text = tokenizer.decode(generated, skip_special_tokens=True)
            parsed = parse_action_text(text)
            if parsed is not None:
                return parsed
        except Exception as exc:
            console.print(f"  [dim]eval generate failed: {exc}[/dim]")
        return BlackstartAction(
            action_type=ActionType.PUBLISH_STATUS,
            status_update=_FALLBACK_STATUS,
        )

    def on_log(self, args: TrainingArguments, state: TrainerState,
               control: TrainerControl, logs=None, **kwargs):
        step = state.global_step
        if step - self._last_eval_step < self.eval_every:
            return
        self._last_eval_step = step

        model = kwargs.get("model")
        tokenizer = kwargs.get("processing_class") or kwargs.get("tokenizer")
        if model is None or tokenizer is None:
            return  # No model handle yet — first log fires before training starts

        scores, hospital_failures, catastrophes, steps_to_done, parse_failures = [], [], [], [], []

        try:
            from unsloth import FastLanguageModel
            FastLanguageModel.for_inference(model)
        except Exception:
            pass
        model.eval()

        for task_id in TASK_ORDER[: self.n_tasks]:
            env = BlackstartCityEnv()
            obs = env.reset(task_id=task_id, seed=self.EVAL_SEED)
            ep_parse_failures = 0
            ep_step = 0

            while not obs.done and ep_step < self.max_episode_steps:
                action = self._generate_action(model, tokenizer, obs)
                if action.action_type == ActionType.PUBLISH_STATUS and action.status_update is _FALLBACK_STATUS:
                    ep_parse_failures += 1
                obs, _, done, _ = env.step(action)
                ep_step += 1
                if done:
                    break

            s = env._state
            scores.append(s.score if s else 0.0)
            hospital_failures.append(s.hospital_failures if s else 0)
            catastrophes.append(1 if (s and s.catastrophe_triggered) else 0)
            steps_to_done.append(s.step_count if s else 0)
            parse_failures.append(ep_parse_failures)

        # Restore training mode so the next training step is unaffected
        try:
            from unsloth import FastLanguageModel
            FastLanguageModel.for_training(model)
        except Exception:
            pass
        model.train()

        try:
            import wandb
            if wandb.run is not None:
                wandb.log(
                    {
                        "eval/grpo_score_mean":            sum(scores) / len(scores),
                        "eval/grpo_score_min":             min(scores),
                        "eval/grpo_hospital_failures":     sum(hospital_failures) / len(hospital_failures),
                        "eval/grpo_catastrophe_rate":      sum(catastrophes) / len(catastrophes),
                        "eval/grpo_steps_to_done":         sum(steps_to_done) / len(steps_to_done),
                        "eval/grpo_parse_failures":        sum(parse_failures) / len(parse_failures),
                    },
                    step=step,
                )
                console.print(
                    f"  [bold #00FFCC]EnvEval[/] step={step}  "
                    f"grpo_score={sum(scores)/len(scores):.3f}  "
                    f"catastrophe_rate={sum(catastrophes)/len(catastrophes):.2f}  "
                    f"parse_failures={sum(parse_failures)/len(parse_failures):.1f}\n"
                )
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name",    default="Qwen/Qwen2.5-3B-Instruct")
    parser.add_argument("--adapter-path",  default=None,
                        help="Optional LoRA adapter path to continue training from SFT output.")
    parser.add_argument("--output-dir",    default="artifacts/blackstart-city-grpo")
    parser.add_argument("--dataset",       default="dataset.jsonl",
                        help="Path to training dataset")
    parser.add_argument("--max-steps",     type=int, default=500)
    parser.add_argument("--report-to",     default="wandb",
                        choices=["wandb", "tensorboard", "none"],
                        help="Experiment tracking backend (default: wandb)")
    parser.add_argument("--wandb-project", default="blackstart-city",
                        help="W&B project name")
    parser.add_argument("--wandb-run-name", default=None,
                        help="W&B run display name (auto-generated if omitted)")
    args = parser.parse_args()

    base_model_name, adapter_path = _resolve_base_and_adapter(args.model_name, args.adapter_path)
    os.makedirs(args.output_dir, exist_ok=True)
    _print_banner(base_model_name, args.max_steps, args.output_dir, args.report_to)

    if adapter_path:
        console.print(
            f"[bold #FFD700]↪ Continuing from adapter:[/] [white]{adapter_path}[/]"
        )

    # ── Experiment tracking ───────────────────────────────────────────────────
    if args.report_to == "wandb":
        try:
            import wandb
            wandb.init(
                project=args.wandb_project,
                name=args.wandb_run_name,
                config={
                    "model_name":            base_model_name,
                    "adapter_path":          adapter_path,
                    "max_steps":             args.max_steps,
                    "learning_rate":         5e-6,
                    "lr_scheduler":          "cosine",
                    "num_generations":       8,
                    "per_device_batch_size": 1,
                    "gradient_accumulation": 2,
                    "max_seq_length":        4096,
                    "lora_rank":             16,
                    "reward_weights":        REWARD_WEIGHTS,
                    "reward_functions": [
                        "env_step (ground-truth)",
                        "format",
                        "alignment",
                        "action_quality",
                        "constraint",
                        "failure_context",
                    ],
                    "dataset":               args.dataset,
                },
                tags=["grpo", "blackstart-city", "rl-training"],
            )
            console.print(
                f"[bold #00FF66]✓ W&B run initialised:[/] "
                f"[white]{wandb.run.url}[/]\n"
            )
        except Exception as e:
            console.print(f"[bold #FF6B6B]⚠ W&B init failed:[/] {e}  (continuing without tracking)\n")
            args.report_to = "none"

    # ── Model ─────────────────────────────────────────────────────────────────
    console.print("[bold #00FFCC]⚡ Loading model & tokenizer…[/]")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=base_model_name,
        max_seq_length=4096,
        load_in_4bit=True,
        fast_inference=False,
        max_lora_rank=16,
        gpu_memory_utilization=0.6,
    )

    # PEFT 0.14.0 bug workaround
    model.warnings_issued = {}

    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        lora_alpha=16,
        use_gradient_checkpointing="unsloth",
        random_state=3407,
    )

    if adapter_path:
        model.load_adapter(
            adapter_path,
            adapter_name="sft_init",
            is_trainable=True,
            autocast_adapter_dtype=False,
        )
        model.set_adapter("sft_init")
        for name, param in model.named_parameters():
            if "lora_" in name and param.dtype != torch.float16:
                param.data = param.data.to(torch.float16)

    # ── Dataset ───────────────────────────────────────────────────────────────
    dataset = load_dataset("json", data_files=args.dataset, split="train")

    def format_for_grpo(example):
        return {"prompt": [
            {"role": "system", "content": (
                "You are a city blackout restoration policy. "
                "Return exactly one valid JSON action object and nothing else."
            )},
            {"role": "user", "content": "Observation:\n" + example["prompt"]},
        ]}
    dataset = dataset.map(format_for_grpo, remove_columns=dataset.column_names)

    # ── Trainer ───────────────────────────────────────────────────────────────
    training_args = GRPOConfig(
        output_dir=args.output_dir,
        learning_rate=5e-6,
        lr_scheduler_type="cosine",
        logging_steps=5,
        max_steps=args.max_steps,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=2,
        num_generations=8,
        generation_batch_size=8,
        max_prompt_length=3500,
        max_completion_length=150,
        temperature=0.9,
        bf16=is_bfloat16_supported(),
        fp16=not is_bfloat16_supported(),
        optim="adamw_8bit",
        report_to=args.report_to,
    )

    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        reward_funcs=[
            env_step_reward_func,
            format_reward_func,
            alignment_reward_func,
            action_quality_reward_func,
            constraint_reward_func,
            failure_context_reward_func,
        ],
        reward_weights=REWARD_WEIGHTS,
        args=training_args,
        train_dataset=dataset,
        callbacks=[
            RichGRPOCallback(log_every=5),
            EnvEvalCallback(eval_every=50, n_tasks=2),
        ],
    )

    console.print(Panel(
        "[bold #00FFCC]🚀  Training started![/]  "
        "Env-step reward active · W&B tracking live · Watch the reward table every 5 steps.",
        border_style="#00FFCC", padding=(0, 2)
    ))
    trainer.train()

    console.print(Panel(
        "[bold #00FF66]✅  Training complete!  Saving model…[/]",
        border_style="#00FF66", padding=(0, 2)
    ))
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    # ── Dashboard ─────────────────────────────────────────────────────────────
    plt.style.use("dark_background")
    fig, axes = plt.subplots(2, 3, figsize=(20, 10), facecolor="#121212")
    fig.suptitle(
        "BLACKSTART CITY: GRPO TRAINING DASHBOARD",
        fontsize=22, fontweight="bold", color="#00FFCC", y=1.02,
    )

    reward_keys_substrings = BASE_REWARD_KEYS
    titles = [
        "ENV STEP (GROUND TRUTH)",
        "FORMAT INTEGRITY",
        "AGENT ALIGNMENT",
        "TACTICAL QUALITY",
        "CONSTRAINT COMPLIANCE",
        "FAILURE AVOIDANCE",
    ]
    colors = ["#FFFFFF", "#FF00FF", "#00CCFF", "#00FF66", "#FFD700", "#FF6B6B"]
    axes_flat = axes.flatten()

    for ax, sub, title, color in zip(axes_flat, reward_keys_substrings, titles, colors):
        actual_key = None
        for log in trainer.state.log_history:
            for k in log.keys():
                if sub in k:
                    actual_key = k
                    break
            if actual_key:
                break

        if actual_key:
            raw_values = [l[actual_key] for l in trainer.state.log_history if actual_key in l]
            window = max(1, len(raw_values) // 10)
            smooth_values = np.convolve(raw_values, np.ones(window) / window, mode="valid")
            ax.plot(raw_values, color=color, alpha=0.2, linewidth=1)
            ax.plot(
                range(window - 1, len(raw_values)), smooth_values,
                color=color, linewidth=3, label="Trend",
            )
            ax.fill_between(range(window - 1, len(raw_values)), smooth_values, alpha=0.08, color=color)
        else:
            ax.text(
                0.5, 0.5, "No data logged",
                transform=ax.transAxes, ha="center", va="center",
                color="#888888", fontsize=12,
            )

        ax.set_title(title, fontsize=13, fontweight="bold", color=color, pad=12)
        ax.set_facecolor("#1e1e1e")
        ax.grid(True, linestyle="--", alpha=0.15)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_xlabel("Training Step", alpha=0.7)
        ax.set_ylabel("Reward Value", alpha=0.7)

    plt.tight_layout()
    dashboard_path = f"{args.output_dir}/reward_curves.png"
    plt.savefig(dashboard_path, dpi=150, bbox_inches="tight", facecolor="#121212")
    console.print(f"[dim]Dashboard saved → {dashboard_path}[/dim]")

    # Upload dashboard image to W&B
    try:
        import wandb
        if wandb.run is not None:
            wandb.log({"charts/reward_dashboard": wandb.Image(dashboard_path)})
            wandb.finish()
    except Exception:
        pass

    print("Done.")


if __name__ == "__main__":
    main()
