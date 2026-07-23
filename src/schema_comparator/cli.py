"""Command-line entry point: load profiles, extract schemas, compare, report.

Composition root wiring `config.loader.load_profiles` -> `application.use_cases.CompareProfilesUseCase`
-> `report.write.write_reports`. No `--format` flag: v1 always generates all
four report outputs (HTML, PDF, Excel, console/TUI).
"""

from __future__ import annotations

import argparse
import functools
import sys

from schema_comparator.config.loader import load_profiles
from schema_comparator.report.write import write_reports
from schema_comparator.tui import run_tui
from schema_comparator.tui.actions import run_comparison


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="schema-comparator")
    parser.add_argument(
        "--config", required=True, help="Ruta al archivo YAML de perfiles de conexión"
    )
    parser.add_argument(
        "--profiles",
        nargs="+",
        help="Subconjunto de nombres de perfiles a comparar (por defecto: todos)",
    )
    parser.add_argument(
        "--tui",
        action="store_true",
        help="Inicia un navegador interactivo de hallazgos en lugar del "
        "resumen de consola simple (requiere una terminal interactiva)",
    )
    parser.add_argument(
        "--exclude-tables",
        nargs="+",
        help="Excluye tablas cuyo nombre contenga alguno de estos textos "
        "(no distingue mayúsculas/minúsculas), p. ej. --exclude-tables LOG QRTZ",
    )
    parser.add_argument(
        "--verify-sps",
        action="store_true",
        help="Ejecuta sp_refreshsqlmodule en SQL Server para verificar que los "
        "procedimientos y vistas compilen correctamente sin referencias rotas",
    )
    return parser


def _resolve_summary_renderer_and_generate_reports(
    use_tui: bool,
    profiles: list,
    exclude_patterns: list[str],
) -> tuple:
    """Decide which `render_summary` callable (if any) to pass to
    `write_reports`, and whether automatic HTML/PDF/Excel generation
    should still happen at startup. Returns
    `(render_summary_or_None, generate_reports: bool)`.
    """
    if not use_tui:
        return None, True
    if sys.stdout.isatty() and sys.stdin.isatty():
        bound_run_tui = functools.partial(
            run_tui, profiles=profiles, exclude_patterns=exclude_patterns
        )
        return bound_run_tui, False
    print(
        "[AVISO] --tui requiere una terminal interactiva; "
        "se usará el resumen de consola simple",
        file=sys.stderr,
    )
    return None, True


def _run_sp_verification(profiles: list, exclude_patterns: list[str] | None = None) -> None:
    from schema_comparator.infrastructure.providers.sqlserver import connection
    from schema_comparator.infrastructure.providers.sqlserver.sp_validator import verify_sps_with_refresh

    patterns = [p.lower() for p in (exclude_patterns or [])]
    print("\n🔍 Ejecutando verificación de procedimientos almacenados y vistas (sp_refreshsqlmodule)...")
    for profile in profiles:
        provider_name = str(getattr(profile, "provider", "sqlserver")).lower()
        if provider_name == "sqlserver":
            try:
                with connection.connect(profile) as conn:
                    results = verify_sps_with_refresh(conn)
                    if patterns:
                        results = tuple(
                            r for r in results
                            if not any(pat in r.object_name.lower() for pat in patterns)
                        )
                    failures = [r for r in results if not r.is_success]
                    if failures:
                        print(f"❌ Perfil '{profile.name}': {len(failures)} objeto(s) con errores de compilación:")
                        for f in failures:
                            print(f"   - [{f.schema_name}].[{f.object_name}]: {f.error_message}")
                    else:
                        print(f"✅ Perfil '{profile.name}': todos los procedimientos/vistas compilaron correctamente ({len(results)} verificados).")
            except Exception as exc:
                print(f"⚠️ Perfil '{profile.name}': no se pudo conectar o verificar SPs: {exc}")


def main(argv: list[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)
    profiles = load_profiles(args.config)
    if args.profiles:
        profiles = [p for p in profiles if p.name in args.profiles]

    exclude_patterns = list(args.exclude_tables or [])
    
    result = run_comparison(profiles, exclude_patterns)

    render_summary, do_generate = _resolve_summary_renderer_and_generate_reports(
        args.tui, profiles, exclude_patterns
    )
    if render_summary is not None:
        write_reports(result, render_summary=render_summary, generate_reports=do_generate)
    else:
        write_reports(result, generate_reports=do_generate)

    if args.verify_sps:
        _run_sp_verification(profiles, exclude_patterns=exclude_patterns)




if __name__ == "__main__":
    main()
