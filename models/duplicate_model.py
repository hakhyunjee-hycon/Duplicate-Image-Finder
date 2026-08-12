import os
from typing import Dict, List, Tuple

class DuplicateModel:
    """
    중복 이미지 스캔 결과 데이터를 보관하고, 삭제 및 이름 변경 등의 파일 I/O 처리를 담당하는 데이터 모델
    """
    def __init__(self):
        # { group_id (str): [filepath_1, filepath_2, ...] }
        self._duplicate_groups: Dict[str, List[str]] = {}

    def set_duplicate_groups(self, groups: Dict[str, List[str]]):
        """스캔 결과를 모델에 설정합니다."""
        self._duplicate_groups = groups

    def get_duplicate_groups(self) -> Dict[str, List[str]]:
        return self._duplicate_groups

    def get_group_files(self, group_id: str) -> List[str]:
        return self._duplicate_groups.get(group_id, [])

    def delete_files(self, file_paths: List[str]) -> Tuple[List[str], List[Tuple[str, str]]]:
        """
        선택된 파일 목록을 디스크에서 삭제하고 모델을 갱신합니다.
        반환: (성공한 파일 목록, [(실패 파일, 오류 메시지)])
        """
        deleted: List[str] = []
        failed: List[Tuple[str, str]] = []

        for path in file_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
                deleted.append(path)
            except Exception as e:
                failed.append((path, str(e)))

        # 모델 갱신: 삭제된 파일 제거
        for group_id in list(self._duplicate_groups.keys()):
            current_list = self._duplicate_groups[group_id]
            updated_list = [p for p in current_list if p not in deleted]
            if len(updated_list) <= 1:
                # 남아있는 파일이 1개 이하가 되면 중복 그룹 해제
                del self._duplicate_groups[group_id]
            else:
                self._duplicate_groups[group_id] = updated_list

        return deleted, failed

    def rename_file(self, old_path: str, new_name: str) -> Tuple[bool, str, str]:
        """
        단일 파일의 이름을 변경합니다.
        반환: (성공여부, 새로운 파일 경로, 메시지)
        """
        if not os.path.exists(old_path):
            return False, old_path, "원본 파일이 존재하지 않습니다."

        dir_name = os.path.dirname(old_path)
        new_path = os.path.join(dir_name, new_name)

        if os.path.exists(new_path) and old_path != new_path:
            return False, old_path, "동일한 이름의 파일이 이미 존재합니다."

        try:
            os.rename(old_path, new_path)
            # 모델 내부 경로 업데이트
            for group_id, paths in self._duplicate_groups.items():
                if old_path in paths:
                    idx = paths.index(old_path)
                    paths[idx] = new_path
            return True, new_path, "성공적으로 변경되었습니다."
        except Exception as e:
            return False, old_path, f"이름 변경 실패: {str(e)}"
