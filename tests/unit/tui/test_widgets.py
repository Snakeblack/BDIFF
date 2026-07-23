"""Unit tests for the new tui.widgets: StatusLog and ExcludeEditor."""

import pytest

from schema_comparator.tui.widgets import ExcludeEditor, StatusLog


@pytest.mark.asyncio
async def test_status_log_info_writes_message() -> None:
    from textual.app import App, ComposeResult

    class _Harness(App):
        def compose(self) -> ComposeResult:
            yield StatusLog(id="status-log")

    app = _Harness()
    async with app.run_test():
        log = app.query_one(StatusLog)
        log.info("Comparación actualizada.")

        assert any("Comparación actualizada." in str(line) for line in log.lines)


@pytest.mark.asyncio
async def test_status_log_error_writes_styled_message() -> None:
    from textual.app import App, ComposeResult

    class _Harness(App):
        def compose(self) -> ComposeResult:
            yield StatusLog(id="status-log")

    app = _Harness()
    async with app.run_test():
        log = app.query_one(StatusLog)
        log.error("Falló la comparación: boom")

        assert any(
            "Fall\u00f3 la comparaci\u00f3n: boom" in str(line) for line in log.lines
        )


@pytest.mark.asyncio
async def test_exclude_editor_seeds_value_from_pattern_list() -> None:
    from textual.app import App, ComposeResult

    class _Harness(App):
        def compose(self) -> ComposeResult:
            yield ExcludeEditor(["LOG", "QRTZ"], id="exclude-editor")

    app = _Harness()
    async with app.run_test():
        editor = app.query_one(ExcludeEditor)

        assert editor.value == "LOG QRTZ"


@pytest.mark.asyncio
async def test_exclude_editor_empty_patterns_seeds_empty_value() -> None:
    from textual.app import App, ComposeResult

    class _Harness(App):
        def compose(self) -> ComposeResult:
            yield ExcludeEditor([], id="exclude-editor")

    app = _Harness()
    async with app.run_test():
        editor = app.query_one(ExcludeEditor)

        assert editor.value == ""
