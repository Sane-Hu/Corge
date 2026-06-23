"""Interactive CLI directory selection helper."""

from __future__ import annotations

import sys
from pathlib import Path


def choose_directory_cli(start_path: Path | None = None) -> Path:
    """Interactively let the user explore directories to choose or create one.

    This runs in pure CLI (stdin/stdout) before the Textual UI is started.
    """
    current = (start_path or Path.cwd()).resolve()
    while True:
        print("\n--- Corge Target Repository Selection ---")
        print(f"Current Directory: {current}")

        # Gather visible subdirectories
        try:
            subdirs = sorted(
                [
                    p
                    for p in current.iterdir()
                    if p.is_dir() and not p.name.startswith(".")
                ]
            )
        except PermissionError:
            print("Error: Permission denied to read this directory.")
            subdirs = []

        print("\nOptions:")
        print("  [0] Confirm and use: (this current directory)")
        print("  [1] Go up to parent directory")
        print("  [2] Create a new directory here")
        print("  [3] Enter a path manually")

        for idx, sd in enumerate(subdirs, 4):
            print(f"  [{idx}] Navigate into: {sd.name}/")

        try:
            choice = input("\nSelect option or directory number: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSelection cancelled. Exiting.")
            sys.exit(0)

        if choice == "0":
            return current
        elif choice == "1":
            current = current.parent.resolve()
        elif choice == "2":
            new_name = input("Enter new directory name: ").strip()
            if new_name:
                new_dir = current / new_name
                try:
                    new_dir.mkdir(parents=True, exist_ok=True)
                    print(f"Created directory: {new_dir}")
                    current = new_dir.resolve()
                except Exception as e:
                    print(f"Error creating directory: {e}")
        elif choice == "3":
            manual_path = input("Enter path: ").strip()
            if manual_path:
                p = Path(manual_path).expanduser().resolve()
                if p.is_dir():
                    current = p
                elif not p.exists():
                    create_choice = (
                        input(f"Directory '{p}' does not exist. Create it? (y/n): ")
                        .strip()
                        .lower()
                    )
                    if create_choice == "y":
                        try:
                            p.mkdir(parents=True, exist_ok=True)
                            current = p
                        except Exception as e:
                            print(f"Error creating directory: {e}")
                else:
                    print(f"Path '{p}' is not a directory.")
        else:
            try:
                idx = int(choice)
                if 4 <= idx < len(subdirs) + 4:
                    current = subdirs[idx - 4]
                else:
                    print(
                        "Invalid choice. Please select one of the "
                        "listed option numbers."
                    )
            except ValueError:
                print("Invalid choice. Please enter a valid number.")
