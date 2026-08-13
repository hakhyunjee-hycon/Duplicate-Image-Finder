# 📊 Duplicate-Image-Finder 프로젝트 분석 결과

## 1. 프로젝트 개요

| 항목 | 내용 |
| :--- | :--- |
| **프로젝트명** | Duplicate-Image-Finder (중복 이미지 검색 및 관리 프로그램) |
| **개발 언어** | Python 3.9+ |
| **주요 라이브러리** | PyQt6 (GUI), Pillow (이미지 처리), hashlib (MD5 해시) |
| **아키텍처 패턴** | MVP (Model-View-Presenter) |
| **핵심 기능** | 로컬 PC 내 중복 이미지 탐지, 그룹별 시각화, 일괄 삭제, 이름 변경, 이미지 미리보기 |

---

## 2. 프로젝트 구조

```
Duplicate-Image-Finder/
├── main.py                    # 애플리케이션 시작점 (엔트리 포인트)
├── requirements.txt           # 의존성 패키지 목록
├── program_analysis.md        # 상세 시스템 아키텍처 분석 보고서
├── run.bat                    # Windows 실행 배치 파일
├── models/
│   ├── image_scanner.py       # 2단계 중복 스캔 로직 (Model)
│   └── duplicate_model.py     # 데이터 상태 및 파일 I/O 관리 (Model)
├── views/
│   ├── main_view.py           # 메인 UI (View)
│   └── preview_dialog.py      # 미리보기 팝업 & 커스텀 캔버스 (View)
├── presenters/
│   ├── main_presenter.py      # 메인 윈도우 비즈니스 제어 및 QThread 관리 (Presenter)
│   └── preview_presenter.py   # 미리보기 팝업 이벤트 중계 (Presenter)
└── utils/
    └── path_utils.py          # 경로 유틸리티 헬퍼 함수
```

---

## 3. 파일별 상세 분석

### 3.1. `main.py` — 애플리케이션 엔트리 포인트

- **역할**: 프로그램의 시작점으로 QApplication 생성, 기본 폰트 설정, MVP 객체 바인딩을 수행
- **주요 내용**:
  - 현재 파일 디렉토리를 `sys.path`에 추가하여 모듈 임포트 문제 방지
  - `Malgun Gothic` 9pt 기본 폰트 설정 (한글 UI 최적화)
  - `DuplicateModel`, `MainView`, `MainPresenter` 객체 생성 및 연결

### 3.2. `models/image_scanner.py` — 중복 이미지 스캔 엔진

- **역할**: Root 디렉토리를 재귀 스캔하여 중복 이미지 탐지
- **주요 클래스**: `ImageScanner`
- **핵심 알고리즘 (2단계 하이브리드 스캔)**:
  1. **1단계 (크기 비교)**: `os.path.getsize()`로 파일 크기를 구해 동일 크기 파일만 후보로 그룹화
  2. **2단계 (해시 비교)**: 후보 파일들에 대해 `MD5` 해시를 64KB Chunk 단위로 계산하여 최종 중복 판정
- **지원 확장자**: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp`, `.tiff`, `.gif`
- **부가 기능**:
  - `cancel()` 메서드로 스캔 작업 취소 지원
  - `progress_callback`으로 실시간 진행률 콜백 제공
  - `OSError`, `PermissionError` 예외 처리로 접근 불가 파일 건너뜀

### 3.3. `models/duplicate_model.py` — 데이터 모델

- **역할**: 중복 그룹 데이터 보관 및 파일 삭제/이름 변경 I/O 처리
- **주요 클래스**: `DuplicateModel`
- **데이터 구조**: `Dict[str, List[str]]` — 해시값을 키로, 파일 경로 리스트를 값으로 저장
- **주요 메서드**:
  - `set_duplicate_groups()` / `get_duplicate_groups()`: 그룹 데이터 설정/조회
  - `delete_files()`: 선택 파일 삭제 후 모델 갱신 (1개 이하 남으면 그룹 해제)
  - `rename_file()`: 단일 파일 이름 변경 및 모델 내부 경로 업데이트

### 3.4. `views/main_view.py` — 메인 UI

- **역할**: 중복 이미지 관리 메인 윈도우 UI 구성
- **주요 클래스**: `MainView` (QMainWindow), `AspectLabel` (커스텀 QLabel)
- **주요 UI 구성 요소**:
  - **Root 폴더 선택 바**: ReadOnly 텍스트박스 + "폴더 선택..." 버튼 + "중복 이미지 스캔 시작" 버튼
  - **진행 상태 바**: 스캔 진행률 실시간 표시
  - **중복 이미지 목록 트리 (QTreeWidget)**: 그룹별 중복 파일 목록, 체크박스 지원, 가변 컬럼 폭
  - **우측 미리보기 패널**: AspectLabel 기반 썸네일 + 파일 상세 정보 (해상도, 크기, 수정일)
  - **하단 액션 바**: 전체 선택 체크박스, 선택 카운트, 파일명 변경, 선택 파일 삭제 버튼
- **주요 기능**:
  - **전체 선택/해제**: Tristate 체크박스 동기화 (Checked/Unchecked/PartiallyChecked)
  - **그룹 전수 삭제 경고**: 그룹 내 모든 파일이 삭제 대상일 때 2차 경고 팝업
  - **Splitter 접힘 감지**: 우측 미리보기 패널이 40px 이하로 접히면 "◀ 미리보기 열기" 큐 버튼 노출
  - **QVariantAnimation**: 미리보기 패널 복원 시 250ms OutCubic 이징 슬라이딩 애니메이션
  - **AspectLabel**: `setPixmap()` 호출 시 레이아웃 커짐 버그를 방지하는 커스텀 렌더링

### 3.5. `views/preview_dialog.py` — 미리보기 팝업

- **역할**: 이미지 미리보기 팝업 다이얼로그 및 커스텀 캔버스
- **주요 클래스**: `PreviewDialog` (QDialog), `ImageCanvasWidget` (QWidget)
- **주요 기능**:
  - **2줄 헤더**: `(현재인덱스/전체개수) 상위2단계폴더` / `파일명`
  - **4px 패딩 유지**: QPainter `setClipRect` 적용으로 여백 보장
  - **확대/축소**: QComboBox (200%, 100%, 75%, 50%, 25%) 및 마우스 휠 (15% 단계)
  - **패닝 (Pan)**: 이미지가 뷰포트보다 클 때 드래그 이동, 클램핑(Clamping)으로 경계 이탈 방지
  - **이전/다음 버튼**: 그룹 내 파일 간 이동
  - **상태바**: 현재 확대/축소 비율 실시간 표시

### 3.6. `presenters/main_presenter.py` — 메인 프레젠터

- **역할**: MainView와 DuplicateModel 간의 이벤트 제어 및 비동기 스캔 관리
- **주요 클래스**: `MainPresenter`, `ScanWorker` (QObject)
- **주요 기능**:
  - **비동기 스캔**: `QThread` + `ScanWorker`로 백그라운드 스캔 실행, UI 프리징 방지
  - **시그널 연결**: `scan_requested`, `delete_requested`, `rename_requested`, `item_double_clicked`
  - **스캔 완료 처리**: 모델에 그룹 데이터 설정 후 뷰에 트리 렌더링
  - **삭제/이름 변경 처리**: 모델 호출 후 뷰 갱신 및 상태 메시지 표시

### 3.7. `presenters/preview_presenter.py` — 미리보기 프레젠터

- **역할**: PreviewDialog 생성 및 실행
- **주요 클래스**: `PreviewPresenter`
- **주요 기능**: `show_preview()` 메서드로 현재 파일 인덱스 계산 후 PreviewDialog 팝업 실행

### 3.8. `utils/path_utils.py` — 경로 유틸리티

- **역할**: 파일 경로에서 상위 2단계 디렉토리 경로 추출
- **주요 함수**: `get_last_two_depths()`
  - 예: `C:/Path/To/FolderA/FolderB/image.png` → `FolderA/FolderB`
  - 디렉토리 depth가 2 미만인 경우 가능한 경로만 반환

---

## 4. 아키텍처 설계 (MVP 패턴)

```
┌─────────────────────────────────────────────────────────────┐
│                        View Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   MainView   │  │ AspectLabel  │  │  PreviewDialog   │  │
│  │ (QMainWindow)│  │  (QLabel)    │  │   (QDialog)      │  │
│  └──────┬───────┘  └──────────────┘  └────────┬─────────┘  │
└─────────┼──────────────────────────────────────┼────────────┘
          │ Signals                              │
┌─────────▼──────────────────────────────────────▼────────────┐
│                     Presenter Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ MainPresenter│  │  ScanWorker  │  │PreviewPresenter  │  │
│  │              │  │ (QThread)    │  │                  │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────┘  │
└─────────┼─────────────────┼────────────────────────────────┘
          │                 │
┌─────────▼─────────────────▼────────────────────────────────┐
│                       Model Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │DuplicateModel│  │ ImageScanner │  │   path_utils     │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. 핵심 기능 요약

| 기능 | 설명 |
| :--- | :--- |
| **2단계 중복 스캔** | 파일 크기 → MD5 해시 순차 비교로 성능 최적화 |
| **비동기 스캔** | QThread 기반 백그라운드 스캔, UI 프리징 방지 |
| **스캔 취소** | 스캔 중 취소 버튼 제공, 즉시 중단 및 상태 표시 |
| **그룹별 시각화** | QTreeWidget으로 중복 그룹 트리 표시 |
| **체크박스 관리** | 전체 선택/해제, Tristate 상태 동기화 |
| **일괄 삭제** | 선택 파일 일괄 삭제 + 그룹 전수 삭제 경고 |
| **이름 변경** | 단일 파일 이름 변경 지원 |
| **미리보기 패널** | 우측 썸네일 + 상세 메타정보 표시 |
| **미리보기 팝업** | 줌/패닝/클램핑 지원 고급 이미지 뷰어 |
| **Splitter 접힘 복원** | QVariantAnimation 슬라이딩 애니메이션 |

---

## 6. 의존성

```txt
PyQt6>=6.5.0
Pillow>=10.0.0
```

---

## 7. 실행 방법

```bash
# 의존성 설치
pip install -r requirements.txt

# 프로그램 실행
python main.py
# 또는 Windows에서 run.bat 실행
```

---

## 8. 종합 평가

### ✅ 강점
1. **완벽한 MVP 패턴 적용**: Model/View/Presenter 관심사 분리가 명확하여 유지보수성 우수
2. **스캔 성능 최적화**: 1차 크기 필터링 후 2차 해시 비교로 불필요한 I/O 절감
3. **디테일한 UX**: ReadOnly 경로 입력, 전수 삭제 경고, Splitter 접힘 복원 애니메이션 등
4. **비동기 처리**: QThread 기반으로 대용량 스캔 시에도 UI 응답성 유지

### 🔮 개선 제안
1. **휴지통 지원**: 파일 즉시 삭제 대신 시스템 휴지통 이동 옵션 (`send2trash` 패키지)
2. **썸네일 아이콘**: 트리 각 행에 소형 썸네일 미리보기 아이콘 추가
3. **스캔 필터링**: 파일 크기 범위 제한 (예: 1MB 이상만 탐색) 기능 추가
