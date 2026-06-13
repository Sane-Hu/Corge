"""Structural checks for the initial boilerplate."""

import importlib


def test_architecture_packages_are_importable() -> None:
    packages = [
        "corge",
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

    for package in packages:
        importlib.import_module(package)

