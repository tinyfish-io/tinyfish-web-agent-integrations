"""Validate that all Python files in the package can be imported."""

import importlib.util
import sys
import traceback


if __name__ == "__main__":
    files = sys.argv[1:]
    has_failure = False
    for file in files:
        try:
            spec = importlib.util.spec_from_file_location("x", file)
            assert spec is not None and spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception:
            has_failure = True
            print(file)  # noqa: T201
            traceback.print_exc()
            print()  # noqa: T201
    sys.exit(1 if has_failure else 0)
