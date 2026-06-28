"""Corge command-line entrypoint.

Traces to docs/02-technical-spec.md and docs/04-functional_testing.md.
"""

from __future__ import annotations

import sys
from datetime import UTC
from pathlib import Path

from textual import work

from corge.agent.bayesian_updater import BayesianUpdater
from corge.agent.schema_tailor import SchemaTailor
from corge.agent.session_controller import SessionController
from corge.approval.gateway import ApprovalGateway
from corge.artifacts.store import ArtifactStore
from corge.budget_manager.manager import BudgetManager
from corge.context.service import ContextService
from corge.context.sticky_validator import StickyNoteValidator
from corge.contracts import (
    LifecycleState,
    Plan,
    PlanStep,
    ProceduralStep,
    RepositoryContext,
    Specification,
    SpecState,
    TechnicalPlan,
)
from corge.knowledge_graph.graph import KnowledgeGraph
from corge.logging.argumentation_log import ArgumentationLog
from corge.logging.audit import AuditLogger
from corge.memory.store import MemoryStore
from corge.providers.provider import bootstrap_provider
from corge.tools.runtime import ToolRuntime
from corge.ui.cli import CliUi, CorgeApp


class RealCorgeApp(CorgeApp):
    """Main Textual application orchestration run loop using the real provider."""

    def __init__(self, target_repo: Path, config_path: Path, global_dir: Path) -> None:
        super().__init__()
        self.target_repo = target_repo.resolve()
        self.config_path = config_path.resolve()
        self.global_dir = global_dir.resolve()

    def on_mount(self) -> None:
        self.run_session()

    @work(thread=True)
    def run_session(self) -> None:
        agent_dir = self.target_repo / ".agent"
        agent_dir.mkdir(parents=True, exist_ok=True)

        # 1. Instantiate concrete implementations
        knowledge_graph = KnowledgeGraph(agent_dir / "kg")
        validator = StickyNoteValidator(knowledge_graph)
        ui = CliUi(self, validator)

        provider = None
        error_message = None
        import tomllib

        while provider is None:
            prefill = {}
            if self.config_path.exists():
                try:
                    with open(self.config_path, "rb") as f:
                        prefill = tomllib.load(f)
                except Exception as exc:
                    print(f"Warning: failed to load config {self.config_path}: {exc}")

            if prefill.get("api_key") == "your-api-key-here":
                prefill["api_key"] = ""

            # Check if we should prompt the user
            should_prompt = (
                not self.config_path.exists()
                or prefill.get("api_key") == ""
                or error_message
            )
            if should_prompt:
                new_cfg = ui.show_provider_config_screen(
                    error_message=error_message,
                    prefill={
                        "model": prefill.get("model", ""),
                        "api_key": prefill.get("api_key", ""),
                        "base_url": prefill.get("base_url", ""),
                        "reasoning_effort": prefill.get("reasoning_effort", ""),
                        "max_socratic_questions": prefill.get("max_socratic_questions", 3),
                    },
                )
                if not new_cfg:
                    try:
                        self.call_from_thread(self.exit)
                    except Exception as exc:
                        print(f"Warning: error during app exit: {exc}")
                    return
                self._update_config_toml(new_cfg)
                error_message = None

            try:
                ui.show_loading("Validating API connection...")
                try:
                    provider = bootstrap_provider(self.config_path)
                    self.auto_advance = getattr(provider._config, "auto_advance_informational_screens", False)
                finally:
                    ui.hide_loading()
            except (FileNotFoundError, ValueError, ConnectionError) as e:
                msg = str(e)
                if isinstance(e, ConnectionError) or "connection" in msg.lower() or "refused" in msg.lower():
                    msg += "\n\n(Please verify that your local LLM server/Ollama is running and the base URL override is correct.)"
                elif isinstance(e, ValueError) or "api key" in msg.lower() or "api_key" in msg.lower():
                    msg += "\n\n(Please verify that your API key is correct and not empty.)"
                error_message = msg

        memory_store = MemoryStore(self.target_repo, self.global_dir)
        context_service = ContextService(
            knowledge_graph, memory_store, self.target_repo
        )
        schema_tailor = SchemaTailor(knowledge_graph, self.global_dir)
        budget_manager = BudgetManager()
        audit_logger = AuditLogger(agent_dir, self.global_dir)
        argumentation_log = ArgumentationLog(agent_dir)
        tool_runtime = ToolRuntime(repo_root=self.target_repo)
        artifact_store = ArtifactStore(agent_dir / "artifacts")

        approval_gateway = ApprovalGateway(ui, audit_logger)
        heuristic_updater = BayesianUpdater(self.global_dir, argumentation_log)

        from corge.prompt_assembler import PromptAssembler
        prompt_assembler = PromptAssembler(context_service, schema_tailor, budget_manager)

        controller = SessionController(
            provider=provider,
            tool_runtime=tool_runtime,
            approval_gateway=approval_gateway,
            context_service=context_service,
            memory_store=memory_store,
            heuristic_updater=heuristic_updater,
            knowledge_graph=knowledge_graph,
            audit_logger=audit_logger,
            artifact_store=artifact_store,
            prompt_assembler=prompt_assembler,
        )

        from corge.agent.session import SessionState, load_session, save_session
        session_state = load_session(agent_dir)
        if session_state:
            controller.load_from_session(session_state)

        import dataclasses

        import dataclasses

        while True:
            ui.update_journey_state(controller.active_agent_name, controller.state.name)
            
            current_session_state = SessionState(
                lifecycle_state=controller.state,
                master_phase=controller.phase,
                spec_state=controller.spec_state,
                plan_state=controller.plan_state,
                specification=controller.specification,
                plan=controller.plan,
                technical_plan=controller.technical_plan,
                procedural_steps=controller.procedural_steps,
                repo_root=self.target_repo,
            )
            save_session(agent_dir, current_session_state)

            if controller.state == LifecycleState.START:
                controller.advance()

            elif controller.state == LifecycleState.REPOSITORY_SELECTION:
                is_empty = True
                if self.target_repo.exists():
                    for child in self.target_repo.iterdir():
                        if child.name not in (".git", ".agent"):
                            is_empty = False
                            break
                controller.set_empty_repo(is_empty)
                controller.advance()

            elif controller.state == LifecycleState.REPOSITORY_ANALYSIS:
                if not controller.is_empty_repo:
                    ui.show_loading("Analyzing repository structure and building Knowledge Graph...")
                try:
                    bundle = controller.analyze_repository(self.target_repo)
                finally:
                    if not controller.is_empty_repo:
                        ui.hide_loading()
                idx = 0
                screens = [
                    lambda: ui.show_repository_understanding(bundle.repository_context),
                    lambda: ui.show_repository_analysis(bundle.repository_context),
                    lambda: ui.show_engineering_profile(bundle.engineering_profile),
                ]
                while 0 <= idx < len(screens):
                    res = screens[idx]()
                    if res is False:
                        idx -= 1
                    else:
                        idx += 1

                if idx < 0:
                    controller.transition_to(LifecycleState.REPOSITORY_SELECTION)
                    continue

                controller.advance()

            elif controller.state == LifecycleState.SPEC_ENTRY:
                controller.specification = ui.show_spec_wizard()
                if controller.specification is None:
                    controller.transition_to(LifecycleState.REPOSITORY_ANALYSIS)
                    continue
                controller.advance()

            elif controller.state == LifecycleState.SPEC_VALIDATION:
                spec = controller.specification
                assert spec is not None
                # Load configured max socratic questions
                heuristics_cfg = controller.load_heuristic_config()
                max_questions = getattr(provider._config, "max_socratic_questions", heuristics_cfg.max_socratic_questions)

                # Run the iterative and capped Socratic wizard loop
                spec, gaps = controller.run_socratic_loop(
                    spec.body, argumentation_log, ui, max_questions=max_questions
                )
                controller.specification = spec

                # Always show the manual refinement editor (Choice 1.2 Option A)
                controller.advance_spec_state(SpecState.ARGUMENTATION_DIFF)
                formatted_spec_text = controller.format_spec_to_text(spec, gaps)
                
                user_edited_spec = ui.show_argumentation_diff(spec.body, formatted_spec_text)
                if user_edited_spec is None:
                    # User clicked Reject or Escape, transition back to Spec Entry
                    controller.transition_to(LifecycleState.SPEC_ENTRY)
                    continue
                
                # Merge user edited text back to Specification fields (Choice 1.1 Option A)
                ui.show_loading("Processing specification edits...")
                try:
                    controller.specification = controller.merge_templated_responses(spec, user_edited_spec)
                finally:
                    ui.hide_loading()

                from corge.agent.session_controller import InvalidTransitionError
                try:
                    controller.advance()
                except InvalidTransitionError:
                    # Unresolved semantic gaps still exist — tell the user and
                    # loop back to the argumentation diff editor.
                    ui.show_confirm(
                        "Unresolved Specification Gaps",
                        "Your specification still contains unresolved gap placeholders\n"
                        "('[GAP: ...]' sections). Please fill them in before proceeding.",
                    )
                    controller.transition_to(LifecycleState.SPEC_VALIDATION)
                    continue

            elif controller.state == LifecycleState.SPEC_APPROVAL:
                controller.finalize_spec_phase(abandoned=False)
                controller.advance()

            elif controller.state == LifecycleState.PLAN_GENERATION:
                spec = controller.specification
                assert spec is not None
                tech_plan = controller.technical_plan
                if tech_plan is None:
                    ui.show_loading("Generating technical plan...")
                    try:
                        tech_plan = controller.generate_technical_plan(spec, on_token=ui.stream_token)
                        controller.technical_plan = tech_plan
                    finally:
                        ui.hide_loading()
                
                new_tech_plan = ui.show_tech_plan_editor(tech_plan)
                if new_tech_plan is None:
                    controller.technical_plan = None
                    controller.transition_to(LifecycleState.SPEC_VALIDATION)
                    continue
                controller.technical_plan = new_tech_plan
                controller.advance()

            elif controller.state == LifecycleState.PLAN_REVIEW:
                tech_plan = controller.technical_plan
                spec = controller.specification
                assert tech_plan is not None
                assert spec is not None
                
                proc_steps = controller.procedural_steps
                if not proc_steps:
                    ui.show_loading("Generating procedural steps...")
                    try:
                        proc_steps = controller.generate_procedural_steps(tech_plan, on_token=ui.stream_token)
                        controller.procedural_steps = proc_steps
                    finally:
                        ui.hide_loading()
                
                new_proc_steps = ui.show_procedural_steps_editor(proc_steps)
                if new_proc_steps is None:
                    controller.procedural_steps = ()
                    controller.transition_to(LifecycleState.PLAN_GENERATION)
                    continue
                controller.procedural_steps = new_proc_steps

                controller.set_approved_plan(
                    Plan(
                        steps=tuple(
                            PlanStep(identifier=s.identifier, description=s.description)
                            for s in controller.procedural_steps
                        ),
                        specification_ref=spec.title,
                    )
                )
                plan = controller.plan
                assert plan is not None
                res_plan = ui.show_plan(plan)
                if res_plan is False:
                    continue
                controller.advance()

            elif controller.state == LifecycleState.PLAN_APPROVAL:
                controller.advance()

            elif controller.state == LifecycleState.EXECUTION:
                step = controller.current_step
                if step is None:
                    controller.advance()
                    continue

                spec = controller.specification
                plan = controller.plan
                assert spec is not None
                assert plan is not None
                
                bundle = controller.collect_context(step, spec)
                
                go_back = False
                while True:
                    if bundle.scenario_memory:
                        res_mem = ui.show_memory(bundle.scenario_memory)
                        if res_mem == "new_spec":
                            controller.transition_to(LifecycleState.SPEC_ENTRY)
                            go_back = True
                            break
                        elif res_mem == "back":
                            if controller.uncomplete_previous_step():
                                go_back = True
                                break
                            else:
                                controller.transition_to(LifecycleState.PLAN_REVIEW)
                                go_back = True
                                break

                    res_exec = ui.show_execution(spec.title, plan, controller.current_step_idx)
                    if res_exec is False:
                        if controller.uncomplete_previous_step():
                            go_back = True
                            break
                        else:
                            controller.transition_to(LifecycleState.PLAN_REVIEW)
                            go_back = True
                            break
                    break
                
                if go_back:
                    continue

                ui.show_loading(f"Executing step: {step.identifier}...")
                from datetime import datetime, UTC

                from corge.agent.coding_agent import ToolExecutionError, ActionRejectedError
                from corge.contracts import MemoryEvent
                try:
                    controller.execute_step(step, bundle, on_token=ui.stream_token)
                    controller.mark_step_completed()
                except ActionRejectedError:
                    if not controller.uncomplete_previous_step():
                        controller.transition_to(LifecycleState.PLAN_REVIEW)
                except ToolExecutionError as e:
                    memory_store.store_scenario(
                        MemoryEvent(
                            kind=spec.title,
                            payload={"step": step.identifier, "error": str(e)},
                            timestamp=datetime.now(UTC).isoformat(),
                        )
                    )

                    retry = ui.show_confirm(
                        "Tool Execution Failed",
                        f"Step {step.identifier} failed with error:\n\n{e}\n\n"
                        "Would you like to retry this step?\n"
                        "(Make your manual code fixes first if needed.\n"
                        "Select 'No' to save your progress and exit the application.)"
                    )
                    if not retry:
                        current_session_state = SessionState(
                            lifecycle_state=controller.state,
                            master_phase=controller.phase,
                            spec_state=controller.spec_state,
                            plan_state=controller.plan_state,
                            specification=controller.specification,
                            plan=controller.plan,
                            technical_plan=controller.technical_plan,
                            procedural_steps=controller.procedural_steps,
                            repo_root=self.target_repo,
                        )
                        save_session(agent_dir, current_session_state)
                        import sys
                        sys.exit(1)
                finally:
                    ui.hide_loading()

            elif controller.state == LifecycleState.VERIFICATION:
                plan = controller.plan
                spec = controller.specification
                assert plan is not None
                assert spec is not None
                step = (
                    plan.steps[-1]
                    if plan.steps
                    else PlanStep(
                        identifier="verification",
                        description="Verification of acceptance criteria",
                    )
                )
                bundle = controller.collect_context(step, spec)
                ui.show_loading("Verifying completion...")
                try:
                    success = controller.evaluate_completion(plan, bundle, on_token=ui.stream_token)
                    from datetime import datetime, UTC

                    from corge.contracts import AuditEvent
                    audit_logger.record_completion(
                        AuditEvent(
                            kind="evaluate_completion",
                            payload={"success": success, "step": step.identifier},
                            timestamp=datetime.now(UTC).isoformat()
                        )
                    )
                finally:
                    ui.hide_loading()
                controller.advance()

            elif controller.state == LifecycleState.COMPLETION_REVIEW:
                plan = controller.plan
                assert plan is not None
                while True:
                    res_review = ui.show_completion_review(plan)
                    if res_review is False:
                        controller.transition_to(LifecycleState.VERIFICATION)
                        break
                    res_logs = ui.show_logs()
                    if res_logs is False:
                        continue
                    controller.advance()
                    continue

            elif controller.state == LifecycleState.DONE:
                choice = ui.show_post_completion_options()
                if choice == "new_spec":
                    controller.specification = None
                    controller.plan = None
                    controller.technical_plan = None
                    controller.procedural_steps = ()
                    controller.transition_to(LifecycleState.SPEC_ENTRY)
                    
                    current_session_state = SessionState(
                        lifecycle_state=controller.state,
                        master_phase=controller.phase,
                        spec_state=controller.spec_state,
                        plan_state=controller.plan_state,
                        specification=controller.specification,
                        plan=controller.plan,
                        technical_plan=controller.technical_plan,
                        procedural_steps=controller.procedural_steps,
                        repo_root=self.target_repo,
                    )
                    save_session(agent_dir, current_session_state)
                    continue
                elif choice == "switch_repo":
                    try:
                        self.call_from_thread(self.exit, "switch_repo")
                    except Exception as exc:
                        print(f"Warning: error during app exit: {exc}")
                    return
                else:
                    break

            else:
                break

        try:
            self.call_from_thread(self.exit)
        except Exception as exc:
            print(f"Warning: error during app exit: {exc}")

    def _update_config_toml(self, new_cfg: dict[str, str]) -> None:
        import tomllib
        from typing import Any

        existing: dict[str, Any] = {}
        if self.config_path.exists():
            try:
                with open(self.config_path, "rb") as f:
                    existing = tomllib.load(f)
            except Exception as exc:
                print(f"Warning: failed to load config {self.config_path}: {exc}")
        else:
            # Prefill from config.toml.example
            template_path = (
                Path(__file__).resolve().parent.parent.parent / "config.toml.example"
            )
            if not template_path.exists():
                template_path = Path("config.toml.example")
            if template_path.exists():
                try:
                    with open(template_path, "rb") as f:
                        existing = tomllib.load(f)
                except Exception as exc:
                    print(f"Warning: failed to load template config {template_path}: {exc}")

        # Update fields from editor
        existing["model"] = new_cfg["model"]
        existing["api_key"] = new_cfg["api_key"]
        existing["base_url"] = new_cfg.get("base_url", "")

        effort = new_cfg.get("reasoning_effort", "")
        if effort:
            existing["reasoning_effort"] = effort
        elif "reasoning_effort" in existing:
            del existing["reasoning_effort"]

        questions = new_cfg.get("max_socratic_questions", "3")
        try:
            existing["max_socratic_questions"] = int(questions)
        except (ValueError, TypeError):
            existing["max_socratic_questions"] = 3

        # Make sure standard defaults exist if missing
        if "max_tokens" not in existing:
            existing["max_tokens"] = 4096
        if "keep_alive" not in existing:
            existing["keep_alive"] = "-1"
        if "timeout" not in existing:
            existing["timeout"] = 120.0
        if "enable_prefix_caching" not in existing:
            existing["enable_prefix_caching"] = True

        # Custom flat-dictionary to TOML serializer
        lines = ["# Corge LLM Provider Configuration"]
        extra_headers = {}
        for k, v in existing.items():
            if k == "extra_headers":
                extra_headers = v
                continue
            if v is None:
                continue
            if isinstance(v, bool):
                lines.append(f"{k} = {str(v).lower()}")
            elif isinstance(v, (int, float)):
                lines.append(f"{k} = {v}")
            else:
                lines.append(f'{k} = "{v}"')

        if extra_headers:
            lines.append("\n[extra_headers]")
            for hk, hv in extra_headers.items():
                lines.append(f'{hk} = "{hv}"')

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """CLI entrypoint function."""
    while True:
        if len(sys.argv) > 1:
            target_path = Path(sys.argv[1]).resolve()
            # Clear sys.argv so if the user switches projects, we fall back to the directory selector
            sys.argv = [sys.argv[0]]
        else:
            from corge.ui.cli import DirectorySelectorApp
            selected = DirectorySelectorApp().run()
            if not selected:
                sys.exit(0)
            target_path = selected

        if not target_path.exists():
            print(f"Error: Target path '{target_path}' does not exist.", file=sys.stderr)
            sys.exit(1)

        print("\nInitializing Corge Coding Agent...")
        print(f"Loading repository: {target_path}")

        global_dir = Path.home() / ".config" / "corge"

        global_dir.mkdir(parents=True, exist_ok=True)

        # Config resolution order:
        # 1. target_path / ".agents" / "CorgeAPIConfig.toml"
        # 2. target_path / "agents" / "CorgeAPIConfig.toml"
        # 3. target_path / "CorgeAPIConfig.toml"
        # 4. target_path / ".agent" / "CorgeAPIConfig.toml"
        # Defaults to target_path / ".agents" / "CorgeAPIConfig.toml"
        config_path = target_path / ".agents" / "CorgeAPIConfig.toml"
        if not config_path.exists():
            for path in [
                target_path / "agents" / "CorgeAPIConfig.toml",
                target_path / "CorgeAPIConfig.toml",
                target_path / ".agent" / "CorgeAPIConfig.toml",
            ]:
                if path.exists():
                    config_path = path
                    break

        try:
            app = RealCorgeApp(target_repo=target_path, config_path=config_path, global_dir=global_dir)
            result = app.run()
            if result == "switch_repo":
                continue
            break
        except (FileNotFoundError, ValueError, ConnectionError) as e:
            print(f"Configuration Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
