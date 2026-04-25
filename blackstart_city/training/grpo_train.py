import argparse
import json
import os
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import torch
from datasets import load_dataset

# Standard HF + PEFT — no Unsloth import so Unsloth cannot auto-patch GRPOTrainer.
# Unsloth's fast_lora kernels crash with CUBLAS_STATUS_EXECUTION_FAILED on
# CUDA 13.0 + T4 (cublasGemmEx fp16 failure in apply_lora_mlp_swiglu). Using
# plain transformers + PEFT avoids all fast-kernel paths entirely.
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import get_peft_model, LoraConfig, TaskType

from trl import GRPOConfig, GRPOTrainer
from transformers import TrainerCallback, TrainerControl, TrainerState, TrainingArguments
from blackstart_city.training.model_utils import parse_action_text


def is_bfloat16_supported() -> bool:
    return torch.cuda.is_available() and torch.cuda.is_bf16_supported()
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

console = Console()

BASE_REWARD_KEYS = [
    "format_reward_func",
    "alignment_reward_func",
    "action_quality_reward_func",
    "constraint_reward_func",
    "failure_context_reward_func",
]
REWARD_LABELS = [
    ("Format",      "#FF00FF"),
    ("Alignment",   "#00CCFF"),
    ("Tact. Quality","#00FF66"),
    ("Constraint",  "#FFD700"),
    ("Fail. Avoid", "#FF6B6B"),
]


def _print_banner(model_name: str, max_steps: int, output_dir: str) -> None:
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
    cfg.add_row("Model",      model_name)
    cfg.add_row("Max Steps",  str(max_steps))
    cfg.add_row("Output Dir", output_dir)
    cfg.add_row("Rewards",    "5 signals  ·  equal weights [0.2 each]")
    console.print(Panel(cfg, title="[bold #00FFCC]Config[/]", border_style="#333333"))


def _resolve_base_and_adapter(
    model_name: str, adapter_path: str | None
) -> tuple[str, str | None]:
    """Resolve base-model + optional LoRA adapter path.

    Supports two modes:
    1) Explicit: --model-name <base-model> --adapter-path <adapter-dir>
    2) Implicit: --model-name <adapter-dir> (auto-detect via adapter_config.json)
    """
    if adapter_path:
        return model_name, adapter_path

    maybe_dir = Path(model_name)
    adapter_cfg = maybe_dir / "adapter_config.json"
    full_cfg = maybe_dir / "config.json"

    # If this looks like an adapter-only directory, derive base model from adapter config.
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
        loss  = logs.get("loss", logs.get("train_loss", None))
        lr    = logs.get("learning_rate", None)

        # ── header row ──────────────────────────────────────────────────────
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
            # TRL logs rewards as  `rewards/<func_name>`
            val = None
            for k, v in logs.items():
                if base_key in k:
                    val = v
                    break
            if val is None:
                continue
            bar_len = int(min(max((val + 1) / 2, 0), 1) * 20)   # map [-1,1] → [0,20]
            bar = f"[{color}]{'█' * bar_len}{'░' * (20 - bar_len)}[/{color}]"
            val_str = f"[{color}]{val:+.4f}[/{color}]"
            tbl.add_row(f"[{color}]{label}[/{color}]", val_str, bar)

        # ── footer: loss + lr ────────────────────────────────────────────────
        extras = []
        if loss is not None:
            extras.append(f"loss [bold white]{loss:.4f}[/]")
        if lr is not None:
            extras.append(f"lr [bold white]{lr:.2e}[/]")
        footer = "  ·  ".join(extras) if extras else ""

        console.print(tbl)
        if footer:
            console.print(f"  [dim]{footer}[/dim]\n")


def format_reward_func(completions, **kwargs) -> list[float]:
    """Gate reward — valid JSON action = 1.0, with partial credit for structure."""
    rewards = []
    for comp in completions:
        try:
            text = comp[0]["content"] if isinstance(comp, list) else comp
            # Partial credit for just trying to use JSON
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
    """
    Rewards alignment with command center agent recommendations.
    Provides partial credit based on raw text search if JSON parsing fails.
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
                # Partial credit: Did the model at least MENTION a critical node or generator?
                partial = 0.0
                critical_ids = [n["id"] for n in obs.get("critical_nodes", [])]
                gen_ids = [g["id"] for g in obs.get("generators", [])]
                for cid in critical_ids:
                    if cid in comp_text: partial += 0.05
                for gid in gen_ids:
                    if gid in comp_text: partial += 0.05
                rewards.append(min(partial, 0.2) - 0.2) # Still a penalty, but variable
                continue

            reward = 0.0
            recs = obs.get("command_center", {}).get("role_recommendations", [])

            if recs:
                # Primary path: match against explicit recommendations
                for rec in recs:
                    rec_action = rec.get("proposed_action")
                    if rec_action and rec_action.get("action_type") == action.action_type.value:
                        if rec_action.get("target_id") == action.target_id:
                            reward = 1.0
                            break
            else:
                # Fallback: derive alignment signal from observable state
                critical_nodes = obs.get("critical_nodes", [])
                generators = obs.get("generators", [])
                unpowered_critical_ids = {
                    n["id"] for n in critical_nodes if not n.get("powered")
                }
                online_generators = [g for g in generators if g.get("online")]
                blackstart_capable_offline = [
                    g for g in generators
                    if g.get("blackstart_capable") and not g.get("online")
                ]

                # Restoring an unpowered critical node is always aligned
                if action.target_id in unpowered_critical_ids:
                    reward = 1.0
                # Starting the first blackstart generator is the correct first move
                elif (
                    not online_generators
                    and action.action_type.value == "start_generator"
                    and blackstart_capable_offline
                    and action.target_id == blackstart_capable_offline[0]["id"]
                ):
                    reward = 0.8
                # Any start_generator when nothing is online is reasonable
                elif not online_generators and action.action_type.value == "start_generator":
                    reward = 0.4

            rewards.append(reward)
        except Exception:
            rewards.append(0.0)
    return rewards


def action_quality_reward_func(prompts, completions, **kwargs) -> list[float]:
    """Graded reward from observation state — no env.step(), no temporal mismatch."""
    rewards = []
    for prompt, comp in zip(prompts, completions):
        try:
            prompt_text = prompt[-1]["content"] if isinstance(prompt, list) else prompt
            obs_json_str = prompt_text.split("Observation:\n")[-1]
            obs_data = json.loads(obs_json_str)
            comp_text = comp[0]["content"] if isinstance(comp, list) else comp
            action = parse_action_text(comp_text)

            if action is None:
                # Partial credit: Did the model mention key terms?
                partial = len(comp_text) / 1000.0 # Length-based reward variance
                if "generator" in comp_text.lower(): partial += 0.05
                if "restore" in comp_text.lower(): partial += 0.05
                rewards.append(min(partial, 0.2) - 0.5)
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

            # Bug fix: only penalize restore_zone if the target is NOT an unpowered critical node
            if unpowered_critical and action.action_type.value == "restore_zone":
                unpowered_ids = {n.get("id") for n in unpowered_critical}
                if action.target_id not in unpowered_ids:
                    score -= 0.5

            rewards.append(max(-1.0, min(1.0, score)))
        except Exception:
            rewards.append(0.0)
    return rewards


def constraint_reward_func(prompts, completions, **kwargs) -> list[float]:
    """
    Penalizes actions that violate scenario constraints visible in the observation.

    Fallback (when active_constraints is empty — old dataset format or early
    episodes before constraints activate): derives a safety signal from grid
    physics — shedding zones when frequency is low is compliant (+0.3), trying
    to restore zones when reserves are critically low is risky (-0.4). This
    guarantees the function returns varied scores across completions.
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
                # Partial credit for length variance
                partial = len(comp_text) / 2000.0
                if "caution" in comp_text.lower(): partial += 0.1
                rewards.append(min(partial, 0.2) - 0.5)
                continue

            score = 0.5  # base: assume compliant

            constraints = obs_data.get("active_constraints", [])
            if constraints:
                # ── Primary path: evaluate explicit constraints ─────────────
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
                # ── Fallback: physics-based safety scoring ─────────────────
                # (produces variance when no explicit constraints are present)
                freq = obs_data.get("frequency_hz", 60.0)
                reserve = obs_data.get("reserve_margin_mw", 0)

                if freq < 59.5:
                    # Low frequency → shedding is safe, restoring is risky
                    if action.action_type.value == "shed_zone":
                        score += 0.3
                    elif action.action_type.value in ("restore_zone", "restore_critical_node",
                                                      "energize_substation"):
                        score -= 0.3

                if reserve < 5 and action.action_type.value == "restore_zone":
                    # Critically low reserve — don't add more load
                    score -= 0.4

                if reserve > 20 and action.action_type.value == "shed_zone":
                    # Plenty of headroom — no need to shed
                    score -= 0.2

            # ── News-feed bonus (applies in both paths) ───────────────────────
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
    ToM Reward: Rewards the model for NOT repeating actions that failed in
    previous tiers (visible in the failure_context).

    Fallback (when failure_context is empty): scores based on whether the model
    avoids acting on damaged/tripped lines or already-online generators — these
    are the natural "would fail" actions detectable from observation state alone.
    This prevents the function from returning a constant 0.0 for every step.
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
                # Partial credit: Did the model mention a previous failure?
                partial = 0.0
                if "failed" in comp_text.lower(): partial += 0.1
                rewards.append(partial - 0.2)
                continue

            failure_ctx = obs_data.get("failure_context", [])

            if failure_ctx:
                # ── Primary path: check against recorded failed actions ──────
                was_failure = False
                for fail in failure_ctx:
                    for failed_action in fail.get("failed_actions", []):
                        if (failed_action.get("action_type") == action.action_type.value
                                and failed_action.get("target_id") == action.target_id):
                            was_failure = True
                            break
                # Positive reward for pivoting, negative for repeating failures
                rewards.append(-1.0 if was_failure else 0.5)
            else:
                # ── Fallback: penalise predictably-futile actions ────────────
                # Acting on a damaged or tripped line is a known-failure action.
                lines = obs_data.get("lines", [])
                generators = obs_data.get("generators", [])

                damaged_line_ids = {l["id"] for l in lines if l.get("damaged") or l.get("tripped")}
                online_gen_ids = {g["id"] for g in generators if g.get("online")}

                if (
                    action.action_type.value in ("close_line", "inspect_line")
                    and action.target_id in damaged_line_ids
                ):
                    # Trying to close an already-damaged line — bad pivot
                    rewards.append(-0.6)
                elif (
                    action.action_type.value == "start_generator"
                    and action.target_id in online_gen_ids
                ):
                    # Starting an already-online generator — wasteful/futile
                    rewards.append(-0.4)
                else:
                    # No detectable futile action — neutral positive
                    rewards.append(0.3)
        except Exception:
            rewards.append(0.0)
    return rewards


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", default="Qwen/Qwen2.5-3B-Instruct")
    parser.add_argument(
        "--adapter-path",
        default=None,
        help="Optional LoRA adapter path to continue training from SFT output.",
    )
    parser.add_argument("--output-dir", default="artifacts/blackstart-city-grpo")
    parser.add_argument("--dataset", default="dataset.jsonl", help="Path to training dataset")
    parser.add_argument("--max-steps", type=int, default=500)
    args = parser.parse_args()

    base_model_name, adapter_path = _resolve_base_and_adapter(args.model_name, args.adapter_path)
    os.makedirs(args.output_dir, exist_ok=True)
    _print_banner(base_model_name, args.max_steps, args.output_dir)
    if adapter_path:
        console.print(
            f"[bold #FFD700]↪ Continuing from adapter:[/] [white]{adapter_path}[/]"
        )

    console.print("[bold #00FFCC]⚡ Loading model & tokenizer…[/]")
    _dtype = torch.float16  # T4 is fp16-only (no bf16)
    model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        torch_dtype=_dtype,
        device_map="auto",
    )
    tokenizer = AutoTokenizer.from_pretrained(base_model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    lora_cfg = LoraConfig(
        r=16,
        lora_alpha=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.0,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    model = get_peft_model(model, lora_cfg)
    model.print_trainable_parameters()
    # PEFT initialises LoRA A/B in float32 by default. Cast to fp16 so every
    # matmul in the forward pass stays fp16 (base weights are fp16).
    for _n, _p in model.named_parameters():
        if _p.requires_grad and _p.dtype != _dtype:
            _p.data = _p.data.to(_dtype)

    if adapter_path:
        from peft import set_peft_model_state_dict
        from safetensors.torch import load_file as _load_safetensors
        _sft_path = Path(adapter_path) / "adapter_model.safetensors"
        if _sft_path.exists():
            _sft_weights = {
                k: v.to(_dtype)
                for k, v in _load_safetensors(str(_sft_path)).items()
            }
            set_peft_model_state_dict(model, _sft_weights)
            console.print(
                f"[green]Loaded {len(_sft_weights)} SFT weights → {_dtype}[/]"
            )
        else:
            console.print(f"[yellow]No adapter_model.safetensors at {_sft_path}, using random LoRA[/]")

    dataset = load_dataset("json", data_files=args.dataset, split="train")

    def format_for_grpo(example):
        return {"prompt": [
            {"role": "system", "content": "You are a city blackout restoration policy. "
                                          "Return exactly one valid JSON action object and nothing else."},
            {"role": "user", "content": "Observation:\n" + example["prompt"]}
        ]}
    dataset = dataset.map(format_for_grpo, remove_columns=dataset.column_names)

    training_args = GRPOConfig(
        output_dir=args.output_dir,
        learning_rate=5e-6,
        lr_scheduler_type="cosine",
        logging_steps=5,
        max_steps=args.max_steps,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=2,
        num_generations=8,
        max_prompt_length=3500,
        max_completion_length=150,
        temperature=0.9,
        bf16=is_bfloat16_supported(),
        fp16=not is_bfloat16_supported(),
        optim="adamw_torch",
        report_to="none",
    )

    _reward_fns = [
        format_reward_func,
        alignment_reward_func,
        action_quality_reward_func,
        constraint_reward_func,
        failure_context_reward_func,
    ]
    _reward_w = [0.2, 0.2, 0.2, 0.2, 0.2]

    def combined_reward_func(prompts, completions, **kwargs):
        """Weighted sum of all 5 reward signals. Used as fallback when
        reward_weights is not supported by the installed TRL version."""
        total = [0.0] * len(completions)
        for fn, w in zip(_reward_fns, _reward_w):
            try:
                scores = fn(prompts=prompts, completions=completions, **kwargs)
            except TypeError:
                scores = fn(completions=completions, **kwargs)
            for i, s in enumerate(scores):
                total[i] += w * float(s)
        return total

    try:
        trainer = GRPOTrainer(
            model=model,
            processing_class=tokenizer,
            reward_funcs=_reward_fns,
            reward_weights=_reward_w,
            args=training_args,
            train_dataset=dataset,
            callbacks=[RichGRPOCallback(log_every=5)],
        )
    except TypeError:
        # Older TRL/Unsloth versions don't support reward_weights parameter.
        # Fall back to a single combined reward function with weights baked in.
        trainer = GRPOTrainer(
            model=model,
            processing_class=tokenizer,
            reward_funcs=[combined_reward_func],
            args=training_args,
            train_dataset=dataset,
            callbacks=[RichGRPOCallback(log_every=5)],
        )

    console.print(Panel(
        "[bold #00FFCC]🚀  Training started![/]  Watch the reward table update every 5 steps.",
        border_style="#00FFCC", padding=(0, 2)
    ))
    trainer.train()
    console.print(Panel(
        "[bold #00FF66]✅  Training complete!  Saving model…[/]",
        border_style="#00FF66", padding=(0, 2)
    ))
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    # --- PREMIUM DASHBOARD — all 5 reward signals ---
    plt.style.use('dark_background')
    fig, axes = plt.subplots(2, 3, figsize=(20, 10), facecolor='#121212')
    fig.suptitle('BLACKSTART CITY: GRPO TRAINING DASHBOARD', fontsize=22,
                 fontweight='bold', color='#00FFCC', y=1.02)

    reward_keys_substrings = [
        "format_reward_func",
        "alignment_reward_func",
        "action_quality_reward_func",
        "constraint_reward_func",
        "failure_context_reward_func",
    ]
    titles = [
        "FORMAT INTEGRITY",
        "AGENT ALIGNMENT",
        "TACTICAL QUALITY",
        "CONSTRAINT COMPLIANCE",
        "FAILURE AVOIDANCE",
    ]
    colors = ['#FF00FF', '#00CCFF', '#00FF66', '#FFD700', '#FF6B6B']

    # Flatten axes and hide the unused 6th subplot
    axes_flat = axes.flatten()
    axes_flat[5].set_visible(False)

    # Detect whether training used individual reward funcs or combined fallback
    _used_combined = not any(
        any(sub in k for k in trainer.state.log_history[0].keys() if trainer.state.log_history)
        for sub in reward_keys_substrings
    ) if trainer.state.log_history else False

    for ax, sub, title, color in zip(axes_flat[:5], reward_keys_substrings, titles, colors):
        actual_key = None
        search_key = "combined_reward_func" if _used_combined else sub
        for log in trainer.state.log_history:
            for k in log.keys():
                if search_key in k:
                    actual_key = k
                    break
            if actual_key:
                break

        if actual_key:
            raw_values = [l[actual_key] for l in trainer.state.log_history if actual_key in l]
            window = max(1, len(raw_values) // 10)
            smooth_values = np.convolve(raw_values, np.ones(window) / window, mode='valid')

            ax.plot(raw_values, color=color, alpha=0.2, linewidth=1)
            ax.plot(range(window - 1, len(raw_values)), smooth_values,
                    color=color, linewidth=3, label='Trend')
            ax.fill_between(range(window - 1, len(raw_values)), smooth_values,
                            alpha=0.08, color=color)
        else:
            ax.text(0.5, 0.5, 'No data logged', transform=ax.transAxes,
                    ha='center', va='center', color='#888888', fontsize=12)

        ax.set_title(title, fontsize=13, fontweight='bold', color=color, pad=12)
        ax.set_facecolor('#1e1e1e')
        ax.grid(True, linestyle='--', alpha=0.15)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_xlabel("Training Step", alpha=0.7)
        ax.set_ylabel("Reward Value", alpha=0.7)

    plt.tight_layout()
    plt.savefig(f"{args.output_dir}/reward_curves.png", dpi=150,
                bbox_inches='tight', facecolor='#121212')
    print(f"Premium Dashboard saved to {args.output_dir}/reward_curves.png")
    print("Done.")


if __name__ == "__main__":
    main()