import re

SAFE_NAME_PATTERN = re.compile(r'[^A-Za-z0-9_]+')


def safe_name(s):
    return SAFE_NAME_PATTERN.sub('_', s).strip().lower()
