# CHANGELOG

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
