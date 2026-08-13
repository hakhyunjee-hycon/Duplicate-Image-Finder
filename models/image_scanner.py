import os
import hashlib
from typing import Callable, Dict, List, Optional

SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff', '.gif'}

class ImageScanner:
    """
    Root 디렉토리를 재귀 스캔하여 파일 크기 및 MD5 해시 기반으로 중복 이미지들을 탐지하는 서비스 클래스
    """
    def __init__(self, chunk_size: int = 65536):
        self.chunk_size = chunk_size
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def is_cancelled(self) -> bool:
        """스캔이 취소되었는지 여부를 반환합니다."""
        return self._is_cancelled

    def calculate_file_hash(self, filepath: str) -> Optional[str]:
        """파일의 MD5 해시값을 계산합니다."""
        hasher = hashlib.md5()
        try:
            with open(filepath, 'rb') as f:
                while chunk := f.read(self.chunk_size):
                    if self._is_cancelled:
                        return None
                    hasher.update(chunk)
            return hasher.hexdigest()
        except (OSError, PermissionError):
            return None

    def scan_directory(
        self,
        root_dir: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, List[str]]:
        """
        Root 폴더 내의 이미지를 탐색하고 중복된 파일 경로 그룹을 반환합니다.
        반환 형태: { 'hash_string': ['/path/to/img1.png', '/path/to/img2.png'], ... }
        """
        self._is_cancelled = False
        size_to_files: Dict[int, List[str]] = {}

        # 1. 파일 탐색 및 크기별 1차 그룹화
        all_image_paths: List[str] = []
        for dirpath, _, filenames in os.walk(root_dir):
            if self._is_cancelled:
                return {}
            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    full_path = os.path.join(dirpath, filename)
                    all_image_paths.append(full_path)

        total_files = len(all_image_paths)
        for idx, filepath in enumerate(all_image_paths):
            if self._is_cancelled:
                return {}
            if progress_callback:
                progress_callback(idx + 1, total_files, f"1/2단계: 파일 크기 분석 중... ({idx+1}/{total_files})")
            
            try:
                size = os.path.getsize(filepath)
                if size > 0:
                    size_to_files.setdefault(size, []).append(filepath)
            except (OSError, PermissionError):
                continue

        # 파일 크기가 동일하여 중복 가능성이 있는 파일 리스트 수집
        candidate_paths: List[str] = []
        for files in size_to_files.values():
            if len(files) > 1:
                candidate_paths.extend(files)

        # 2. 해시 계산 및 최종 중복 그룹화
        hash_to_files: Dict[str, List[str]] = {}
        total_candidates = len(candidate_paths)
        for idx, filepath in enumerate(candidate_paths):
            if self._is_cancelled:
                return {}
            if progress_callback:
                progress_callback(idx + 1, total_candidates, f"2/2단계: 바이너리 해시 비교 중... ({idx+1}/{total_candidates})")
            
            file_hash = self.calculate_file_hash(filepath)
            if file_hash:
                hash_to_files.setdefault(file_hash, []).append(filepath)

        # 2개 이상 중복된 그룹만 필터링
        duplicate_groups = {h: paths for h, paths in hash_to_files.items() if len(paths) > 1}
        return duplicate_groups
