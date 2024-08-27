import asyncio
import platform

# Psycopg cannot use the 'ProactorEventLoop' to run in async mode.
# use a compatible event loop, for instance by setting 'asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())'
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy()) # type: ignore[attr-defined]
