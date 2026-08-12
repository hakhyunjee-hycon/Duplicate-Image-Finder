import os
from typing import List, Dict, Tuple
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTreeWidget, QTreeWidgetItem, QProgressBar, QMessageBox,
    QFileDialog, QInputDialog, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

class MainView(QMainWindow):
    """
    중복 이미지 관리 메인 윈도우 UI
    """
    # Signals for Presenter
    scan_requested = pyqtSignal(str)          # Root 폴더 경로
    cancel_scan_requested = pyqtSignal()
    delete_requested = pyqtSignal(list)       # 삭제할 파일 경로 리스트
    rename_requested = pyqtSignal(str, str)    # (이름 변경할 파일 경로, 새 파일명)
    item_double_clicked = pyqtSignal(str, list) # (더블클릭한 파일경로, 해당 그룹 전체 파일경로 리스트)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("중복 이미지 검사 및 관리 프로그램 (MVP Architecture)")
        self.resize(1000, 650)
        self._init_ui()

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # 1. Root 폴더 선택 바
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Root 폴더:"))
        
        self.txt_root = QLineEdit()
        self.txt_root.setPlaceholderText("검사할 이미지 Root 폴더 경로를 선택하세요...")
        folder_layout.addWidget(self.txt_root)

        self.btn_browse = QPushButton("폴더 선택...")
        self.btn_browse.clicked.connect(self._on_browse_folder)
        folder_layout.addWidget(self.btn_browse)

        self.btn_scan = QPushButton("중복 이미지 스캔 시작")
        self.btn_scan.setStyleSheet("font-weight: bold; background-color: #007acc; color: white; padding: 6px 12px;")
        self.btn_scan.clicked.connect(self._on_scan_clicked)
        folder_layout.addWidget(self.btn_scan)

        main_layout.addLayout(folder_layout)

        # 2. 진행 상태 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("준비됨")
        self.lbl_status.setFont(QFont("Malgun Gothic", 9))
        main_layout.addWidget(self.lbl_status)

        # 3. 중복 이미지 Tree/Table 리스트업 UI (멀티셀렉트 가능)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["파일명 / 경로", "파일 크기", "수정 날짜"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection) # 멀티셀렉트 지원!
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        main_layout.addWidget(self.tree, stretch=1)

        # 4. 하단 액션 버튼들 (삭제, Rename)
        action_layout = QHBoxLayout()
        
        self.lbl_selected_count = QLabel("선택된 항목: 0개")
        action_layout.addWidget(self.lbl_selected_count)

        action_layout.addStretch(1)

        self.btn_rename = QPushButton("파일명 변경 (Rename)")
        self.btn_rename.clicked.connect(self._on_rename_clicked)
        action_layout.addWidget(self.btn_rename)

        self.btn_delete = QPushButton("선택 파일 삭제 (Delete)")
        self.btn_delete.setStyleSheet("background-color: #d9534f; color: white; font-weight: bold;")
        self.btn_delete.clicked.connect(self._on_delete_clicked)
        action_layout.addWidget(self.btn_delete)

        main_layout.addLayout(action_layout)

        # 선택 항목 변경 이벤트 동기화
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)

    def _on_browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "이미지 Root 폴더 선택")
        if folder:
            self.txt_root.setText(folder)

    def _on_scan_clicked(self):
        path = self.txt_root.text().strip()
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "경고", "유효한 Root 폴더 경로를 입력하세요.")
            return
        self.scan_requested.emit(path)

    def _on_selection_changed(self):
        selected_items = self.tree.selectedItems()
        # 파일 노드만 카운트 (그룹 노드 제외)
        file_count = sum(1 for item in selected_items if item.data(0, Qt.ItemDataRole.UserRole) is not None)
        self.lbl_selected_count.setText(f"선택된 항목: {file_count}개")

    def _on_delete_clicked(self):
        selected_items = self.tree.selectedItems()
        file_paths = []
        for item in selected_items:
            path = item.data(0, Qt.ItemDataRole.UserRole)
            if path and os.path.exists(path):
                file_paths.append(path)

        if not file_paths:
            QMessageBox.warning(self, "경고", "삭제할 파일을 1개 이상 선택하세요.")
            return

        reply = QMessageBox.question(
            self, "확인", f"선택한 {len(file_paths)}개 파일을 정말 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.delete_requested.emit(file_paths)

    def _on_rename_clicked(self):
        selected_items = self.tree.selectedItems()
        file_paths = [
            item.data(0, Qt.ItemDataRole.UserRole)
            for item in selected_items if item.data(0, Qt.ItemDataRole.UserRole) is not None
        ]

        if len(file_paths) != 1:
            QMessageBox.warning(self, "경고", "이름 변경은 단 1개의 파일만 선택했을 때 진행할 수 있습니다.")
            return

        target_path = file_paths[0]
        old_name = os.path.basename(target_path)

        new_name, ok = QInputDialog.getText(
            self, "파일명 변경", "새 파일 이름을 입력하세요:", QLineEdit.EchoMode.Normal, old_name
        )
        if ok and new_name.strip() and new_name.strip() != old_name:
            self.rename_requested.emit(target_path, new_name.strip())

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        if not file_path:
            # 그룹 헤더 항목을 더블클릭한 경우 펼치기/접기
            item.setExpanded(not item.isExpanded())
            return

        # 부모 그룹의 모든 파일 경로 수집
        parent_group = item.parent()
        group_files = []
        if parent_group:
            for i in range(parent_group.childCount()):
                child = parent_group.child(i)
                cp = child.data(0, Qt.ItemDataRole.UserRole)
                if cp:
                    group_files.append(cp)

        self.item_double_clicked.emit(file_path, group_files)

    def update_status(self, text: str):
        self.lbl_status.setText(text)

    def update_progress(self, current: int, total: int, message: str):
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.lbl_status.setText(message)

    def finish_progress(self, message: str):
        self.progress_bar.setVisible(False)
        self.lbl_status.setText(message)

    def display_duplicate_groups(self, groups: Dict[str, List[str]]):
        """중복 그룹 트리 렌더링"""
        self.tree.clear()

        group_index = 1
        total_duplicates = 0
        for hash_val, paths in groups.items():
            if len(paths) < 2:
                continue

            # 그룹 노드 생성
            group_node = QTreeWidgetItem(self.tree)
            group_node.setText(0, f"그룹 #{group_index} (중복 {len(paths)}개) - Hash: {hash_val[:8]}...")
            group_node.setFont(0, QFont("Malgun Gothic", 10, QFont.Weight.Bold))
            group_node.setExpanded(True)

            for path in paths:
                child = QTreeWidgetItem(group_node)
                child.setText(0, path)
                child.setData(0, Qt.ItemDataRole.UserRole, path)

                if os.path.exists(path):
                    size_kb = os.path.getsize(path) / 1024.0
                    mtime = os.path.getmtime(path)
                    import datetime
                    mtime_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                    child.setText(1, f"{size_kb:.1f} KB")
                    child.setText(2, mtime_str)
                else:
                    child.setText(1, "N/A")
                    child.setText(2, "N/A")

                total_duplicates += 1

            group_index += 1

        self.finish_progress(f"스캔 완료: 총 {group_index - 1}개 중복 그룹, {total_duplicates}개 중복 파일 발견.")
