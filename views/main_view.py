import os
import datetime
from typing import List, Dict, Tuple
from PIL import Image

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTreeWidget, QTreeWidgetItem, QProgressBar, QMessageBox,
    QFileDialog, QInputDialog, QHeaderView, QAbstractItemView, QSplitter,
    QGroupBox, QFrame, QSizePolicy, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QVariantAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QPixmap, QImage, QPainter

from utils.path_utils import get_last_two_depths


class AspectLabel(QLabel):
    """
    이미지를 비율에 맞춰 캔버스 영역 내에만 축소/확대 렌더링하며,
    setPixmap() 호출 시 sizeHint() 확장에 의한 레이아웃 커짐 현상을 원천 방지하는 커스텀 라벨
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None

    def set_preview_pixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self.update()

    def clear_preview(self):
        self._pixmap = None
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._pixmap and not self._pixmap.isNull():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = self.contentsRect()
            if rect.width() > 0 and rect.height() > 0:
                scaled = self._pixmap.scaled(
                    rect.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                x = rect.x() + (rect.width() - scaled.width()) // 2
                y = rect.y() + (rect.height() - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)


class MainView(QMainWindow):
    """
    중복 이미지 관리 메인 윈도우 UI
    - 전체 선택 체크박스
    - 그룹 전수 삭제 시 안전 경고 팝업
    - 크기 커짐 방지 소형 이미지 미리보기 캔버스
    - 가변 컬럼 폭 조절
    """
    # Signals for Presenter
    scan_requested = pyqtSignal(str)          # Root 폴더 경로
    cancel_scan_requested = pyqtSignal()
    delete_requested = pyqtSignal(list)       # 삭제할 파일 경로 리스트
    rename_requested = pyqtSignal(str, str)    # (이름 변경할 파일 경로, 새 파일명)
    item_double_clicked = pyqtSignal(str, list) # (더블클릭한 파일경로, 해당 그룹 전체 파일경로 리스트)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Duplicated Image Finder")
        self.resize(1150, 700)
        self._is_updating_checks = False  # 시그널 순환 방지용 플래그
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
        self.txt_root.setReadOnly(True)
        self.txt_root.setPlaceholderText("검사할 이미지 Root 폴더 경로를 선택하세요...")
        folder_layout.addWidget(self.txt_root)

        self.btn_browse = QPushButton("폴더 선택...")
        self.btn_browse.clicked.connect(self._on_browse_folder)
        folder_layout.addWidget(self.btn_browse)

        self.btn_scan = QPushButton("중복 이미지 스캔 시작")
        self.btn_scan.setStyleSheet("font-weight: bold; background-color: #007acc; color: white; padding: 6px 12px;")
        self.btn_scan.clicked.connect(self._on_scan_clicked)
        folder_layout.addWidget(self.btn_scan)

        # 스캔 취소 버튼 (스캔 중에만 표시)
        self.btn_cancel = QPushButton("스캔 취소")
        self.btn_cancel.setStyleSheet(
            "font-weight: bold; background-color: #f0ad4e; color: white; padding: 6px 12px;"
        )
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self._on_cancel_clicked)
        folder_layout.addWidget(self.btn_cancel)

        main_layout.addLayout(folder_layout)

        # 2. 진행 상태 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("준비됨")
        self.lbl_status.setFont(QFont("Malgun Gothic", 9))
        main_layout.addWidget(self.lbl_status)

        # 3. 중앙 분할 영역 (QSplitter: 좌측 트리 + 우측 소형 이미지 미리보기)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(True)
        self.splitter.splitterMoved.connect(self._on_splitter_moved)
        main_layout.addWidget(self.splitter, stretch=1)

        # 3-1. 좌측: 중복 이미지 Tree (QGroupBox 감싸기 & 가변 컬럼 폭 & 체크박스)
        tree_box = QGroupBox("중복 이미지 목록")
        tree_box.setStyleSheet("QGroupBox { font-weight: bold; }")
        tree_box_layout = QVBoxLayout(tree_box)
        tree_box_layout.setContentsMargins(10, 15, 10, 10)
        tree_box_layout.setSpacing(8)

        # 접힌 미리보기 복원 큐 버튼 (오른쪽 밀기로 미리보기가 접혔을 때 노출)
        header_layout = QHBoxLayout()
        header_layout.addStretch(1)
        
        self.btn_show_preview = QPushButton("◀ 미리보기 열기")
        self.btn_show_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_show_preview.setStyleSheet(
            "QPushButton { background-color: #007acc; color: white; font-weight: bold; "
            "border: none; border-radius: 4px; padding: 4px 10px; font-size: 11px; } "
            "QPushButton:hover { background-color: #005999; }"
        )
        self.btn_show_preview.setVisible(False)
        self.btn_show_preview.clicked.connect(self._restore_preview_panel)
        header_layout.addWidget(self.btn_show_preview)
        
        tree_box_layout.addLayout(header_layout)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["파일명 / 경로", "파일 크기", "수정 날짜"])
        
        # 가변 컬럼 폭 조절 가능하도록 Interactive 설정 및 초기폭 지정
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.tree.setColumnWidth(0, 480)
        self.tree.setColumnWidth(1, 100)
        self.tree.setColumnWidth(2, 140)

        # 체크박스 및 선택 이벤트 동기화
        self.tree.itemChanged.connect(self._on_tree_item_changed)
        self.tree.currentItemChanged.connect(self._on_tree_current_item_changed)
        self.tree.itemClicked.connect(self._on_tree_current_item_changed)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        tree_box_layout.addWidget(self.tree)
        self.splitter.addWidget(tree_box)

        # 3-2. 우측: 소형 미리보기 패널 (AspectLabel 사용으로 크기 커짐 방지)
        preview_box = QGroupBox("미리보기")
        preview_box.setStyleSheet("QGroupBox { font-weight: bold; }")
        preview_layout = QVBoxLayout(preview_box)
        preview_layout.setContentsMargins(10, 15, 10, 10)
        preview_layout.setSpacing(8)

        # 썸네일 표시 커스텀 라벨 (AspectLabel)
        self.lbl_preview_img = AspectLabel(preview_box)
        self.lbl_preview_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview_img.setStyleSheet("border: 1px solid #d0d0d0; background-color: #f8f9fa; border-radius: 4px;")
        self.lbl_preview_img.setMinimumSize(220, 220)
        self.lbl_preview_img.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        preview_layout.addWidget(self.lbl_preview_img)

        # 이미지 상세 정보 라벨
        self.lbl_preview_info = QLabel("이미지를 선택하면 이곳에 미리보기가 표시됩니다.")
        self.lbl_preview_info.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.lbl_preview_info.setWordWrap(True)
        self.lbl_preview_info.setStyleSheet("color: #333333; line-height: 1.4;")
        preview_layout.addWidget(self.lbl_preview_info)

        preview_layout.addStretch(1)
        self.splitter.addWidget(preview_box)

        # Splitter 비율 설정 (좌측: 75%, 우측: 25%)
        self.splitter.setSizes([750, 250])

        # 4. 하단 액션 버튼들 (전체 선택 체크박스, 선택 카운트, 삭제, Rename)
        action_layout = QHBoxLayout()
        
        # 전체 선택 체크박스 추가
        self.chk_select_all = QCheckBox("전체 선택")
        self.chk_select_all.setFont(QFont("Malgun Gothic", 9, QFont.Weight.Bold))
        self.chk_select_all.stateChanged.connect(self._on_select_all_changed)
        action_layout.addWidget(self.chk_select_all)

        action_layout.addSpacing(10)

        self.lbl_selected_count = QLabel("선택된 항목: 0개")
        self.lbl_selected_count.setFont(QFont("Malgun Gothic", 9))
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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._check_preview_visibility()

    def _on_splitter_moved(self, pos: int, index: int):
        self._check_preview_visibility()

    def _check_preview_visibility(self):
        sizes = self.splitter.sizes()
        if len(sizes) >= 2:
            right_w = sizes[1]
            if right_w <= 40:
                self.btn_show_preview.setVisible(True)
            else:
                self.btn_show_preview.setVisible(False)

    def _restore_preview_panel(self):
        current_sizes = self.splitter.sizes()
        total_width = sum(current_sizes)
        if total_width == 0:
            total_width = self.width()

        target_right = max(260, int(total_width * 0.25))
        target_left = max(100, total_width - target_right)

        start_left, start_right = current_sizes[0], current_sizes[1]
        end_left, end_right = target_left, target_right

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(250)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)

        def on_step(progress: float):
            cur_left = int(start_left + (end_left - start_left) * progress)
            cur_right = int(start_right + (end_right - start_right) * progress)
            self.splitter.setSizes([cur_left, cur_right])

        self._anim.valueChanged.connect(on_step)
        self._anim.finished.connect(lambda: self.btn_show_preview.setVisible(False))
        self._anim.start()

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

    def _on_cancel_clicked(self):
        """스캔 취소 버튼 클릭 시 시그널 발행"""
        self.cancel_scan_requested.emit()

    def set_scanning_state(self, is_scanning: bool):
        """스캔 중 상태에 따라 버튼 가시성 전환"""
        self.btn_scan.setVisible(not is_scanning)
        self.btn_cancel.setVisible(is_scanning)

    def get_checked_file_paths(self) -> List[str]:
        """현재 체크박스로 선택된(Checked) 모든 파일의 경로 리스트 반환"""
        checked_paths = []
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            group_node = root.child(i)
            for j in range(group_node.childCount()):
                child = group_node.child(j)
                if child.checkState(0) == Qt.CheckState.Checked:
                    path = child.data(0, Qt.ItemDataRole.UserRole)
                    if path:
                        checked_paths.append(path)
        return checked_paths

    def _update_checked_count(self):
        """선택 카운트 업데이트 및 전체 선택 체크박스 상태 동기화"""
        all_paths = []
        checked_paths = []
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            group_node = root.child(i)
            for j in range(group_node.childCount()):
                child = group_node.child(j)
                path = child.data(0, Qt.ItemDataRole.UserRole)
                if path:
                    all_paths.append(path)
                    if child.checkState(0) == Qt.CheckState.Checked:
                        checked_paths.append(path)

        total_count = len(all_paths)
        checked_count = len(checked_paths)
        self.lbl_selected_count.setText(f"선택된 항목: {checked_count}/{total_count}개")

        # 전체 선택 체크박스 상태 동기화 (시그널 차단 처리)
        self.chk_select_all.blockSignals(True)
        if total_count > 0 and checked_count == total_count:
            self.chk_select_all.setCheckState(Qt.CheckState.Checked)
        elif checked_count == 0:
            self.chk_select_all.setCheckState(Qt.CheckState.Unchecked)
        else:
            self.chk_select_all.setCheckState(Qt.CheckState.PartiallyChecked)
        self.chk_select_all.blockSignals(False)

    def _on_select_all_changed(self, state_int: int):
        """'전체 선택' 체크박스 토글 처리"""
        if self._is_updating_checks:
            return

        self._is_updating_checks = True
        try:
            target_state = Qt.CheckState(state_int)
            if target_state == Qt.CheckState.PartiallyChecked:
                target_state = Qt.CheckState.Checked

            root = self.tree.invisibleRootItem()
            for i in range(root.childCount()):
                group_node = root.child(i)
                group_node.setCheckState(0, target_state)
                for j in range(group_node.childCount()):
                    group_node.child(j).setCheckState(0, target_state)
        finally:
            self._is_updating_checks = False
            self._update_checked_count()

    def _on_tree_item_changed(self, item: QTreeWidgetItem, column: int):
        """트리 각 항목의 체크박스 상태 변경 시 동기화 처리"""
        if column != 0 or self._is_updating_checks:
            return

        self._is_updating_checks = True
        try:
            # 1. 부모(그룹 노드) 체크 변경 -> 하위 자식 노드 일괄 적용
            if item.parent() is None:
                state = item.checkState(0)
                if state in (Qt.CheckState.Checked, Qt.CheckState.Unchecked):
                    for i in range(item.childCount()):
                        item.child(i).setCheckState(0, state)

            # 2. 자식(파일 노드) 체크 변경 -> 부모(그룹 노드) 상태 업데이트 (Checked/Unchecked/PartiallyChecked)
            else:
                parent = item.parent()
                if parent:
                    total_children = parent.childCount()
                    checked_count = sum(1 for i in range(total_children) if parent.child(i).checkState(0) == Qt.CheckState.Checked)
                    
                    if checked_count == total_children:
                        parent.setCheckState(0, Qt.CheckState.Checked)
                    elif checked_count == 0:
                        parent.setCheckState(0, Qt.CheckState.Unchecked)
                    else:
                        parent.setCheckState(0, Qt.CheckState.PartiallyChecked)
        finally:
            self._is_updating_checks = False
            self._update_checked_count()

    def _on_tree_current_item_changed(self, current: QTreeWidgetItem, previous=None):
        """트리 항목 선택 시 우측 소형 미리보기 패널 갱신"""
        if not current:
            self._clear_preview()
            return

        file_path = current.data(0, Qt.ItemDataRole.UserRole)
        if not file_path or not os.path.exists(file_path):
            self._clear_preview()
            return

        self._update_preview_panel(file_path)

    def _clear_preview(self):
        self.lbl_preview_img.clear_preview()
        self.lbl_preview_info.setText("이미지를 선택하면 이곳에 미리보기가 표시됩니다.")

    def _update_preview_panel(self, file_path: str):
        """우측 미리보기 패널 썸네일 및 상세 정보 표시"""
        try:
            pixmap = QPixmap(file_path)
            if pixmap.isNull():
                self._clear_preview()
                return

            # 커스텀 AspectLabel로 렌더링 (라벨 크기가 커지는 버그 해결)
            self.lbl_preview_img.set_preview_pixmap(pixmap)

            # 메타데이터 정보 구성
            filename = os.path.basename(file_path)
            depth2_folder = get_last_two_depths(file_path)
            file_size_kb = os.path.getsize(file_path) / 1024.0
            
            # 해상도 구하기
            width, height = pixmap.width(), pixmap.height()
            
            mtime = os.path.getmtime(file_path)
            mtime_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')

            info_text = (
                f"<b>파일명:</b> {filename}<br/>"
                f"<b>위치:</b> {depth2_folder}<br/>"
                f"<b>해상도:</b> {width} × {height} px<br/>"
                f"<b>크기:</b> {file_size_kb:.1f} KB<br/>"
                f"<b>수정일:</b> {mtime_str}"
            )
            self.lbl_preview_info.setText(info_text)
        except Exception:
            self._clear_preview()

    def _on_delete_clicked(self):
        file_paths = self.get_checked_file_paths()
        if not file_paths:
            QMessageBox.warning(self, "경고", "삭제할 파일을 체크박스로 1개 이상 선택하세요.")
            return

        # 그룹 내 모든 원본이 완전히 삭제되는지(100% 삭제) 안전 검사
        total_deleted_groups = []
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            group_node = root.child(i)
            group_files = []
            for j in range(group_node.childCount()):
                p = group_node.child(j).data(0, Qt.ItemDataRole.UserRole)
                if p:
                    group_files.append(p)

            checked_in_group = [p for p in group_files if p in file_paths]
            if group_files and len(checked_in_group) == len(group_files):
                group_name = group_node.text(0)
                total_deleted_groups.append((group_name, len(group_files)))

        # 그룹 원본이 유실되는 전수 삭제 경고 처리
        if total_deleted_groups:
            warn_msg = (
                f"⚠️ [데이터 유실 주의 경고]\n\n"
                f"선택하신 파일 중 {len(total_deleted_groups)}개 그룹의 모든 파일(100%)이 삭제 대상으로 선택되었습니다.\n\n"
                f"해당 그룹의 모든 파일이 삭제되면 남은 원본이 없어 해당 이미지가 완전히 소실됩니다.\n\n"
                f"정말 중복 원본까지 완전히 삭제하시겠습니까?"
            )
            reply = QMessageBox.warning(
                self,
                "⚠️ 그룹 파일 전수 삭제 경고",
                warn_msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No  # 실수 방지를 위한 기본값 No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        else:
            reply = QMessageBox.question(
                self, "확인", f"체크 선택한 {len(file_paths)}개 파일을 삭제하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self.delete_requested.emit(file_paths)

    def _on_rename_clicked(self):
        file_paths = self.get_checked_file_paths()
        if len(file_paths) != 1:
            QMessageBox.warning(self, "경고", "이름 변경은 체크박스로 단 1개의 파일만 선택했을 때 진행할 수 있습니다.")
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
            item.setExpanded(not item.isExpanded())
            return

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
        """중복 그룹 트리 렌더링 (체크박스 활성화)"""
        self._is_updating_checks = True
        self.tree.clear()
        self._clear_preview()

        group_index = 1
        total_duplicates = 0
        for hash_val, paths in groups.items():
            if len(paths) < 2:
                continue

            # 그룹 노드 생성 (체크박스 및 Tristate 지원)
            group_node = QTreeWidgetItem(self.tree)
            group_node.setText(0, f"그룹 #{group_index} (중복 {len(paths)}개) - Hash: {hash_val[:8]}...")
            group_node.setFont(0, QFont("Malgun Gothic", 10, QFont.Weight.Bold))
            group_node.setFlags(group_node.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsAutoTristate)
            group_node.setCheckState(0, Qt.CheckState.Unchecked)
            group_node.setExpanded(True)

            for path in paths:
                child = QTreeWidgetItem(group_node)
                child.setText(0, path)
                child.setData(0, Qt.ItemDataRole.UserRole, path)
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, Qt.CheckState.Unchecked)

                if os.path.exists(path):
                    size_kb = os.path.getsize(path) / 1024.0
                    mtime = os.path.getmtime(path)
                    mtime_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                    child.setText(1, f"{size_kb:.1f} KB")
                    child.setText(2, mtime_str)
                else:
                    child.setText(1, "N/A")
                    child.setText(2, "N/A")

                total_duplicates += 1

            group_index += 1

        self._is_updating_checks = False
        self._update_checked_count()
        self.finish_progress(f"스캔 완료: 총 {group_index - 1}개 중복 그룹, {total_duplicates}개 중복 파일 발견.")
