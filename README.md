# 🖼️ Duplicate-Image-Finder (중복 이미지 검색 및 관리 프로그램)

PyQt6 및 Python을 기반으로 구축된 MVP(Model-View-Presenter) 아키텍처의 중복 이미지 탐지 및 관리 Desktop 애플리케이션입니다.

---

## 🌟 주요 기능 (Key Features)

1. **2단계 하이브리드 중복 이미지 스캔**:
   - 1차: `os.path.getsize`로 동일 크기 파일 빠르게 그룹화.
   - 2차: `MD5` 64KB Chunk 해시 비교로 유일한 바이너리 중복 그룹 탐지.
2. **QTreeWidget 기반 멀티셀렉트 파일 관리**:
   - 그룹별 중복 목록 시각화.
   - 다중 선택(Ctrl/Shift)을 이용한 선택 파일 일괄 삭제 및 이름 변경.
3. **인터랙티브 이미지 미리보기 팝업 (Preview Dialog)**:
   - 2줄 헤더 표시: `(현재인덱스/전체개수) 상위2단계 폴더` / `파일명`
   - 가로/세로 4px 패딩 유지 및 자동 Aspect Ratio Fit/Fill.
   - 지정 비율(200%, 100%, 75%, 50%, 25%) / 휠 확대·축소 지원.
   - 화면 경계 이탈 방지 클램핑(Clamping) 조작 패닝(Pan).
4. **비동기 멀티스레딩 (QThread)**:
   - 스캔 중 UI가 프레이징(Freezing)되지 않으며 실시간 Progress Bar 동기화.

---

## 🚀 실행 방법 (Getting Started)

### 필요 라이브러리 설치
```bash
pip install -r requirements.txt
```

### 프로그램 실행
```bash
python main.py
```
*(또는 Windows 환경에서 `run.bat` 실행)*

---

## 📁 프로젝트 구조 (Project Structure)

```
_duplicate_image_finder_fromAI/
├── main.py                    # 애플리케이션 시작점
├── requirements.txt           # Dependency 패키지 목록
├── program_analysis.md        # 상세 시스템 아키텍처 분석 보고서
├── models/
│   ├── image_scanner.py       # 2단계 중복 스캔 로직 (Model)
│   └── duplicate_model.py     # 데이터 상태 및 I/O 관리 (Model)
├── views/
│   ├── main_view.py           # 메인 UI (View)
│   └── preview_dialog.py      # 미리보기 팝업 & 커스텀 QPainter 캔버스 (View)
├── presenters/
│   ├── main_presenter.py      # 메인 윈도우 비즈니스 제어 및 QThread 관리 (Presenter)
│   └── preview_presenter.py   # 미리보기 팝업 이벤트 중계 (Presenter)
└── utils/
    └── path_utils.py          # 2 depth 경로 추출 헬퍼 함수
```

---

## 📄 라이선스 (License)
MIT License
