# Specification: MySQL and MariaDB Provider

## Feature: MySQL & MariaDB Schema Discovery and DDL Rendering

### Scenario: Introspect MySQL schema tables and columns
Given a MySQL database connection profile
When schema discovery is requested for a database target
Then `MySqlProvider` MUST query `information_schema.tables` and `information_schema.columns`
And return a `SchemaSnapshot` with table and column definitions including data types, nullability, and primary key metadata.

### Scenario: Introspect MariaDB schema tables and columns
Given a MariaDB database connection profile
When schema discovery is requested for a database target
Then `MariaDbProvider` MUST query `information_schema.tables` and `information_schema.columns`
And return a `SchemaSnapshot` compatible with BDIFF comparison engine.

### Scenario: Quoting identifiers with backticks
Given column or table names needing quotation
When generating DDL or queries for MySQL or MariaDB
Then identifiers MUST be enclosed in backticks (e.g. `` `user_id` ``).

### Scenario: Generate DDL migration statements
Given schema drift findings targeting MySQL or MariaDB
When DDL consolidation script generation is requested
Then missing columns MUST generate `ALTER TABLE `table` ADD COLUMN `col` TYPE NULLABILITY`
And modified column types MUST generate `ALTER TABLE `table` MODIFY COLUMN `col` TYPE NULLABILITY`.
