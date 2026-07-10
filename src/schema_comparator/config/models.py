"""Value object representing a named SQL Server connection profile."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConnectionProfile:
    """A named SQL Server connection profile.

    `connection_string` is an ODBC connection string passed verbatim to a
    future pyodbc connector. Any ADO.NET/`SqlClient`-style keyword present
    in the original YAML value is translated to its ODBC equivalent once,
    at config-load time (see `config/connection_string.py`), before this
    object is constructed. This model still never decomposes the string
    into separate host/user/password/auth-mode fields, so both SQL
    authentication (`UID=...;PWD=...;`) and Windows integrated
    authentication (`Trusted_Connection=yes;`) are supported without this
    model branching on auth mode.
    """

    name: str
    connection_string: str

    def __repr__(self) -> str:
        # Defense-in-depth: redact the secret even if the object is logged
        # or interpolated with %r by an unrelated logger.
        return f"ConnectionProfile(name={self.name!r}, connection_string=<redacted>)"
