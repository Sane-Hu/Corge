"""Prompt construction boundaries."""

from corge.contracts import ContextBundle, PlanStep


class PromptAssembler:
    """Prompt assembler responsibilities from docs/04-module-contracts.md."""

    def collect_context(self, step: PlanStep) -> ContextBundle:
        raise NotImplementedError

    def assemble_prompt(self, context: ContextBundle) -> str:
        raise NotImplementedError

