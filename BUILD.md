# 🖥️ Windows 실행파일(onedir .exe) 빌드 가이드

배포 대상 직원이 Python 설치 없이 더블클릭으로 실행할 수 있도록
`streamlit-desktop-app` 으로 데스크톱 앱(.exe)을 만든다.

> ⚠️ **크로스 빌드 불가** — Windows exe 는 **반드시 Windows PC** 에서 빌드해야 한다.
> macOS/Linux 에서 빌드하면 해당 OS용 바이너리가 나온다.

## 사전 준비 (Windows)

- Python 3.10~3.12 설치 (PATH 등록)
- 저장소 루트에 `icon.ico` 존재 (이미 포함됨)

## 빌드 (한 번에)

저장소 루트에서:

```bat
build_windows.bat
```

스크립트가 수행하는 일:

1. `pip install -r requirements.txt` — 앱 의존성
2. `pip install streamlit-desktop-app` — 빌드 도구 (requirements 와 별개)
3. onedir 빌드 (`--onefile` 미사용 = PyInstaller 기본 onedir):
   ```bat
   streamlit-desktop-app build app.py ^
     --name 셔틀버스정산 ^
     --icon icon.ico ^
     --pyinstaller-options --noconfirm ^
       --add-data "settlement.py;." ^
       --add-data "excel_format.py;." ^
       --copy-metadata streamlit ^
       --collect-all streamlit
   ```
4. `dist\셔틀버스정산\` 폴더를 `셔틀버스정산_win.zip` 으로 패키징

## 옵션 설명

- **onedir vs onefile**: `--onefile` 을 주지 않으므로 PyInstaller 기본값인
  **onedir**(폴더 배포)로 빌드된다. 첫 실행 압축 해제가 없어 기동이 빠르다.
- **`--add-data "settlement.py;."` / `"excel_format.py;."`**:
  `app.py` 가 import 하므로 보통 자동 포함되지만, 누락 시를 대비해 명시.
  Windows 의 add-data 구분자는 `;` 이다.
- **`--copy-metadata streamlit` / `--collect-all streamlit`**:
  streamlit 메타데이터/정적 파일 누락으로 인한 빌드·실행 오류를 예방.

## 빌드 후 확인

- `dist\셔틀버스정산\` 폴더에 `settlement.py` / `excel_format.py` 관련 모듈이
  포함됐는지 확인. 누락 시 위 `--add-data` 가 적용됐는지 점검.
- `dist\셔틀버스정산\셔틀버스정산.exe` 더블클릭 → 데스크톱 창이 뜨고
  웹앱과 동일하게 동작하는지 확인.

## 배포 대상 PC 요구사항

- **Edge WebView2** + **.NET 4.x** 필요 (보통 Windows 10/11 기본 포함).
- 없을 경우 Microsoft 의 WebView2 Runtime 을 설치.

## 산출물

- `dist\셔틀버스정산\` — 실행 폴더 (exe + 의존 파일)
- `셔틀버스정산_win.zip` — 배포용 압축본
