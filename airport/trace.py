# TRACE mode: when ENABLED is True, the algorithms print what they are doing
# (hash probes, BST paths and neighbours, sorting passes). Used for the interview.
ENABLED = False


def log(message):
    if ENABLED:
        print("   [trace]", message)
