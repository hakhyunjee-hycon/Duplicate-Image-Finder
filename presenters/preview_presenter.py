from typing import List
from views.preview_dialog import PreviewDialog

class PreviewPresenter:
    """
    Preview Popup Dialog와 데이터간의 비즈니스 로직을 연결하는 Presenter
    """
    def __init__(self, parent_view=None):
        self.parent_view = parent_view
        self.dialog = None

    def show_preview(self, current_file: str, group_files: List[str]):
        """이미지 preview popup을 생성하고 엽니다."""
        if not group_files:
            group_files = [current_file]

        try:
            current_index = group_files.index(current_file)
        except ValueError:
            current_index = 0

        self.dialog = PreviewDialog(file_paths=group_files, current_index=current_index, parent=self.parent_view)
        self.dialog.exec()
