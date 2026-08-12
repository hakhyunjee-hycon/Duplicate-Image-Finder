# 🖼️ Duplicate-Image-Finder (중복 이미지 검색 및 관리 프로그램)

PyQt6 및 Python을 기반으로 구축된 MVP(Model-View-Presenter) 아키텍처의 중복 이미지 탐지 및 관리 Desktop 애플리케이션입니다.

---

## 🌟 주요 기능 (Key Features)

1. **2단계 하이브리드 중복 이미지 스캔**:
   - 1차: `os.path.getsize`로 동일 크기 파일 빠르게 그룹화.
   - 2차: `MD5` 64KB Chunk 해시 비교로 유일한 바이너리 중복 그룹 탐지.
2. **QTreeWidget 명시적 체크박스(Checkbox) 멀티셀렉트 파일 관리**:
   - 그룹별 중복 목록 시각화.
   - 항목별 체크박스(`ItemIsUserCheckable`) 지원 (그룹 선택 시 하위 자식 일괄 체크/해제).
   - 선택된 체크 항목들을 일괄 삭제 및 단일 파일 이름 변경.
3. **가변 컬럼 폭 (Interactive Column Resizing)**:
   - 마우스 드래그를 통해 파일명/경로, 크기, 수정 날짜 컬럼 너비를 자유롭게 조절 가능.
4. **우측 소형 미리보기 패널 (Right Preview Panel)**:
   - 트리의 이미지 항목 클릭 시 우측 패널에서 썸네일 이미지 및 해상도/크기/수정일 등 상세 메타정보 표시.
5. **고급 미리보기 팝업 (Preview Dialog)**:
   - 파일 더블 클릭 시 독립 팝업 창 실행.
   - 2줄 헤더 표시: `(현재인덱스/전체개수) 상위2단계 폴더` / `파일명`
   - 가로/세로 4px 패딩 유지 및 지정 비율(200%, 100%, 75%, 50%, 25%) / 휠 확대·축소 지원.
   - 화면 경계 이탈 방지 클램핑(Clamping) 조작 패닝(Pan).
6. **비동기 멀티스레딩 (QThread)**:
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
