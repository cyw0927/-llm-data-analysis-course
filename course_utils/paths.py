
from pathlib import Path

def get_project_root():
    current = Path.cwd().resolve()
    project_root = current

    while True:
        if (current / "data").is_dir():
            project_root = current
            break
        current = current.parent

    return project_root


def get_data_dir():
    return get_project_root() / "data"