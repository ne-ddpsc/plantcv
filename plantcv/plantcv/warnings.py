# Warnings handling

import sys

def warnings(warning):
    """Print out warning message

    Inputs:
    warning = warning message text

    :param warning: str
    """
    print(warning, file=sys.stderr)
