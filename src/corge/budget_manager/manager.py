"""Context budget enforcement — satisfies ``contracts.BudgetManagerPort``."""

import dataclasses

from corge.contracts import ContextBundle


class BudgetManager:
    """Concrete budget manager.  Satisfies ``contracts.BudgetManagerPort``."""

    def _estimate_str(self, text: str) -> int:
        return len(text) // 4

    def _clip_large_string(self, text: str, max_length: int = 2000) -> str:
        if len(text) <= max_length:
            return text
        half = max_length // 2
        return text[:half] + "\n... [CLIPPED] ...\n" + text[-half:]

    def _bundle_to_text(self, context: ContextBundle) -> str:
        lines = [context.specification.title, context.specification.body]
        lines.extend(context.engineering_profile.rules)
        for mem in context.scenario_memory:
            lines.append(str(mem.payload))
        lines.extend(context.recent_actions)
        return "\n".join(lines)

    def estimate_tokens(self, context: ContextBundle) -> int:
        text = self._bundle_to_text(context)
        try:
            import tiktoken

            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except ImportError:
            # todo: fallback heuristic; upgrade path: install tiktoken for ±1% accuracy
            return len(text) // 4

    def rank_context(self, context: ContextBundle) -> ContextBundle:
        # todo: implement semantic ranking (e.g. TF-IDF or vector similarity) 
        # Tiers are structurally ranked in the ContextBundle definition.
        return context

    def clip(self, context: ContextBundle, token_limit: int) -> ContextBundle:
        # 1. Always clip large individual outputs in the transcript to save token costs
        clipped_actions = tuple(
            self._clip_large_string(action) for action in context.recent_actions
        )

        # 2. Always drop older events to maintain a tight context loop and prevent
        # multi-turn bloat, regardless of whether we are near the actual LLM limit.
        # This keeps token usage (and thus cost) low without hindering performance.
        context = dataclasses.replace(
            context,
            scenario_memory=context.scenario_memory[-10:],
            engineering_facts=context.engineering_facts[-10:],
            recent_actions=clipped_actions[-20:],
        )

        # 3. If for some reason we are STILL over a hard token limit
        # (e.g. massive single step),
        # apply an even stricter emergency fallback.
        if self.estimate_tokens(context) > token_limit:
            return dataclasses.replace(
                context,
                scenario_memory=context.scenario_memory[-3:],
                engineering_facts=context.engineering_facts[-3:],
                recent_actions=context.recent_actions[-5:],
            )

        return context

    def deduplicate(self, context: ContextBundle) -> ContextBundle:
        # Deduplicate files and facts while preserving order
        unique_files = tuple(dict.fromkeys(context.relevant_files))
        unique_facts = tuple(dict.fromkeys(context.engineering_facts))

        # Deduplicate older reads/actions in the transcript.
        # We keep the LATEST occurrence.
        # Reverse, deduplicate, then reverse back.
        unique_actions_reversed = list(dict.fromkeys(reversed(context.recent_actions)))
        unique_actions = tuple(reversed(unique_actions_reversed))

        return dataclasses.replace(
            context,
            relevant_files=unique_files,
            recent_actions=unique_actions,
            engineering_facts=unique_facts,
        )

    def summarize(self, context: ContextBundle) -> str:
        # todo: implement LLM-based summarization for massive context
        step_id = context.current_step_id or "unknown"
        return f"Context for Step {step_id}: {context.specification.title}"

    def compact(self, context: ContextBundle) -> ContextBundle:
        context = self.deduplicate(context)
        # We aggressively compact to save usage costs in large-context models.
        # token_limit acts as an emergency hard ceiling.
        return self.clip(context, token_limit=128000)
