# Schema Comparator

Compara esquemas de SQL Server entre varias bases de microservicios
(dominio seguros) y detecta drift: tablas/columnas faltantes, tipos o
tamaños distintos, columnas renombradas. Genera reportes HTML/PDF/Excel
y un resumen de consola; opcionalmente un TUI interactivo (`--tui`).

## Quick start (zero-setup)

No hace falta crear el virtualenv a mano. Con cualquier intérprete
Python 3.11+ instalado, corré directamente:

```bash
python run.py --config config.local.yaml --tui
```

(`py run.py ...` o `python3 run.py ...` funcionan igual). La primera vez,
`run.py` crea `.venv` en la raíz del repo, instala el proyecto dentro
(`pip install -e .`) y relanza el CLI. Las siguientes ejecuciones detectan
que `.venv` ya está listo y arrancan el CLI directamente, sin reinstalar
nada. Si `.venv` se borra o queda a medio provisionar, `run.py` lo vuelve
a crear automáticamente la próxima vez.

Todos los argumentos que le pases a `run.py` se reenvían sin modificar al
CLI real (`--config`, `--profiles`, `--tui`, `--exclude-tables`, etc.), y
el código de salida del CLI se propaga sin cambios.

Antes de correrlo, copiá `config.example.yaml` a `config.local.yaml` y
completá tus cadenas de conexión reales (ese archivo está en
`.gitignore`, nunca se commitea).

### Alternativa: `uv run` / `pipx run`

Si ya tenés [`uv`](https://github.com/astral-sh/uv) o `pipx` instalados,
también podés usarlos para correr el CLI sin gestionar el venv vos mismo
(por ejemplo `uv run schema-comparator --config config.local.yaml`). Esto
es solo una alternativa para quien ya tenga esas herramientas; `run.py`
sigue siendo el mecanismo principal recomendado, ya que no requiere tener
nada instalado más allá de un Python del sistema.

## Instalación manual (alternativa a `run.py`)

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e .
python -m schema_comparator.cli --config config.local.yaml
```

## Desarrollo

```bash
pip install -e ".[dev]"
pytest
```
