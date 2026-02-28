"""
Shared utility/helper functions used across services.
"""

def strip_json_codeblock(text: str) -> str:
    """
    Strips ```json ... ``` or ``` ... ``` wrappers from LLM output.
    """
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def clamp(value: float, min_val: float, max_val: float) -> float:
    """
    Clamps a float value between min and max.
    """
    return max(min_val, min(max_val, value))
