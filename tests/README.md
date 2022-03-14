# Tests

## Run tests in docker-compose

Just `up` the docker-compose in `tests` directory:

```bash
(cd tests; docker-compose up --exit-code-from pytest; docker-compose down;)
```
