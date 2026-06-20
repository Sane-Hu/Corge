"""Planning and execution orchestration — satisfies ``contracts.AgentPort``."""

import json
import pathlib
from typing import Any

from corge.contracts import (
    ApprovalDecision,
    ApprovalGatewayPort,
    ApprovalRequest,
    ContextBundle,
    MemoryEvent,
    MemoryStorePort,
    Plan,
    PlanStep,
    ProceduralStep,
    PromptAssemblerPort,
    ProviderMessage,
    ProviderPort,
    SchemaTailorPort,
    SemanticGap,
    Specification,
    TechnicalPlan,
    ToolAction,
    ToolRuntimePort,
)


class ToolExecutionError(Exception):
    """Raised when a tool execution fails to prevent straying."""
    pass


class AgentService:
    """Concrete agent stub. Satisfies ``contracts.AgentPort`` protocol."""

    def __init__(
        self,
        provider: ProviderPort,
        prompt_assembler: PromptAssemblerPort,
        tool_runtime: ToolRuntimePort,
        approval_gateway: ApprovalGatewayPort,
        memory_store: MemoryStorePort,
        schema_tailor: SchemaTailorPort,
    ) -> None:
        self._provider = provider
        self._prompt_assembler = prompt_assembler
        self._tool_runtime = tool_runtime
        self._approval_gateway = approval_gateway
        self._memory_store = memory_store
        self._schema_tailor = schema_tailor

    def _parse_json(self, text: str) -> Any:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:-3].strip()
        elif text.startswith("```"):
            text = text[3:-3].strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ToolExecutionError(f"Failed to parse provider response: {e}") from e

    def analyze_specification_gaps(self, canvas_text: str) -> tuple[SemanticGap, ...]:
        framework = self._schema_tailor.detect_framework()
        schema = self._schema_tailor.fetch_schema(framework)
        
        prompt = (
            f"Analyze the following freestyle canvas text for missing requirements.\n"
            f"Context framework: {framework or 'generic'}\n"
            f"Schema expected structure: {json.dumps(schema)}\n"
            f"Canvas Text: {canvas_text}\n\n"
            f"Return a JSON object with a 'gaps' array. Each gap should be an object "
            f"with a 'topic' (string) indicating what is missing (e.g. 'Database Schema', "
            f"'Auth Middleware')."
        )
        response = self._provider.chat((ProviderMessage(role="user", content=prompt),))
        try:
            data = self._parse_json(response.content)
            gaps = [SemanticGap(topic=g["topic"]) for g in data.get("gaps", [])]
            return tuple(gaps)
        except Exception:
            return ()

    def generate_technical_plan(self, specification: Specification) -> TechnicalPlan:
        prompt = (
            f"Create a technical architecture plan for the following specification.\n"
            f"Title: {specification.title}\n"
            f"Body: {specification.body}\n"
            f"Acceptance Criteria: {specification.acceptance_criteria.items}\n\n"
            f"Return a JSON object with a 'content' string that outlines module boundaries, "
            f"interfaces, and high-level architecture decisions."
        )
        response = self._provider.chat((ProviderMessage(role="user", content=prompt),))
        data = self._parse_json(response.content)
        content = data.get("content", "No technical plan generated.")
        return TechnicalPlan(content=content, specification_ref=specification.title)

    def generate_procedural_steps(
        self, technical_plan: TechnicalPlan
    ) -> tuple[ProceduralStep, ...]:
        prompt = (
            f"Based on the following technical plan, create granular procedural execution steps.\n"
            f"Technical Plan:\n{technical_plan.content}\n\n"
            f"Return a JSON object with a 'steps' array. Each step should be an object "
            f"with 'identifier' (string) and 'description' (string)."
        )
        response = self._provider.chat((ProviderMessage(role="user", content=prompt),))
        data = self._parse_json(response.content)

        steps = []
        for step_data in data.get("steps", []):
            steps.append(
                ProceduralStep(
                    identifier=step_data.get("identifier", "unknown"),
                    description=step_data.get("description", "No description"),
                )
            )
        return tuple(steps)

    def execute_step(self, step: PlanStep, context: ContextBundle) -> None:
        prompt = self._prompt_assembler.assemble_prompt(context)
        prompt += (
            "\n\nReturn a JSON object representing the tool action to take. "
            "It must include 'action' (string, e.g. 'read', 'write', 'edit', 'bash'), "
            "'target' (string), and 'content' (string, for write), "
            "'old' and 'new' (for edit), or 'command' (string, for bash)."
        )
        response = self._provider.chat((ProviderMessage(role="user", content=prompt),))
        data = self._parse_json(response.content)

        action_str = data.get("action")
        try:
            action = ToolAction(action_str)
        except ValueError as e:
            raise ToolExecutionError(f"Invalid tool action: {action_str}") from e

        target = data.get("target", "")

        if action != ToolAction.READ:
            request = ApprovalRequest(
                action=action,
                target=target,
                reason=step.description,
                step_ref=step.identifier,
            )
            decision = self._approval_gateway.approve(request)
            if decision == ApprovalDecision.REJECTED:
                raise ToolExecutionError("Action was rejected by human approval.")

        path = pathlib.Path(target)
        if action == ToolAction.READ:
            result = self._tool_runtime.read(path)
        elif action == ToolAction.WRITE:
            result = self._tool_runtime.write(path, data.get("content", ""))
        elif action == ToolAction.EDIT:
            result = self._tool_runtime.edit(
                path, data.get("old", ""), data.get("new", "")
            )
        elif action == ToolAction.BASH:
            result = self._tool_runtime.bash(
                data.get("command", ""), context.repository_context.root
            )
        else:
            raise ToolExecutionError(f"Unsupported tool action: {action}")

        if not result.success:
            raise ToolExecutionError(f"Tool execution failed: {result.stderr}")

    def evaluate_completion(self, plan: Plan, context: ContextBundle) -> bool:
        prompt = (
            f"Are the acceptance criteria met for plan '{plan.specification_ref}'?\n"
            f"Return a JSON object with a boolean 'completed'."
        )
        response = self._provider.chat((ProviderMessage(role="user", content=prompt),))
        data = self._parse_json(response.content)
        return bool(data.get("completed", False))

    def update_memory(self, event: MemoryEvent) -> None:
        self._memory_store.store_event(event)
