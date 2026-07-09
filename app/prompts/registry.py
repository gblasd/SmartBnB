"""Centralized prompt registry for SmartBnB."""

from app.prompts.templates import (
    PromptTemplate,
    AGENT_SYSTEM,
    DASHBOARD_SYSTEM,
    REVIEW_ANALYSIS,
    PROPERTY_SEARCH,
    QUERY_REWRITE,
)

class PromptRegistry:
    def __init__(self):
        self._prompts: dict[str, PromptTemplate] = {}

    def register(self, prompt: PromptTemplate) -> None:
        key = f"{prompt.name}:{prompt.version}"
        self._prompts[key] = prompt
        self._prompts[f"{prompt.name}:latest"] = prompt

    def get(self, name: str, version: str = "latest") -> PromptTemplate:
        key = f"{name}:{version}"
        if key not in self._prompts:
            raise KeyError(f"Prompt '{key}' not found in registry")
        return self._prompts[key]

    def list_prompts(self) -> list[str]:
        return [k for k in self._prompts if not k.endswith(":latest")]

prompt_registry = PromptRegistry()
for template in [AGENT_SYSTEM, DASHBOARD_SYSTEM, REVIEW_ANALYSIS, PROPERTY_SEARCH, QUERY_REWRITE]:
    prompt_registry.register(template)
