"""Smoke test: the package imports successfully."""


def test_import_schema_comparator() -> None:
    import schema_comparator  # noqa: F401


def test_import_schema_comparator_report() -> None:
    """Confirms Jinja2/xhtml2pdf import cleanly in the installed environment."""
    import schema_comparator.report  # noqa: F401
