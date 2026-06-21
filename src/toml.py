import sys

try:
    from tomllib import *  # type: ignore
except ImportError:
    try:
        from tomli import *  # type: ignore
    except ImportError:
        print("error: please install 'tomli' or use Python 3.11+", file=sys.stderr)
        sys.exit(1)
