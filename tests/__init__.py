import logging
import sys

logging.basicConfig(
    # level=logging.DEBUG,
    stream=sys.stderr,
    format="%(asctime)s [%(levelname).1s] %(name)s %(message)s",
)
