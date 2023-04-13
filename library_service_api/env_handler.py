import os


def env_custom_value_or_none(variable: str):
    """
    Checks if user provided custom values to env variables.
    Makes variable equal None if user didn't change default value.
    """
    value = os.environ[variable]
    if variable == value:
        return None
    return value
