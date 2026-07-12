"""Regression guards: the shipped examples must stay importable and runnable.

examples/openai_integration.py previously failed at import time
('from audit import AuditLog') and again at run time (unpacking enforce()
as a tuple). These tests load each example as a module so a future
regression of either kind fails CI rather than shipping silently.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def _load_example(name: str):
    path = EXAMPLES_DIR / name
    spec = importlib.util.spec_from_file_location(f"_example_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # raises on import error / syntax error
    return module


def test_openai_integration_is_importable():
    mod = _load_example("openai_integration.py")
    assert callable(mod.main)


def test_demo_is_importable():
    mod = _load_example("demo.py")
    assert callable(mod.main)


def test_openai_integration_main_runs_with_fake_llm(tmp_path, monkeypatch):
    """Run main() end-to-end in a temp dir so the metrics file is harmless.

    Guards the full enforce()->result-object usage path that was previously
    broken by tuple-unpacking.
    """
    monkeypatch.chdir(tmp_path)
    mod = _load_example("openai_integration.py")
    # main() prints and writes enforcement_metrics.json; it must not raise.
    mod.main()
    assert (tmp_path / "enforcement_metrics.json").exists()
