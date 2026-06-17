"""Prompt construction — satisfies ``contracts.PromptAssemblerPort``."""

from corge.contracts import ContextBundle, PlanStep


class PromptAssembler:
    """Concrete prompt assembler stub.  Satisfies ``contracts.PromptAssemblerPort``."""

    def collect_context(self, step: PlanStep) -> ContextBundle:
        raise NotImplementedError

    def assemble_prompt(self, context: ContextBundle) -> str:
        raise NotImplementedError
