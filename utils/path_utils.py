import os
from pathlib import Path

def get_last_two_depths(file_path: str) -> str:
    """
    파일 경로에서 마지막 2개의 디렉토리 depth를 추출합니다.
    예: C:/Path/To/FolderA/FolderB/image.png -> "FolderA/FolderB"
    디렉토리 depth가 2 미만인 경우 가능한 디렉토리 경로만 반환합니다.
    """
    path = Path(file_path)
    parent = path.parent
    parts = parent.parts
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    # 드라이브 루트(예: 'C:\\')가 포함될 경우 조율
    last_two = parts[-2:]
    return os.path.join(*last_two)
