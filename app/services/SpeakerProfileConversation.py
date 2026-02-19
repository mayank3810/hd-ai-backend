"""
Conversation AI: generates user-facing assistant messages.

This module MUST NOT perform validation decisions. It only turns:
- (step, normalized_answer, next_step) into a transition message
- (step, user_answer, reason_code, retry_count) into a recovery message
"""

from __future__ import annotations

import os
import hashlib
from typing import Any, Dict, List, Optional, Union

from openai import OpenAI

from app.config.speaker_profile_steps import StepDefinition, get_step_by_name


def _allowed_display(allowed: Optional[List[Any]]) -> List[str]:
    """Convert allowed_values to list of display strings (for recovery messages). Handles list of str or list of topic objects."""
    if not allowed:
        return []
    return [
        (x.get("name") or x.get("slug") or "") if isinstance(x, dict) else str(x)
        for x in allowed
    ]


def _stable_seed(*parts: str) -> int:
    h = hashlib.sha256("||".join(parts).encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def _fallback_transition(
    step_name: str,
    normalized_answer: Any,
    next_step: Optional[Dict[str, Any]],
    is_last_step: bool = False,
) -> str:
    if is_last_step:
        return "You've completed your speaker profile—thanks for sharing!"
    if step_name == "full_name":
        name = str(normalized_answer or "").strip()
        first = name.split()[0] if name else ""
        return f"Nice to meet you{', ' + first if first else ''}! {next_step.get('question') if next_step else 'What topics do you speak about?'}"
    if next_step and next_step.get("question"):
        return f"Got it. {next_step['question']}"
    return "Got it. What's next?"


def _fallback_recovery(
    step: StepDefinition,
    reason_code: str,
    retry_count: int,
    allowed_values: Optional[List[Any]] = None,
) -> str:
    q = step.question
    raw_allowed = allowed_values if allowed_values is not None else (step.allowed_values or [])
    allowed = _allowed_display(raw_allowed) if raw_allowed and isinstance(raw_allowed[0], dict) else (raw_allowed if isinstance(raw_allowed, list) else [])

    variants = []
    if reason_code in ("EMPTY", "REQUIRED"):
        variants = [
            f"I didn't catch an answer—{q}",
            f"Could you share that with me? {q}",
            f"Just to make sure I understand—{q}",
        ]
    elif reason_code == "MISSING_PROFILE_ID":
        variants = [
            "Let's start from the beginning—what is your full name?",
            "I don't have your profile yet. Could you tell me your full name first?",
        ]
    elif reason_code == "INVALID_FULL_NAME":
        variants = [
            "That doesn't quite look like a full name. Could you share your real full name (first and last)?",
            "Please enter your full name, e.g. first and last name.",
        ]
    elif reason_code == "INVALID_EMAIL":
        variants = [
            "That doesn't look like a valid email address. Could you double-check and try again?",
            "Please enter a valid email address (e.g. name@example.com).",
        ]
    elif reason_code in ("INVALID_URL",):
        variants = [
            "That link doesn't look quite right. Could you paste the full URL (including https://)?",
            "Could you share a valid URL? It should start with https://",
            "I’m having trouble with that link—can you paste the full URL?",
        ]
    elif reason_code in ("ENUM_NO_MATCH", "ENUM_INVALID"):
        if allowed:
            display_str = ", ".join(str(a) for a in allowed)
            variants = [
                f"I didn’t quite catch that—could you choose from: {display_str}?",
                f"Which option fits best? Pick from: {display_str}.",
                f"To keep things consistent, please choose from: {display_str}.",
            ]
        else:
            variants = [
                "I didn’t quite catch that—could you try again?",
                "Could you rephrase that for me?",
                "Can you share that again in a bit more detail?",
            ]
    else:
        # IRRELEVANT / GIBBERISH / SPAM / LOW_EFFORT / UNKNOWN
        variants = [
            f"I’m not totally sure I understood—could you answer this more directly? {q}",
            f"Could you share a bit more detail so I can capture it accurately? {q}",
            f"Help me understand—what would you say for this? {q}",
        ]

    idx = (retry_count or 0) % max(len(variants), 1)
    msg = variants[idx]

    # Escalate help after repeated failures: examples; for enum optionally list allowed_values
    if (retry_count or 0) > 1 and allowed:
        if reason_code in ("ENUM_NO_MATCH", "ENUM_INVALID"):
            msg = f"{msg} Allowed options: {', '.join(str(a) for a in allowed)}."
        else:
            msg = f"{msg} For example: {allowed[0]}."
    return msg


def generate_welcome_message(first_step_question: str) -> str:
    """
    Generate an AI welcome message for the first step (init).
    Returns HTML-formatted message with line breaks for better spacing.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return f"Welcome to Human Driven AI.<br>I will help you to create an account and find matching speaking opportunities<br>{first_step_question}"
    
    client = OpenAI(api_key=api_key)
    prompt = {
        "first_step_question": first_step_question,
        "requirements": [
            "Write a short, warm welcome message (3 lines maximum).",
            "Line 1: Welcome to Human Driven AI.",
            "Line 2: Explain that you will help them create an account and find matching speaking opportunities.",
            "Line 3: Ask for their name (use the first_step_question naturally).",
            "Format: Use <br> tags for line breaks. Keep each line concise (one short sentence per line).",
            "Vary the wording slightly each time while keeping the same structure.",
        ],
    }
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful conversational assistant for Human Driven AI. Return ONLY the HTML-formatted message with <br> tags for line breaks. No JSON. Keep it short and concise - maximum 3 lines."},
                {"role": "user", "content": str(prompt)},
            ],
            temperature=0.8,  # Higher temperature for more variation
            timeout=10,
        )
        msg = (completion.choices[0].message.content or "").strip()
        # Ensure we have <br> tags, fallback to adding them if AI didn't include them
        if "<br>" not in msg and "\n" in msg:
            msg = msg.replace("\n", "<br>")
        elif "<br>" not in msg:
            # If no line breaks, try to add them after periods (simple heuristic)
            parts = msg.split(". ")
            if len(parts) >= 2:
                msg = ".<br>".join(parts)
        return msg or f"Welcome to Human Driven AI.<br>I will help you to create an account and find matching speaking opportunities<br>{first_step_question}"
    except Exception:
        return f"Welcome to Human Driven AI.<br>I will help you to create an account and find matching speaking opportunities<br>{first_step_question}"


def generate_transition_message(
    step_name: str,
    normalized_answer: Union[str, List[str]],
    next_step: Optional[Dict[str, Any]],
    is_last_step: bool = False,
) -> str:
    """
    Generate a conversational transition message after a VALID step.
    When is_last_step is True, generate a completion message and do not ask another question.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _fallback_transition(step_name, normalized_answer, next_step, is_last_step)

    if is_last_step:
        seed = _stable_seed(step_name, str(normalized_answer), "complete")
        client = OpenAI(api_key=api_key)
        prompt = {
            "step": step_name,
            "normalized_answer": normalized_answer,
            "requirements": [
                "This was the final step. Acknowledge the user's answer briefly.",
                "Congratulate them on completing their speaker profile. Do NOT ask any further questions.",
                "Keep it natural, friendly, and concise (1-2 sentences).",
            ],
            "variation_seed": seed,
        }
        try:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful conversational assistant. Return ONLY the assistant message text. No JSON. Do not ask any question."},
                    {"role": "user", "content": str(prompt)},
                ],
                temperature=0.6,
                timeout=10,
            )
            msg = (completion.choices[0].message.content or "").strip()
            return msg or _fallback_transition(step_name, normalized_answer, next_step, True)
        except Exception:
            return _fallback_transition(step_name, normalized_answer, next_step, True)

    seed = _stable_seed(step_name, str(normalized_answer), str(next_step or {}))
    client = OpenAI(api_key=api_key)
    next_q = (next_step or {}).get("question", "")
    prompt = {
        "step": step_name,
        "normalized_answer": normalized_answer,
        "next_question": next_q,
        "requirements": [
            "Write one short assistant message that acknowledges the user's answer and smoothly asks the next question.",
            "Do not mention validation, rules, or grammar.",
            "Assume good intent.",
            "Keep it natural, friendly, and concise.",
        ],
        "variation_seed": seed,
    }

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful conversational assistant. Return ONLY the assistant message text. No JSON."},
                {"role": "user", "content": str(prompt)},
            ],
            temperature=0.6,
            timeout=10,
        )
        msg = (completion.choices[0].message.content or "").strip()
        return msg or _fallback_transition(step_name, normalized_answer, next_step, is_last_step)
    except Exception:
        return _fallback_transition(step_name, normalized_answer, next_step, is_last_step)


def generate_recovery_message(
    step_name: str,
    user_answer: Union[str, List[str], List[dict]],
    reason_code: str,
    retry_count: int = 0,
    allowed_values: Optional[List[Any]] = None,
) -> str:
    """
    Generate a conversational recovery message after an INVALID step.

    Must:
    - not mention grammar
    - assume good intent
    - vary phrasing
    - escalate help if retry_count > 1
    - avoid repeating exact wording across retries (best-effort; enforced in fallback rotation)
    """
    step = get_step_by_name(step_name)
    if not step:
        return "I didn’t quite catch that—could you try again?"

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _fallback_recovery(step, reason_code, retry_count, allowed_values)

    seed = _stable_seed(step_name, str(user_answer), reason_code, str(retry_count))
    client = OpenAI(api_key=api_key)
    allowed = allowed_values if allowed_values is not None else (step.allowed_values or None)

    is_multiselect = step.form_type == "multiselect" or step.multi_select
    if is_multiselect:
        payload_step = {
            "step_name": step.step_name,
            "question": step.question,
            "allowed_values": allowed if allowed is not None else [],
            "multi_select": step.multi_select,
        }
    else:
        payload_step = {"step_name": step.step_name, "question": step.question}

    payload: Dict[str, Any] = {
        "step": payload_step,
        "user_answer": user_answer,
        "reason_code": reason_code,
        "retry_count": retry_count,
        "requirements": [
            "Write ONE short assistant message asking the user to try again.",
            "Do not mention grammar, spelling, or 'validation'.",
            "Assume the user has good intent. Focus on intent, not length or picking all options.",
            "Vary phrasing compared to prior attempts (retry_count).",
            "If retry_count > 1, escalate help by giving an example or offering the allowed options (if provided).",
            "Do not repeat the exact same wording across retries.",
        ],
        "variation_seed": seed,
    }

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful conversational assistant. Return ONLY the assistant message text. No JSON."},
                {"role": "user", "content": str(payload)},
            ],
            temperature=0.8,
            timeout=10,
        )
        msg = (completion.choices[0].message.content or "").strip()
        return msg or _fallback_recovery(step, reason_code, retry_count, allowed_values)
    except Exception:
        return _fallback_recovery(step, reason_code, retry_count, allowed_values)

