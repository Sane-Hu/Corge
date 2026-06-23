"""Skeleton import contract tests."""

import importlib


def test_public_modules_import_cleanly() -> None:
    module_names = [
        "corge",
        "corge.contracts",
        "corge.ui",
        "corge.agent",
        "corge.context",
        "corge.prompt_assembler",
        "corge.budget_manager",
        "corge.knowledge_graph",
        "corge.memory",
        "corge.artifacts",
        "corge.approval",
        "corge.tools",
        "corge.providers",
        "corge.logging",
    ]

    for module_name in module_names:
        module = importlib.import_module(module_name)
        assert module is not None
