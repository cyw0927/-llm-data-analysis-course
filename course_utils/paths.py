from pathlib import Path


def get_project_root():
    current = Path(__file__).resolve().parent

    while current != current.parent:
        if (current / "data").is_dir():
            return current

        current = current.parent

    raise FileNotFoundError("프로젝트 루트를 찾을 수 없습니다.")


def get_data_dir():
    return get_project_root() / "data"