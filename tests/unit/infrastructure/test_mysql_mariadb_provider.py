"""Unit tests for MySQL and MariaDB providers."""

from schema_comparator.config.models import ConnectionProfile
from schema_comparator.domain.comparison.models import ColumnAttributes
from schema_comparator.infrastructure.providers.mariadb import MariaDbProvider
from schema_comparator.infrastructure.providers.mysql import MySqlProvider
from schema_comparator.infrastructure.providers.mysql_family.ddl_renderer import (
    format_mysql_column_definition,
    generate_mysql_script,
    quote_identifier,
)
from schema_comparator.infrastructure.providers.mysql_family.introspector import build_snapshot
from schema_comparator.infrastructure.providers.registry import get_default_registry


def test_mysql_and_mariadb_registration():
    registry = get_default_registry()
    assert "mysql" in registry.list_providers()
    assert "mariadb" in registry.list_providers()

    mysql_p = registry.require("mysql")
    assert isinstance(mysql_p, MySqlProvider)
    assert mysql_p.provider_id == "mysql"

    mariadb_p = registry.require("mariadb")
    assert isinstance(mariadb_p, MariaDbProvider)
    assert mariadb_p.provider_id == "mariadb"


def test_mysql_capabilities():
    p = MySqlProvider()
    caps = p.capabilities()
    assert caps.provider_id == "mysql"
    assert caps.supports_drop_column is True
    assert caps.supports_alter_column is True


def test_quote_identifier():
    assert quote_identifier("users") == "`users`"
    assert quote_identifier("user`name") == "`user``name`"


def test_introspector_build_snapshot():
    rows = [
        ("app_db", "users", "id", "int", None, 10, 0, "NO", 1, None, "auto_increment", None),
        ("app_db", "users", "email", "varchar", 255, None, None, "YES", 2, None, "", "utf8mb4_unicode_ci"),
    ]
    snapshot = build_snapshot("mysql_profile", rows)
    assert snapshot.profile_name == "mysql_profile"
    assert len(snapshot.tables) == 1
    t = snapshot.tables[0]
    assert t.table_name == "users"
    assert len(t.columns) == 2
    assert t.columns[0].name == "id"
    assert t.columns[0].is_identity is True
    assert t.columns[1].name == "email"
    assert t.columns[1].is_nullable is True


def test_generate_mysql_script():
    profile = ConnectionProfile(name="dev_mysql", connection_string="Server=localhost;", provider="mysql")
    col_attrs = ColumnAttributes(
        data_type="varchar",
        character_maximum_length=100,
        numeric_precision=None,
        numeric_scale=None,
        is_nullable=False,
    )
    missing_tables = [
        ("app_db", "orders", [("id", ColumnAttributes(data_type="int", character_maximum_length=None, numeric_precision=10, numeric_scale=0, is_nullable=False))]),
    ]
    missing_cols = [("app_db", "users", "age", ColumnAttributes(data_type="int", character_maximum_length=None, numeric_precision=10, numeric_scale=0, is_nullable=True))]
    discrepant_cols = [
        (
            "app_db",
            "users",
            "email",
            ColumnAttributes(data_type="varchar", character_maximum_length=50, numeric_precision=None, numeric_scale=None, is_nullable=True),
            col_attrs,
        )
    ]

    script = generate_mysql_script(profile, missing_tables, missing_cols, discrepant_cols)
    assert "CREATE TABLE IF NOT EXISTS `app_db`.`orders`" in script
    assert "ALTER TABLE `app_db`.`users` ADD COLUMN `age` int NULL;" in script
    assert "ALTER TABLE `app_db`.`users` MODIFY COLUMN `email` varchar(100) NOT NULL;" in script
    assert "SET FOREIGN_KEY_CHECKS = 0;" in script
