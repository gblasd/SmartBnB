"""Input validation and prompt injection detection."""

import re
from dataclasses import dataclass

@dataclass
class ValidationResult:
    safe: bool
    reason: str = ""
    sanitized_input: str = ""

class InputGuard:
    INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"you\s+are\s+now",
        r"forget\s+(your|all)\s+rules",
        r"system\s*prompt",
        r"act\s+as\s+(if|a)",
        r"pretend\s+you\s+are",
        r"\bDAN\b",
        r"do\s+anything\s+now",
    ]
    MAX_INPUT_LENGTH = 10_000
    PII_PATTERNS = {
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "phone": r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b\d{4}[-.\s]?\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b",
    }

    async def validate(self, user_input: str) -> ValidationResult:
        if not user_input or not user_input.strip():
            return ValidationResult(safe=False, reason="Empty input")
        if len(user_input) > self.MAX_INPUT_LENGTH:
            return ValidationResult(
                safe=False,
                reason=f"Input too long ({len(user_input)} > {self.MAX_INPUT_LENGTH})",
            )
        if self._detect_injection(user_input):
            return ValidationResult(safe=False, reason="Potential prompt injection detected")
        sanitized = self._redact_pii(user_input)
        return ValidationResult(safe=True, sanitized_input=sanitized)

    def _detect_injection(self, text: str) -> bool:
        text_lower = text.lower()
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, text_lower):
                return True
        return False

    def _redact_pii(self, text: str) -> str:
        result = text
        for pii_type, pattern in self.PII_PATTERNS.items():
            result = re.sub(pattern, f"[REDACTED_{pii_type.upper()}]", result)
        return result

input_guard = InputGuard()
