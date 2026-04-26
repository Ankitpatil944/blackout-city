from __future__ import annotations

import argparse
import json
from pathlib import Path

from blackstart_city.env import BlackstartCityEnv
from blackstart_city.tasks.catalog import TASK_ORDER
from blackstart_city.training.model_utils import build_policy_prompt, invalid_action_penalty, parse_action_text


def sequence_logprob_and_entropy(model, input_ids, attention_mask, generated_ids, torch_module):
    """Return (total_log_prob, mean_entropy) for the generated tokens."""
    full_ids = torch_module.cat([input_ids, generated_ids], dim=1)
    full_mask = torch_module.ones_like(full_ids)
    outputs = model(input_ids=full_ids, attention_mask=full_mask)
    logits = outputs.logits[:, :-1, :]
    targets = full_ids[:, 1:]
    prompt_len = input_ids.shape[1]
    gen_token_count = generated_ids.shape[1]
    if gen_token_count == 0:
        zero = torch_module.zeros((), device=full_ids.device)
        return zero, zero
    start_idx = prompt_len - 1
    end_idx = start_idx + gen_token_count
    selected_logits = logits[:, start_idx:end_idx, :]
    selected_targets = targets[:, start_idx:end_idx]
    log_probs = torch_module.log_softmax(selected_logits, dim=-1)
    token_log_probs = log_probs.gather(-1, selected_targets.unsqueeze(-1)).squeeze(-1)
    # Entropy: -sum(p * log_p) averaged over generated tokens.
    probs = torch_module.softmax(selected_logits, dim=-1)
    entropy = -(probs * log_probs).sum(dim=-1).mean()
    return token_log_probs.sum(), entropy


def rollout_episode(env: BlackstartCityEnv, model, tokenizer, task_id: str, seed: int, max_new_tokens: int, torch_module) -> tuple[list, list, list[float], dict]:
    """Returns (logprobs, entropies, rewards, info)."""
    observation = env.reset(task_id=task_id, seed=seed)
    seen_signatures: set[str] = set()
    logprobs: list = []
    entropies: list = []
    rewards: list[float] = []
    info = {"score": observation.reward_breakdown.current_score, "resolved": False, "catastrophe_triggered": False}

    while not observation.done:
        prompt = build_policy_prompt(observation)
        inputs = tokenizer(prompt, return_tensors="pt")
        inputs = {key: value.to(model.device) for key, value in inputs.items()}

        outputs = model.generate(
            **inputs,
            do_sample=True,
            temperature=0.8,
            top_p=0.95,
            max_new_tokens=max_new_tokens,
            pad_token_id=tokenizer.eos_token_id,
        )
        generated_ids = outputs[:, inputs["input_ids"].shape[1] :]
        text = tokenizer.decode(generated_ids[0], skip_special_tokens=True)
        action = parse_action_text(text)

        lp, ent = sequence_logprob_and_entropy(model, inputs["input_ids"], inputs["attention_mask"], generated_ids, torch_module)

        if action is None:
            _, penalty, terminate, reason = invalid_action_penalty(observation)
            rewards.append(penalty)
            logprobs.append(lp)
            entropies.append(ent)
            info = {
                "score": max(0.01, observation.reward_breakdown.current_score + penalty),
                "resolved": False,
                "catastrophe_triggered": terminate,
                "reason": reason,
            }
            if terminate:
                break
            continue

        signature = f"{action.action_type.value}|{action.target_id or ''}|{action.requested_mw or 0}"
        if signature in seen_signatures:
            _, penalty, _, reason = invalid_action_penalty(observation)
            rewards.append(penalty)
            logprobs.append(lp)
            entropies.append(ent)
            info = {
                "score": max(0.01, observation.reward_breakdown.current_score + penalty),
                "resolved": False,
                "catastrophe_triggered": False,
                "reason": f"{reason} Repeated action signature.",
            }
            continue

        seen_signatures.add(signature)
        observation, reward, done, info = env.step(action)
        logprobs.append(lp)
        entropies.append(ent)
        rewards.append(reward)
        if done:
            break

    return logprobs, entropies, rewards, info


def discounted_returns(rewards: list[float], gamma: float, torch_module):
    returns = []
    running = 0.0
    for reward in reversed(rewards):
        running = reward + gamma * running
        returns.append(running)
    returns.reverse()
    return torch_module.tensor(returns, dtype=torch_module.float32)


def main() -> None:
    parser = argparse.ArgumentParser(description="True reward-driven RL training loop for Blackstart City.")
    parser.add_argument("--model-name", default="Qwen/Qwen2.5-3B-Instruct")
    parser.add_argument("--output-dir", default="artifacts/blackstart-city-rl")
    parser.add_argument("--task-id", default="local_blackstart", choices=TASK_ORDER)
    parser.add_argument("--train-steps", type=int, default=30)
    parser.add_argument("--episodes-per-update", type=int, default=2)
    parser.add_argument("--gamma", type=float, default=0.98)
    parser.add_argument("--learning-rate", type=float, default=1e-5)
    parser.add_argument("--max-new-tokens", type=int, default=96)
    parser.add_argument("--save-every", type=int, default=10)
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--entropy-coeff", type=float, default=0.01)
    parser.add_argument("--max-grad-norm", type=float, default=1.0)
    parser.add_argument("--baseline-ema", type=float, default=0.9)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        print(
            json.dumps(
                {
                    "mode": "reward-driven-rl",
                    "model_name": args.model_name,
                    "task_id": args.task_id,
                    "train_steps": args.train_steps,
                    "episodes_per_update": args.episodes_per_update,
                },
                indent=2,
            )
        )
        return

    import torch
    from peft import LoraConfig, get_peft_model
    from torch.optim import AdamW
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    tokenizer.pad_token = tokenizer.eos_token
    base_model = AutoModelForCausalLM.from_pretrained(args.model_name, device_map="auto")
    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(base_model, peft_config)
    model.train()

    optimizer = AdamW(model.parameters(), lr=args.learning_rate)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    progress_path = output_dir / "rl_metrics.jsonl"

    global_seed = args.seed_start
    ema_baseline = 0.0  # exponential moving average baseline for variance reduction

    for step in range(1, args.train_steps + 1):
        optimizer.zero_grad()
        env = BlackstartCityEnv()
        batch_losses = []
        batch_entropy_bonuses = []
        batch_scores = []
        batch_returns = []

        for _ in range(args.episodes_per_update):
            logprobs, entropies, rewards, info = rollout_episode(
                env,
                model,
                tokenizer,
                task_id=args.task_id,
                seed=global_seed,
                max_new_tokens=args.max_new_tokens,
                torch_module=torch,
            )
            global_seed += 1
            if not logprobs:
                continue
            returns = discounted_returns(rewards, args.gamma, torch).to(model.device)

            # Subtract EMA baseline before per-episode normalization for lower variance.
            ema_baseline = args.baseline_ema * ema_baseline + (1 - args.baseline_ema) * returns.mean().item()
            advantages = returns - ema_baseline
            if advantages.numel() > 1:
                advantages = (advantages - advantages.mean()) / (advantages.std(unbiased=False) + 1e-6)

            # REINFORCE loss with advantage baseline.
            policy_loss = torch.stack([-lp * adv for lp, adv in zip(logprobs, advantages)]).mean()
            # Entropy bonus to prevent premature policy collapse.
            mean_entropy = torch.stack(entropies).mean() if entropies else torch.zeros((), device=model.device)
            entropy_bonus = -args.entropy_coeff * mean_entropy

            batch_losses.append(policy_loss + entropy_bonus)
            batch_entropy_bonuses.append(float(mean_entropy.detach().cpu().item()))
            batch_scores.append(float(info["score"]))
            batch_returns.append(float(sum(rewards)))

        if not batch_losses:
            continue

        loss = torch.stack(batch_losses).mean()
        loss.backward()
        # Gradient clipping to prevent weight explosion from noisy RL gradients.
        torch.nn.utils.clip_grad_norm_(model.parameters(), args.max_grad_norm)
        optimizer.step()

        metrics = {
            "step": step,
            "loss": round(float(loss.detach().cpu().item()), 4),
            "mean_episode_return": round(sum(batch_returns) / len(batch_returns), 4),
            "mean_score": round(sum(batch_scores) / len(batch_scores), 4),
            "mean_entropy": round(sum(batch_entropy_bonuses) / max(1, len(batch_entropy_bonuses)), 4),
            "ema_baseline": round(ema_baseline, 4),
            "episodes_per_update": args.episodes_per_update,
            "task_id": args.task_id,
        }
        print(json.dumps(metrics))
        with progress_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(metrics) + "\n")

        if step % args.save_every == 0 or step == args.train_steps:
            checkpoint_dir = output_dir / f"step-{step}"
            checkpoint_dir.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(checkpoint_dir)
            tokenizer.save_pretrained(checkpoint_dir)

    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"Saved reward-trained policy to {output_dir}")


if __name__ == "__main__":
    main()
