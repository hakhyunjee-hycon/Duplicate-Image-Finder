import os
from typing import List
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QStatusBar, QWidget, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QColor, QWheelEvent, QMouseEvent, QFont

from utils.path_utils import get_last_two_depths


class ImageCanvasWidget(QWidget):
    """
    이미지를 표시하고 4px 패딩, 오토 핏, 드래그 이동(Pan clamping), 확대/축소를 담당하는 캔버스 위젯
    """
    zoom_changed = pyqtSignal(float)  # 비율 변경 시 시그널 (예: 1.0 = 100%)

    PADDING = 4  # 가로/세로 4px 패딩

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)

        self.pixmap: QPixmap = QPixmap()
        self.scale_factor: float = 1.0
        self.img_pos: QPointF = QPointF(self.PADDING, self.PADDING)

        self._is_dragging: bool = False
        self._drag_start: QPointF = QPointF()
        self._pos_start: QPointF = QPointF()

    def set_image(self, image_path: str):
        """이미지 로드 및 초기 Fit 계산"""
        if os.path.exists(image_path):
            self.pixmap = QPixmap(image_path)
        else:
            self.pixmap = QPixmap()

        self.reset_view()

    def reset_view(self):
        """화면 크기에 맞춰 초기 확대/축소 비율 계산 및 중앙 정렬"""
        if self.pixmap.isNull():
            self.update()
            return

        iw = self.pixmap.width()
        ih = self.pixmap.height()

        vw = self.width() - self.PADDING * 2
        vh = self.height() - self.PADDING * 2

        if vw <= 0 or vh <= 0:
            return

        # 요구사항에 따른 Initial Zoom / Fit 계산
        if iw <= vw and ih <= vh:
            # 이미지가 팝업보다 작은 경우 -> 100% 원본 비율
            new_scale = 1.0
        else:
            sw = vw / iw
            sh = vh / ih
            if iw > vw and ih <= vh:
                new_scale = sw
            elif iw <= vw and ih > vh:
                new_scale = sh
            else:
                # 가로/세로 모두 큰 경우 -> 비율이 더 큰 것을 기준으로 축소 (더 많이 줄여야 하는 축)
                new_scale = min(sw, sh)

        self.scale_factor = new_scale
        self._center_and_clamp()
        self.zoom_changed.emit(self.scale_factor)
        self.update()

    def set_zoom_ratio(self, ratio: float):
        """지정된 비율로 Zoom 설정 (예: 2.0 = 200%)"""
        if self.pixmap.isNull():
            return
        
        # 뷰어 중앙 기준 비율 변경
        old_scale = self.scale_factor
        self.scale_factor = max(0.05, min(ratio, 10.0))  # 5% ~ 1000% 제한
        
        # 중심점 유지 조율
        vw = self.width() - self.PADDING * 2
        vh = self.height() - self.PADDING * 2
        center_x = vw / 2 + self.PADDING
        center_y = vh / 2 + self.PADDING
        
        # 이전 좌표 대비 확대 축소 위치 보정
        rel_x = center_x - self.img_pos.x()
        rel_y = center_y - self.img_pos.y()
        
        factor = self.scale_factor / old_scale
        new_x = center_x - rel_x * factor
        new_y = center_y - rel_y * factor
        
        self.img_pos = QPointF(new_x, new_y)
        self._clamp_pos()
        self.zoom_changed.emit(self.scale_factor)
        self.update()

    def _center_and_clamp(self):
        """이미지를 가웅데 놓기 및 위치 범위 제한"""
        if self.pixmap.isNull():
            return

        iw = self.pixmap.width() * self.scale_factor
        ih = self.pixmap.height() * self.scale_factor

        vw = self.width() - self.PADDING * 2
        vh = self.height() - self.PADDING * 2

        if iw <= vw:
            x = self.PADDING + (vw - iw) / 2
        else:
            x = self.PADDING

        if ih <= vh:
            y = self.PADDING + (vh - ih) / 2
        else:
            y = self.PADDING

        self.img_pos = QPointF(x, y)
        self._clamp_pos()

    def _clamp_pos(self):
        """이미지가 view area (패딩 4px 제외 영역)를 벗어나지 않도록 위치 제한"""
        if self.pixmap.isNull():
            return

        iw = self.pixmap.width() * self.scale_factor
        ih = self.pixmap.height() * self.scale_factor

        vw = self.width() - self.PADDING * 2
        vh = self.height() - self.PADDING * 2

        x = self.img_pos.x()
        y = self.img_pos.y()

        # X축 제한
        if iw <= vw:
            x = self.PADDING + (vw - iw) / 2
        else:
            min_x = self.PADDING + vw - iw
            max_x = self.PADDING
            x = max(min_x, min(x, max_x))

        # Y축 제한
        if ih <= vh:
            y = self.PADDING + (vh - ih) / 2
        else:
            min_y = self.PADDING + vh - ih
            max_y = self.PADDING
            y = max(min_y, min(y, max_y))

        self.img_pos = QPointF(x, y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.reset_view()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 배경 칠하기 (Dark 테마 느낌)
        painter.fillRect(self.rect(), QColor("#1e1e1e"))

        # View Area (4px 패딩 경계선 가이드 표시 - 필요시)
        view_rect = QRectF(
            self.PADDING,
            self.PADDING,
            self.width() - self.PADDING * 2,
            self.height() - self.PADDING * 2
        )

        if not self.pixmap.isNull():
            iw = self.pixmap.width() * self.scale_factor
            ih = self.pixmap.height() * self.scale_factor

            target_rect = QRectF(self.img_pos.x(), self.img_pos.y(), iw, ih)

            # View Area 안으로만 렌더링되도록 Clip 적용 (4px 패딩 유지 보장)
            painter.save()
            painter.setClipRect(view_rect)
            painter.drawPixmap(target_rect.toRect(), self.pixmap)
            painter.restore()
        else:
            painter.setPen(QColor("#888888"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "이미지를 로드할 수 없습니다.")

    def wheelEvent(self, event: QWheelEvent):
        """마우스 휠 확대/축소"""
        if self.pixmap.isNull():
            return
        
        angle = event.angleDelta().y()
        if angle > 0:
            new_scale = self.scale_factor * 1.15
        else:
            new_scale = self.scale_factor / 1.15

        self.set_zoom_ratio(new_scale)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and not self.pixmap.isNull():
            iw = self.pixmap.width() * self.scale_factor
            ih = self.pixmap.height() * self.scale_factor
            vw = self.width() - self.PADDING * 2
            vh = self.height() - self.PADDING * 2

            # 이미지가 뷰포트보다 클 때만 드래그 허용
            if iw > vw or ih > vh:
                self._is_dragging = True
                self._drag_start = event.position()
                self._pos_start = QPointF(self.img_pos)
                self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_dragging:
            delta = event.position() - self._drag_start
            self.img_pos = self._pos_start + delta
            self._clamp_pos()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            self.setCursor(Qt.CursorShape.ArrowCursor)


class PreviewDialog(QDialog):
    """
    이미지 미리보기 팝업 Dialog Window
    """
    def __init__(self, file_paths: List[str], current_index: int = 0, parent=None):
        super().__init__(parent)
        self.file_paths = file_paths
        self.current_index = max(0, min(current_index, len(file_paths) - 1))

        self.setWindowTitle("이미지 미리보기")
        self.resize(900, 700)

        self._init_ui()
        self.update_preview()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 0)
        layout.setSpacing(6)

        # 1. 헤더 영역 (2줄 표시)
        # 1줄: (1/N) 폴더 경로 (마지막 2 depth)
        # 2줄: 파일명
        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)

        self.lbl_header_line1 = QLabel()
        self.lbl_header_line1.setFont(QFont("Malgun Gothic", 10, QFont.Weight.Bold))
        self.lbl_header_line1.setStyleSheet("color: #2b5b84;")

        self.lbl_header_line2 = QLabel()
        self.lbl_header_line2.setFont(QFont("Malgun Gothic", 11, QFont.Weight.Bold))
        self.lbl_header_line2.setStyleSheet("color: #111111;")

        header_layout.addWidget(self.lbl_header_line1)
        header_layout.addWidget(self.lbl_header_line2)
        layout.addLayout(header_layout)

        # 2. 이미지 View Area (4px 패딩 유지 캔버스)
        self.canvas = ImageCanvasWidget(self)
        self.canvas.zoom_changed.connect(self._on_zoom_changed)
        layout.addWidget(self.canvas, stretch=1)

        # 3. 하단 컨트롤 바 (Prev / Combobox / Next)
        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(4, 4, 4, 4)

        self.btn_prev = QPushButton("◀ 이전 (Prev)")
        self.btn_prev.setMinimumHeight(32)
        self.btn_prev.clicked.connect(self._go_prev)

        # Next(우) 버튼 왼쪽에 Combobox (200%, 100%, 75%, 50%, 25%)
        self.combo_zoom = QComboBox()
        self.combo_zoom.setMinimumHeight(32)
        self.combo_zoom.addItems(["200%", "100%", "75%", "50%", "25%"])
        self.combo_zoom.setCurrentText("100%")
        self.combo_zoom.currentIndexChanged.connect(self._on_combo_zoom_changed)

        self.btn_next = QPushButton("다음 (Next) ▶")
        self.btn_next.setMinimumHeight(32)
        self.btn_next.clicked.connect(self._go_next)

        control_layout.addWidget(self.btn_prev)
        control_layout.addStretch(1)
        control_layout.addWidget(QLabel("확대/축소:"))
        control_layout.addWidget(self.combo_zoom)
        control_layout.addWidget(self.btn_next)

        layout.addLayout(control_layout)

        # 4. Status Bar (우측 하단 확대/축소 비율 표시)
        self.status_bar = QStatusBar()
        self.lbl_zoom_status = QLabel("100%")
        self.status_bar.addPermanentWidget(self.lbl_zoom_status)
        layout.addWidget(self.status_bar)

    def update_preview(self):
        """현재 인덱스의 이미지 및 헤더 정보 업데이트"""
        if not self.file_paths:
            return

        filepath = self.file_paths[self.current_index]
        total = len(self.file_paths)
        idx_str = f"({self.current_index + 1}/{total})"

        folder_depth2 = get_last_two_depths(filepath)
        filename = os.path.basename(filepath)

        # 헤더 텍스트 1, 2줄 설정
        self.lbl_header_line1.setText(f"{idx_str}  {folder_depth2}")
        self.lbl_header_line2.setText(f"파일명: {filename}")

        # 버튼 활성화 여부
        self.btn_prev.setEnabled(self.current_index > 0)
        self.btn_next.setEnabled(self.current_index < total - 1)

        # 이미지 렌더링
        self.canvas.set_image(filepath)

    def _go_prev(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.update_preview()

    def _go_next(self):
        if self.current_index < len(self.file_paths) - 1:
            self.current_index += 1
            self.update_preview()

    def _on_combo_zoom_changed(self):
        text = self.combo_zoom.currentText().replace("%", "").strip()
        try:
            val = float(text) / 100.0
            self.canvas.set_zoom_ratio(val)
        except ValueError:
            pass

    def _on_zoom_changed(self, scale: float):
        """캔버스 줌 변경 시 status bar 및 combobox 동기화"""
        pct = int(round(scale * 100))
        self.lbl_zoom_status.setText(f"확대/축소: {pct}%")

        # ComboBox 텍스트 동기화 (블록 시그널로 루프 방지)
        pct_text = f"{pct}%"
        self.combo_zoom.blockSignals(True)
        idx = self.combo_zoom.findText(pct_text)
        if idx >= 0:
            self.combo_zoom.setCurrentIndex(idx)
        else:
            self.combo_zoom.setEditText(pct_text)
        self.combo_zoom.blockSignals(False)
