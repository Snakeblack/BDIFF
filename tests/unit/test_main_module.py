"""Unit test for `schema_comparator.__main__`: confirms the module-level
guard reaches `cli.main`, enabling `python -m schema_comparator.cli`
style invocation used by run.py's relaunch step."""

import runpy
from unittest.mock import patch


def test_module_invocation_runs_main() -> None:
    with patch("schema_comparator.cli.main") as m_main:
        runpy.run_module("schema_comparator.__main__", run_name="__main__")

    m_main.assert_called_once_with()
