# CHANGELOG

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
  - CI by github workflows

## v0.2a3

Date: 2021-03-14

- Change:

  - Drop Python 3.5 support.
  - Remove SQLAlchemy version requires earlier than 1.4 in setup, it's not supported actually.
  - Adjust PostgreSQL lock's constructor arguments order

- Add:

  - More test cases, and add test/deploy workflow in github actions.
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

      Connection URL is like: `"postgresql+asyncpg://user:password@host:5432/db"`

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
- Replace black2b with crc64-iso in PostgreSQL key convert function
- Only named arguments as extra parameters allowed in Lock's implementation class
