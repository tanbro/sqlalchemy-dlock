# build a base python image for multiple-version tests

FROM quay.io/pypa/manylinux_2_28_x86_64
RUN --mount=type=cache,target=/var/cache/dnf \
    dnf install -y \
    curl \
    mysql mysql-devel \
    postgresql libpq-devel \
    unixODBC unixODBC-devel && \
    curl -fsSL https://packages.microsoft.com/config/rhel/8/prod.repo \
        -o /etc/yum.repos.d/mssql-release.repo && \
    ACCEPT_EULA=Y dnf install -y msodbcsql18
