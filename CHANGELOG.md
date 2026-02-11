# CHANGELOG

## v0.8.0 (WIP)

> 📅 **Date** TBD

- 🆕 **New Features:**
  - **Oracle Database Support:**
    - Added support for Oracle Database using `DBMS_LOCK` package
    - Supports all 6 Oracle lock modes: `NL` (Null), `SS` (Sub-Shared), `SX` (Sub-Exclusive), `S` (Shared), `SSX` (Shared Sub-Exclusive), `X` (Exclusive)
    - Lock mode compatibility matrix for fine-grained concurrency control
    - Transaction-level locks via `release_on_commit` parameter
    - Integer lock IDs (0-1073741823) with automatic hash-based conversion for string keys (using blake2b)
    - Both synchronous and asynchronous lock implementations
  - **MSSQL (Microsoft SQL Server) Support:**
    - Added support for SQL Server application locks using `sp_getapplock`
    - Multiple lock modes: Exclusive, Shared, and Update
    - Both synchronous and asynchronous lock implementations
  - **MariaDB Support:**
    - Added explicit MariaDB registry entry (compatible with MySQL named locks)

- 🏗️ **Refactor:**
  - Refactored lock base classes to reduce code duplication between synchronous and asynchronous implementations
  - Extracted common lock state validation logic into base class methods
  - Introduced `do_acquire` and `do_release` abstract methods for concrete implementations
  - Added `@final` decorator to `acquire`, `release`, and `close` methods in base classes to prevent override while ensuring consistent behavior
  - Improved consistency between MySQL, PostgreSQL, MSSQL, and Oracle lock implementations

- 📦 **Dependencies:**
  - Added `oracledb>=2.0` as optional dependency for Oracle (recommended)
  - Added `cx_Oracle>=8.3` as optional dependency for Oracle (legacy)
  - Added `pyodbc` and `pymssql` as optional dependencies for MSSQL
  - Added `aioodbc` as optional dependency for MSSQL async

- 📚 **Documentation:**
  - Added comprehensive Oracle lock types documentation with examples
  - Added MSSQL lock types documentation with examples
  - Updated README with all supported databases and their lock mechanisms
  - Added connection string examples for Oracle and MSSQL
  - Added Oracle Free service to `db.docker-compose.yml` for testing

- ⚠️ **TODO (Before Release):**
  - Integration testing with Oracle Database (Docker)
  - Integration testing with MSSQL (Docker)

## v0.7.0

> 📅 **Date** 2025-10-12

- 🆕 **New Features:**
  - Supported Python 3.14
- 💔 **Breaking Changes:**
  - Drop support for Python 3.8
- 📦 **Build:**
  - Upgrade build backend to `setuptools>=80`
  - Remove all `requirements.txt` files

## v0.6.1.post2

> 📅 **Date** 2024-11-29

- 🐛 Bug-fix:
  - Issue #4: PostgreSQL xact lock in context manager produces warning #4
- ✅ Changes:
  - `typing-extensions` required for Python earlier than 3.12
- 🖊️ Modifications:
  - Add some `override` decorators
- 🎯 CI:
  - update pre-commit hooks

## v0.6.1

> 📅 **Date** 2024-4-6

- ✅ Changes:
  - `typing-extensions` required for Python earlier than 3.10

## v0.6

> 📅 **Date** 2024-3-28

- ❎ Breaking Changes:
  - Remove `level` arguments of PostgreSQL lock class' constructor.
    `xact` and `shared` arguments were added.
- 🆕 New Features:
  - support `transaction` and `shared` advisory lock for PostgreSQL.
- 🐛 Bug fix:
  - PostgreSQL transaction level advisory locks are held until the current transaction ends.
    Manual release for that is disabled, and a warning message will be printed.
- 🕐 Optimize
  - Reduce duplicated codes
  - Better unit tests

## v0.5.3

> 📅 **Date** 2024-3-15

## v0.5

Date: 2023-12-06

- New:
  - `contextual_timeout` parameter for “with” statement
  - Support Python 3.12

## v0.4

Date: 2023-06-17

- Remove:
  - remove `acquired` property, it's alias of `locked`
  - remove setter of `locked` property

- Optimize:
  - re-arrange package's structure
  - Many optimizations

- CI/Test:
  - GitHub action: Python 3.8~3.11 x SQLAlchemy 1.x/2.x matrix testing
  - Local compose: Python 3.7~3.11 x SQLAlchemy 1.x/2.x matrix testing

- Doc: Update to Sphinx 7.x, and Furo theme

## v0.3.1

Date: 2023-06-13

- A hotfix for project's dependencies setup error.

## v0.3

Date: 2023-06-13

- Remove:
  - Python 3.6 support

- Tests:
  - New docker compose based tests, from python 3.7 to 3.11, both SQLAlchemy 1.x and 2.x

- Docs:
  - Update to newer Sphinx docs

- Build:
  - Move all project meta to pyproject.toml, remove setup.cfg and setup.py

## v0.2.1

Date: 2023-02-25

- New:
  - support SQLAlchemy 2.0

## v0.2

Date: 2021-03-23

First v0.2.x version released.

## v0.2b2/b3

Date: 2021-03-23

- Add:
  - More unit tests
  - Optimized CI

## v0.2b1

Date: 2021-03-16

- Add:

  - New unit tests
  - CI by GitHub workflows

## v0.2a3

Date: 2021-03-14

- Change:

  - Drop Python 3.5 support.
  - Remove SQLAlchemy version requires earlier than 1.4 in setup, it's not supported, actually.
  - Adjust PostgreSQL lock's constructor arguments order

- Add:

  - More test cases, and add test/deploy workflow in GitHub actions.
  - Add docker-compose test scripts

## v0.2a2

Date: 2021-03-09

- Change:

  - Rename a lot of function/class:

    - `sadlock` -> `create_sadlock`
    - `asyncio.sadlock` -> `asyncio.create_async_sadlock`

    and some other ...

## v0.2a1

Date: 2021-03-08

- New:

  - Asynchronous IO Support by:

    - [aiomysql](https://github.com/aio-libs/aiomysql) for MySQL

      Connection URL is like: `"mysql+aiomysql://user:password@host:3306/schema?charset=utf8mb4"`

    - [asyncpg](https://github.com/MagicStack/asyncpg) for PostgreSQL

      Connection URL is like: `"PostgreSQL+asyncpg://user:password@host:5432/db"`

    Read <https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html> for details

## v0.1.2

Date: 2021-01-26

Still an early version, not for production.

- Changes:
  - Arguments and it's default value of `acquire` now similar to stdlib's `multiprossing.Lock`, instead of `Threading.Lock`
  - MySQL lock now accepts float-point value as `timeout`
- Adds
  - Several new test cases
- Other
  - Many other small adjustment

## v0.1.1

- A very early version, maybe not stable enough.
- Replace `black2b` with crc64-iso in PostgreSQL key convert function
- Only named arguments as extra parameters allowed in Lock's implementation class
