"""Specification agent — handles SpecState reiterations."""

import json
import re

from corge.contracts import ProviderMessage, ProviderPort, SemanticGap


class SpecificationAgent:
    """Manages the interactive specification wizard and semantic gaps."""
    
    def __init__(self, provider: ProviderPort) -> None:
        self.provider = provider

    def analyze_specification_gaps(self, canvas_text: str) -> tuple[SemanticGap, ...]:
        prompt = (
            "You are a strict system architect.\n"
            "Analyze the following drafted specification for semantic gaps, "
            "missing logic, or undefined edge cases.\n"
            "Return ONLY a JSON array of objects with keys 'topic' and 'description'.\n\n"
            f"Draft:\n{canvas_text}"
        )
        msg = ProviderMessage(role="user", content=prompt)
        response = self.provider.chat((msg,))
        
        match = re.search(r"\[.*\]", response.content, re.DOTALL)
        if match:
            try:
                gaps = json.loads(match.group(0))
                return tuple(
                    SemanticGap(topic=g["topic"], description=g["description"])
                    for g in gaps
                )
            except Exception:
                pass
        return ()
