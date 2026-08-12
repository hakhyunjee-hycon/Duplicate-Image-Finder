import sys
import os

# 현재 파일이 위치한 디렉토리를 sys.path 최상단에 추가하여 모듈 임포트 방지
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

from models.duplicate_model import DuplicateModel
from views.main_view import MainView
from presenters.main_presenter import MainPresenter


def main():
    app = QApplication(sys.argv)

    # 기본 폰트 설정
    default_font = QFont("Malgun Gothic", 9)
    app.setFont(default_font)

    # MVP 객체 생성 및 바인딩
    model = DuplicateModel()
    view = MainView()
    presenter = MainPresenter(view, model)

    view.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
