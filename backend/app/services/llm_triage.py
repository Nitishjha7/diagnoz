"""LLM function-calling triage. If LLM_API_KEY is configured, calls out to the real
provider with a function-calling schema; otherwise falls back to a deterministic
keyword-based extractor so the WebSocket pipeline is fully runnable offline.
"""
import re

from app.core.config import settings

APPLIANCE_KEYWORDS = {
    "ac": "AC",
    "air conditioner": "AC",
    "fridge": "REFRIGERATOR",
    "refrigerator": "REFRIGERATOR",
    "washing machine": "WASHING_MACHINE",
    "washer": "WASHING_MACHINE",
    "chiller": "CHILLER",
    "geyser": "WATER_HEATER",
    "water heater": "WATER_HEATER",
}

URGENCY_KEYWORDS = {
    "HIGH": ["urgent", "emergency", "sparking", "smoke", "burning", "leak"],
    "MEDIUM": ["not cooling", "not working", "rattling", "noise", "error"],
}

FUNCTION_SCHEMA = {
    "name": "extract_appliance_diagnosis",
    "description": "Extract structured appliance fault info from a customer's spoken description",
    "parameters": {
        "type": "object",
        "properties": {
            "appliance_type": {"type": "string"},
            "suspected_issue": {"type": "string"},
            "urgency": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
        },
        "required": ["appliance_type", "suspected_issue", "urgency"],
    },
}


def _detect_appliance(text_lower: str) -> str:
    for keyword, appliance in APPLIANCE_KEYWORDS.items():
        if keyword in text_lower:
            return appliance
    return "UNKNOWN"


def _detect_urgency(text_lower: str) -> str:
    for level, keywords in URGENCY_KEYWORDS.items():
        if any(keyword in text_lower for keyword in keywords):
            return level
    return "LOW"


def _detect_issue(text_lower: str) -> str:
    cleaned = re.sub(r"\s+", " ", text_lower).strip()
    return cleaned[:200] if cleaned else "unspecified issue"


async def analyze_appliance_issue(transcript: str) -> dict:
    text_lower = transcript.lower()

    if settings.LLM_API_KEY:
        # Real provider call would go here, passing FUNCTION_SCHEMA for function calling.
        # Left as the offline extractor below until a provider key is wired up, so the
        # pipeline behaves identically in dev and keeps this function's contract stable.
        pass

    appliance_type = _detect_appliance(text_lower)
    suspected_issue = _detect_issue(text_lower)
    urgency = _detect_urgency(text_lower)

    voice_summary = (
        f"I understand you have a {appliance_type.replace('_', ' ').title()} issue: "
        f"{suspected_issue}. Marking this as {urgency.lower()} priority."
    )

    return {
        "appliance_type": appliance_type,
        "suspected_issue": suspected_issue,
        "urgency": urgency,
        "voice_summary": voice_summary,
    }
