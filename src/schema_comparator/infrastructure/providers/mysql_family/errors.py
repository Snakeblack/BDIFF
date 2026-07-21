"""Exception translation for MySQL and MariaDB providers."""

from schema_comparator.discovery.errors import ConnectionFailedError, MetadataAccessError


def translate_connect_error(profile_name: str, exc: Exception) -> ConnectionFailedError:
    """Translate driver connect error into standard ConnectionFailedError."""
    return ConnectionFailedError(
        f"Fallo al conectar con el servidor MySQL/MariaDB en el perfil '{profile_name}': {exc}"
    )


def translate_query_error(profile_name: str, exc: Exception) -> MetadataAccessError:
    """Translate catalog query error into standard MetadataAccessError."""
    return MetadataAccessError(
        f"Error ejecutando consulta de catálogo MySQL/MariaDB en el perfil '{profile_name}': {exc}"
    )

