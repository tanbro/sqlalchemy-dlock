# Tests

## Run tests in docker-compose

In `tests` directory, run:

```bash
docker-compose up
```

Wait all containers startup. Run following command in another terminal:

```bash
docker-compose run --rm --entrypoint /bin/bash python tests/run.sh
```
