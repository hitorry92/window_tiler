# 🪟 Window Tiler

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![Tkinter](https://img.shields.io/badge/Tkinter-GUI-FF6F00?style=flat)
![License](https://img.shields.io/badge/License-MIT-4CAF50?style=flat)

Windows용 멀티 모니터 창 타일링 도구

</div>

---

## 🖼️ 미리보기

<div align="center">
  <img src="./win_tiler.png" alt="Window Tiler Preview">
</div>

---

## 📖 프로젝트 소개

Window Tiler는 Windows 환경에서 여러 모니터를 지원하는 윈도우 타일링 도구입니다. 

다중 모니터를 사용하여 작업할 때 창들을 자동으로 정렬하고, 메인 슬롯과 사이드 슬롯 간의 창 위치를 쉽게 교환할 수 있습니다.

### 주요 기능

- 🚀 **멀티 모니터 지원**: 각 모니터별로 독립적인 타일링 프로필 적용
- 🔄 **로컬/글로벌 모드**: 모니터별 독립 운영 또는 전체 연동 모드
- 📦 **창 자동 배치**: 열린 창들을 슬롯에 자동으로 할당
- 💾 **프로필 저장/불러오기**: 커스텀 레이아웃을 프로필로 저장
- ⌨️ **단축키 지원**: 키보드로 빠른 타일링 제어
- 🔔 **트레이 실행**: 백그라운드에서 계속 운영

---

## 🛠️ 설치 방법

### 필수 요구사항

- Python 3.11 이상
- Windows 10/11

### 의존성 설치

```bash
pip install -r requirements.txt
```

### 실행 방법

```bash
python main.py
```

---

## 📋 사용 방법

### 기본 작동

1. 프로그램 실행 시 트레이 아이콘이 생성됩니다.
2. 트레이 아이콘을 우클릭하여 설정 창을 열 수 있습니다.
3. 단축키(`Ctrl+Shift+T` 기본값)를 눌러 타일링을 시작/중지합니다.

### 설정 창 사용

#### 상단 패널

- **모니터 선택**: 편집할 모니터 선택
- **프로필**: 레이아웃 프로필 선택/저장/삭제
- **모드 전환**: 로컬 모드 ↔ 글로벌 모드

#### 좌측 패널 (미리보기)

- **분할선 드래그**: 마우스로 분할 비율 조절
- **슬롯 클릭**: 메인 슬롯 지정
- **우클릭 메뉴**: 창 할당, 병합, 고정 등

#### 우측 패널 (창 배정 기록)

- 창 목록 확인
- 드래그 앤 드롭으로 창 위치 교환
- 고정/덮개 토글

### 창 교환 (Swap) 방법

1. **자동 교환**: 사이드 창을 클릭하면 메인 슬롯과 자동 교환
2. **투명 덮개 클릭**: 사이드 창 위의 덮개를 클릭하여 교환
3. **UI에서 교환**: 창 배정 기록에서 드래그하여 교환

---

## 📂 프로젝트 구조

```
├── main.py                 # 메인 실행 파일
├── requirements.txt        # 의존성 패키지
├── README.md             # 프로젝트 문서
│
├── src/
│   ├── main.py           # 앱 메인 클래스
│   ├── app_config.py     # 설정 관리
│   ├── tiling_engine.py  # 타일링 엔진
│   ├── event_monitor.py  # 이벤트 모니터
│   ├── hotkey_manager.py # 단축키 관리
│   ├── tray_manager.py   # 트레이 관리
│   ├── overlay_manager.py# 오버레이 관리
│   ├── win_utils.py     # 윈도우 유틸리티
│   │
│   └── gui/
│       ├── settings_gui.py      # 설정 GUI
│       ├── preview_canvas.py    # 미리보기 캔버스
│       ├── slot_tree.py         # 슬롯 트리 뷰
│       ├── window_selector.py   # 창 선택기
│       ├── hotkey_entry.py      # 단축키 입력
│       ├── theme.py             # 테마 설정
│       └── components/
│           ├── profile_panel.py     # 프로필 패널
│           ├── split_panel.py      # 분할 패널
│           └── control_panel.py    # 제어 패널
```

---

## 💻 개발 정보

### 사용 기술

| 기술 | 설명 |
|------|------|
| Python 3.11+ | 프로그래밍 언어 |
| Tkinter | GUI 프레임워크 |
| ctypes | Windows API 호출 |
| win32gui | 윈도우 핸들링 |

### 개발 환경 설정

```bash
# 가상환경 생성
python -m venv venv

# 활성화 (Windows)
venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 실행
python main.py
```

---

## ⚙️ 설정 파일

설정 파일은 `%APPDATA%/WindowTiler/config.json`에 저장됩니다.

### 주요 설정 항목

| 항목 | 설명 | 기본값 |
|------|------|--------|
| `hotkey` | 타일링 단축키 | `Ctrl+Shift+T` |
| `gap` | 창 간격 (픽셀) | `0` |
| `swap_mode` | 로컬/글로벌 모드 | `local` |
| `monitor_index` | 현재 선택된 모니터 | `0` |

---

## 📄 라이선스

MIT License

---

## 🔗 관련 링크

- 이슈 리포트: GitHub Issues
- 문서: Wiki
