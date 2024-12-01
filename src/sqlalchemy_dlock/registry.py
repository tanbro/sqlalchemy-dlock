REGISTRY = {
    "mysql": {
        "module": ".lock.mysql",
        "package": "${package}",  # module name relative to the package
        "class": "MysqlSadLock",
    },
    "postgresql": {
        "module": ".lock.postgresql",
        "package": "${package}",  # module name relative to the package
        "class": "PostgresqlSadLock",
    },
}

ASYNCIO_REGISTRY = {
    "mysql": {
        "module": ".lock.mysql",
        "package": "${package}",  # module name relative to the package
        "class": "MysqlAsyncSadLock",
    },
    "postgresql": {
        "module": ".lock.postgresql",
        "package": "${package}",  # module name relative to the package
        "class": "PostgresqlAsyncSadLock",
    },
}
