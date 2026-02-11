# build a base python image for multiple-version tests

FROM quay.io/pypa/manylinux_2_28_x86_64
RUN --mount=type=cache,target=/var/cache/dnf \
    dnf install -y \
    mysql mysql-devel \
    postgresql libpq-devel \
    unixODBC unixODBC-devel
