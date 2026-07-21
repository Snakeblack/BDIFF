"""MySQL & MariaDB connection context manager."""

from contextlib import contextmanager
from typing import Any, Generator

from schema_comparator.config.models import ConnectionProfile


@contextmanager
def connect(profile: ConnectionProfile, **kwargs: Any) -> Generator[Any, None, None]:
    """Establish connection to MySQL / MariaDB using pymysql driver."""
    try:
        import pymysql
    except ImportError as exc:
        raise ImportError(
            "pymysql es necesario para conectar a MySQL/MariaDB. Instálalo con 'pip install pymysql' "
            "o 'pip install bdiff[mysql]'."
        ) from exc

    conn_args = {
        "host": kwargs.get("host", "localhost"),
        "port": kwargs.get("port", 3306),
        "user": kwargs.get("user", "root"),
        "password": kwargs.get("password", ""),
        "database": kwargs.get("database"),
        "charset": kwargs.get("charset", "utf8mb4"),
    }
    # Filter out None values
    conn_args = {k: v for k, v in conn_args.items() if v is not None}

    conn = pymysql.connect(**conn_args)
    try:
        yield conn
    finally:
        conn.close()
