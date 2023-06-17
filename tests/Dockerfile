# build a base python image for multiple-version tests

ARG PYTHON_VERSION
FROM python:$PYTHON_VERSION
ARG APT_SOURCES
RUN --mount=type=cache,target=/var/cache/apt \
    if [ -n "${APT_SOURCES}" ]; then printenv APT_SOURCES | tee /etc/apt/sources.list; fi && \
    apt-get -o Acquire::Check-Valid-Until=false update && \
    apt-get install -y default-mysql-client postgresql-client default-libmysqlclient-dev libpq-dev
