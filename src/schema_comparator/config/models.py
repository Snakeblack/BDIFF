"""Value object representing a named SQL Server connection profile."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConnectionProfile:
    """A named SQL Server connection profile.

    `connection_string` is an opaque ODBC string passed verbatim to a future
    pyodbc connector; it is NEVER parsed into host/user/password/auth
    fields, so both SQL authentication (`UID=...;PWD=...;`) and Windows
    integrated authentication (`Trusted_Connection=yes;`) are supported
    without this model branching on auth mode.
    """

    name: str
    connection_string: str

    def __repr__(self) -> str:
        # Defense-in-depth: redact the secret even if the object is logged
        # or interpolated with %r by an unrelated logger.
        return f"ConnectionProfile(name={self.name!r}, connection_string=<redacted>)"
