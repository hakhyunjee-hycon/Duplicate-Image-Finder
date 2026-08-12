from typing import List, Dict
from PyQt6.QtCore import QObject, QThread, pyqtSignal

from models.image_scanner import ImageScanner
from models.duplicate_model import DuplicateModel
from views.main_view import MainView
from presenters.preview_presenter import PreviewPresenter


class ScanWorker(QObject):
    """
    백그라운드 스레드에서 이미지 중복 스캔을 수행하는 Worker
    """
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(dict)

    def __init__(self, root_dir: str):
        super().__init__()
        self.root_dir = root_dir
        self.scanner = ImageScanner()

    def run(self):
        groups = self.scanner.scan_directory(
            self.root_dir,
            progress_callback=lambda cur, tot, msg: self.progress.emit(cur, tot, msg)
        )
        self.finished.emit(groups)

    def cancel(self):
        self.scanner.cancel()


class MainPresenter(QObject):
    """
    MainView와 DuplicateModel 간의 사용자 상호작용 및 이벤트 제어를 담당하는 Main Presenter
    """
    def __init__(self, view: MainView, model: DuplicateModel):
        super().__init__()
        self.view = view
        self.model = model
        self.preview_presenter = PreviewPresenter(parent_view=self.view)

        self._scan_thread = None
        self._scan_worker = None

        # Connect View Signals
        self.view.scan_requested.connect(self.start_scan)
        self.view.delete_requested.connect(self.delete_files)
        self.view.rename_requested.connect(self.rename_file)
        self.view.item_double_clicked.connect(self.open_preview)

    def start_scan(self, root_dir: str):
        """스캔 스레드를 시작합니다."""
        self.view.btn_scan.setEnabled(False)
        self.view.update_status("스캔 준비 중...")

        self._scan_thread = QThread()
        self._scan_worker = ScanWorker(root_dir)
        self._scan_worker.moveToThread(self._scan_thread)

        self._scan_thread.started.connect(self._scan_worker.run)
        self._scan_worker.progress.connect(self.view.update_progress)
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.finished.connect(self._scan_thread.quit)
        self._scan_worker.finished.connect(self._scan_worker.deleteLater)
        self._scan_thread.finished.connect(self._scan_thread.deleteLater)

        self._scan_thread.start()

    def _on_scan_finished(self, groups: Dict[str, List[str]]):
        self.view.btn_scan.setEnabled(True)
        self.model.set_duplicate_groups(groups)
        self.view.display_duplicate_groups(groups)

    def delete_files(self, file_paths: List[str]):
        """선택된 파일 삭제 처리"""
        deleted, failed = self.model.delete_files(file_paths)
        updated_groups = self.model.get_duplicate_groups()
        self.view.display_duplicate_groups(updated_groups)

        if failed:
            msg = f"삭제 완료: {len(deleted)}개 성공, {len(failed)}개 실패."
        else:
            msg = f"삭제 완료: {len(deleted)}개 파일이 성공적으로 삭제되었습니다."
        self.view.update_status(msg)

    def rename_file(self, old_path: str, new_name: str):
        """단일 파일 이름 변경 처리"""
        success, new_path, message = self.model.rename_file(old_path, new_name)
        if success:
            updated_groups = self.model.get_duplicate_groups()
            self.view.display_duplicate_groups(updated_groups)
            self.view.update_status(f"이름 변경 성공: {new_name}")
        else:
            self.view.update_status(f"오류: {message}")

    def open_preview(self, current_file: str, group_files: List[str]):
        """Preview Popup 띄우기"""
        self.preview_presenter.show_preview(current_file, group_files)
