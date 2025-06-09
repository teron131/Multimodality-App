#!/usr/bin/env python3
"""Simple test runner for the utils module."""

import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Run the test suite for utils module."""
    test_dir = Path(__file__).parent
    project_root = test_dir.parent

    print("🧪 Running utils tests...")

    try:
        result = subprocess.run(
            ["uv", "run", "pytest", "test/test_utils.py", "-v"],
            cwd=project_root,
            check=True,
        )
        print("✅ All tests passed!")

    except subprocess.CalledProcessError as e:
        print(f"❌ Tests failed with exit code {e.returncode}")
        sys.exit(e.returncode)
    except FileNotFoundError:
        print("❌ uv not found. Please install uv or run tests manually with: pytest test/test_utils.py -v")
        sys.exit(1)


if __name__ == "__main__":
    main()
