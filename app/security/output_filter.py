"""Output filtering and sanitization."""

import re
from dataclasses import dataclass

@dataclass
class FilterResult:
    safe: bool
    reason: str = ""
    filtered_content: str = ""

class OutputFilter:
    SENSITIVE_PATTERNS = {
        "api_key": r"(?:sk-|key-)[a-zA-Z0-9]{20,}",
        "aws_key": r"AKIA[0-9A-Z]{16}",
        "connection_string": r"(?:postgresql|mysql|mongodb)://[^\s]+",
        "password": r"(?:password|passwd|pwd)\s*[=:]\s*\S+",
    }
    PII_PATTERNS = {
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b\d{4}[-.\s]?\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b",
    }

    async def filter(self, content: str) -> FilterResult:
        if not content:
            return FilterResult(safe=True, filtered_content="")
        filtered = content
        reasons = []
        for name, pattern in self.SENSITIVE_PATTERNS.items():
            if re.search(pattern, filtered):
                filtered = re.sub(pattern, f"[REDACTED_{name.upper()}]", filtered)
                reasons.append(f"Redacted {name}")
        for name, pattern in self.PII_PATTERNS.items():
            if re.search(pattern, filtered):
                filtered = re.sub(pattern, f"[REDACTED_{name.upper()}]", filtered)
                reasons.append(f"Redacted {name}")
        return FilterResult(
            safe=len(reasons) == 0,
            reason="; ".join(reasons) if reasons else "",
            filtered_content=filtered,
        )

output_filter = OutputFilter()
