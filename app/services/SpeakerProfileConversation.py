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
        next_q = next_step.get("question") if next_step else "What are some of the topics you want to cover in your speaking opportunities?"
        return f"Great, it's nice to meet you, {first}! {next_q}" if first else f"Great, it's nice to meet you! {next_q}"
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
        if step.step_name == "topics":
            variants = [
                "Topics help us match you to opportunities. Could you pick one or more from the list?",
                "Picking a topic helps your profile—choose one or more from the list when you're ready!",
            ]
        elif step.step_name == "speaking_formats":
            variants = [
                "Speaking formats help event organizers find you. Could you pick one or more from the list?",
                "Picking your formats helps your profile—choose from the list when you're ready!",
            ]
        elif step.step_name == "delivery_mode":
            variants = [
                "How you deliver helps us match you to the right events. Could you pick one or more from the list?",
                "Picking delivery mode helps your profile—choose from the list when you're ready!",
            ]
        elif step.step_name == "talk_description":
            variants = [
                "A short description of your talk helps us match you to the right events. Could you share a bit about your talk or expertise?",
                "Describing your talk helps your profile—share a few sentences when you're ready!",
            ]
        elif step.step_name == "key_takeaways":
            variants = [
                "Key takeaways help event organizers see what audiences get from your talk. Could you share a few?",
                "Sharing key takeaways helps your profile—a few points for your audience when you're ready!",
            ]
        elif step.step_name == "target_audiences":
            variants = [
                "Target audiences help us match you to the right events. Could you pick one or more from the list?",
                "Picking your audience helps your profile—choose one or more from the list when you're ready!",
            ]
        else:
            variants = [
                f"I didn't catch that—could you share? {q}",
                f"Could you share that with me? {q}",
                f"Just to make sure I understand—{q}",
            ]
    elif reason_code == "MISSING_PROFILE_ID":
        variants = [
            "Let's start from the beginning—what is your full name?",
            "I don't have your profile yet. Could you tell me your full name first?",
        ]
    elif reason_code == "REFUSAL":
        # Calm, friendly reply when user declines. For topics, explain why it matters for their profile without demanding.
        if step.step_name == "full_name":
            variants = [
                "No problem. When you're ready, share your full name and we can continue.",
                "That's okay. Whenever you're ready, share your full name to continue.",
            ]
        elif step.step_name == "email":
            variants = [
                "No problem. When you're ready, share your email and we can continue.",
                "That's okay. Whenever you're ready, share your email to continue.",
            ]
        elif step.step_name == "topics":
            variants = [
                "No pressure! Topics help us match you to opportunities. Whenever you're ready, pick one or more from the list.",
                "That's okay! If you don't see yours, pick the closest match—we can refine later. Ready when you are!",
            ]
        elif step.step_name == "speaking_formats":
            variants = [
                "No pressure! Speaking formats help event organizers find you. Whenever you're ready, pick one or more from the list.",
                "That's okay! Pick one or more formats from the list when you're ready—it helps your profile.",
            ]
        elif step.step_name == "delivery_mode":
            variants = [
                "No pressure! How you deliver helps us match you to events. Whenever you're ready, pick one or more from the list.",
                "That's okay! Pick your delivery option(s) from the list when you're ready—it helps your profile.",
            ]
        elif step.step_name == "target_audiences":
            variants = [
                "No pressure! Target audiences help us match you to the right events. Whenever you're ready, pick one or more from the list.",
                "That's okay! Picking your audience helps your profile—choose from the list when you're ready!",
            ]
        elif step.step_name == "linkedin_url":
            variants = [
                "No problem. You can skip this step—we'll move on.",
                "That's okay. We'll continue without it.",
            ]
        elif step.step_name == "past_speaking_examples":
            variants = [
                "No problem. You can skip this step—we'll move on.",
                "That's okay. We'll continue without it.",
            ]
        elif step.step_name == "video_links":
            variants = [
                "No problem. You can skip this step—we'll move on.",
                "That's okay. We'll continue without it.",
            ]
        elif step.step_name == "talk_description":
            variants = [
                "No problem. When you're ready, share a bit about your talk and we can continue.",
                "That's okay. Whenever you're ready, describe your talk or expertise and we'll move on.",
            ]
        elif step.step_name == "key_takeaways":
            variants = [
                "No problem. You can skip this step—we'll move on.",
                "That's okay. We'll continue without it.",
            ]
        else:
            variants = [
                "No problem. When you're ready, we can continue.",
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
        if step.step_name == "linkedin_url":
            variants = [
                "That doesn't look like a LinkedIn profile link. Paste one like https://linkedin.com/in/yourprofile, or you can skip this step.",
                "We need a LinkedIn profile URL (linkedin.com/in/...) or you can skip. Your choice!",
            ]
        else:
            variants = [
                "That link doesn't look quite right. Could you paste the full URL (including https://)?",
                "Could you share a valid URL? It should start with https://",
                "I’m having trouble with that link—can you paste the full URL?",
            ]
    elif reason_code in ("ENUM_NO_MATCH", "ENUM_INVALID"):
        if step.step_name == "topics" and allowed:
            variants = [
                "Topics help us match you to opportunities. Could you pick one or more from the list?",
                "Picking a topic helps your profile—choose one or more from the list when you're ready!",
            ]
        elif step.step_name == "speaking_formats" and allowed:
            variants = [
                "Speaking formats help event organizers find you. Could you pick one or more from the list?",
                "Picking your formats helps your profile—choose from the list when you're ready!",
            ]
        elif step.step_name == "delivery_mode" and allowed:
            variants = [
                "How you deliver helps us match you to the right events. Could you pick one or more from the list?",
                "Picking delivery mode helps your profile—choose from the list when you're ready!",
            ]
        elif step.step_name == "target_audiences" and allowed:
            variants = [
                "Target audiences help us match you to the right events. Could you pick one or more from the list?",
                "Picking your audience helps your profile—choose from the list when you're ready!",
            ]
        elif allowed:
            display_str = ", ".join(str(a) for a in allowed)
            variants = [
                f"I didn't quite catch that—could you choose from: {display_str}?",
                f"Which option fits best? Pick from: {display_str}.",
                f"To keep things consistent, please choose from: {display_str}.",
            ]
        else:
            variants = [
                "I didn't quite catch that—could you try again?",
                "Could you rephrase that for me?",
                "Can you share that again in a bit more detail?",
            ]
    elif reason_code == "GIBBERISH" and step.step_name == "video_links":
        variants = [
            "That doesn't look like a video link. Paste a YouTube or Vimeo URL, or you can skip this step.",
            "We need a speaking video link (YouTube or Vimeo) or you can skip. Your choice!",
        ]
    elif reason_code in ("GIBBERISH", "UNRELATED") and step.step_name in ("talk_description", "key_takeaways"):
        if step.step_name == "talk_description":
            variants = [
                "A short description helps us match you to the right events. Could you share a bit about your talk or expertise?",
                "Describing your talk helps your profile—share a few sentences when you're ready!",
            ]
        else:
            variants = [
                "Key takeaways help organizers see what audiences get. Could you share a few points?",
                "Sharing key takeaways helps your profile—a few points when you're ready!",
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
    Tone matches conversation-sample: warm greeting, value prop, then "Let's begin with the basics. What is your name?"
    """
    fallback_msg = (
        "Hello! Thanks for joining Human Driven AI! My job is to find the right speaking opportunities for you "
        "including drafting the submission materials for each event.<br>Let's begin with the basics. What is your name?"
    )
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return fallback_msg

    client = OpenAI(api_key=api_key)
    prompt = {
        "first_step_question": first_step_question,
        "requirements": [
            "Write a short, warm welcome message (3 lines maximum) in a friendly Speaker Pitcher–style conversation.",
            "Line 1: Warm greeting (e.g. 'Hello! Thanks for joining...') and state your job: find the right speaking opportunities for them and help with drafting submission materials for each event. Use product name 'Human Driven AI'.",
            "Line 2: Optional short reassurance about the process (can be brief or folded into line 1).",
            "Line 3: End with 'Let's begin with the basics. What is your name?' (or very close).",
            "Tone: friendly and conversational like the Speaker Pitcher sample. Use <br> tags for line breaks. No JSON. Keep it concise.",
        ],
    }

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a friendly onboarding agent for Human Driven AI. Match the conversational style of a Speaker Pitcher sample: warm greeting, clear value prop (finding speaking opportunities, drafting submission materials), then ask for their name. Return ONLY the HTML-formatted message with <br> tags for line breaks. No JSON. Maximum 3 lines.",
                },
                {"role": "user", "content": str(prompt)},
            ],
            temperature=0.8,
            timeout=10,
        )
        msg = (completion.choices[0].message.content or "").strip()
        if "<br>" not in msg and "\n" in msg:
            msg = msg.replace("\n", "<br>")
        elif "<br>" not in msg and ". " in msg:
            parts = msg.split(". ")
            if len(parts) >= 2:
                msg = ".<br>".join(parts)
        return msg or fallback_msg
    except Exception:
        return fallback_msg


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
                "Congratulate them warmly on completing their speaker profile; thank them for sharing. Do NOT ask any further questions.",
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
            "Match a friendly Speaker Pitcher–style flow: brief acknowledgment then ask the next question in a natural, conversational way.",
            "If the step just completed was full_name: acknowledge with 'Great, it's nice to meet you, [first name]!' then rephrase the next_question conversationally (e.g. for topics: 'What are some of the topics you want to cover in your speaking opportunities? You can always add more to your profile later.').",
            "For any other step: use short acknowledgments like 'Great, thanks!', 'Got it.', or 'Thanks.' then smoothly ask the next question. Rephrase the next_question conversationally when it fits (e.g. delivery: 'Do you want virtual events or in-person, or both?'; speaking formats: 'Do you want keynotes, workshops, solo presentations, panels? You can choose all of these.').",
            "Do not mention validation, rules, or grammar. Assume good intent. Tone: warm and conversational. Return ONLY the assistant message. No JSON.",
        ],
        "variation_seed": seed,
    }

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a friendly conversational assistant. Match Speaker Pitcher–style flow: brief acknowledgment (e.g. Great, thanks! / Got it.) then natural rephrasing of the next question. Return ONLY the assistant message text. No JSON.",
                },
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

    # For REFUSAL on these steps use fallback only—avoids AI mixing up steps or suggesting alternatives (e.g. 'topics' for wrong step, 'phone number' for email)
    if reason_code == "REFUSAL" and step_name in ("full_name", "email", "talk_description", "key_takeaways", "delivery_mode", "topics", "speaking_formats", "target_audiences"):
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
            "Write ONE very short assistant message (1–2 short sentences only; under 25 words). No long paragraphs.",
            "Tone: friendly and conversational (like the Speaker Pitcher sample). Assume good intent; do not mention validation or grammar.",
            "Do not mention grammar, spelling, or 'validation'.",
            "Never use demanding or bureaucratic language: no 'This is a required field', 'We need it from you', 'You must provide', or similar.",
            "Do NOT suggest alternatives (e.g. phone number, other contact methods). Only re-ask for the same field; never offer a different field or option.",
            "CRITICAL—match the CURRENT step_name only. Do NOT mention 'topics' or 'pick a topic' or 'Sharing topics' unless step_name is exactly 'topics'. For delivery_mode say 'delivery' or 'how you deliver', never 'topics'. For target_audiences say 'target audiences' or 'who your audience is', never 'topics'. For talk_description or key_takeaways there is NO list—ask for a description or key takeaways in their own words; never say 'pick from the list' or 'topic'.",
            "When step_name is 'topics': brief line on why topics help match them to opportunities, then ask to pick from the list.",
            "When step_name is 'speaking_formats': brief line on why formats help (event organizers find them), then ask to pick from the list (e.g. Keynote, Panel, etc.). Do not say 'topics'.",
            "When step_name is 'delivery_mode': brief line on why delivery helps (match to events), then ask to choose from the options (In-Person, Virtual, Hybrid). Do not say 'topics' or 'Sharing topics'.",
            "When step_name is 'talk_description': brief line on why describing their talk helps (match to right events), then ask to share a description of their talk or expertise in their own words. No list, no topics.",
            "When step_name is 'key_takeaways': brief line on why key takeaways help, then ask to share a few points for their audience. No list, no topics.",
            "When step_name is 'target_audiences': brief line on why target audiences help (match to right events), then ask to pick from the list. Do not say 'topics'.",
            "For other steps, re-ask in a friendly way in 1–2 short sentences, matching that step only.",
            "Focus on intent, not length or picking all options.",
            "Vary phrasing compared to prior attempts (retry_count).",
            "If retry_count > 1, add one short hint that fits the step (e.g. 'pick from the list' only for steps that have a list: topics, speaking_formats, delivery_mode, target_audiences). For talk_description/key_takeaways, hint 'share a few sentences' or similar, not 'list'.",
            "Do not repeat the exact same wording across retries.",
        ],
        "variation_seed": seed,
    }

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a friendly conversational assistant. Keep every message SHORT: 1–2 short sentences only (under 25 words). No long paragraphs. Return ONLY the assistant message text. No JSON.",
                },
                {"role": "user", "content": str(payload)},
            ],
            temperature=0.8,
            timeout=10,
        )
        msg = (completion.choices[0].message.content or "").strip()
        return msg or _fallback_recovery(step, reason_code, retry_count, allowed_values)
    except Exception:
        return _fallback_recovery(step, reason_code, retry_count, allowed_values)

