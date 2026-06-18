@echo off
REM ============================================================
REM  셔틀버스 정산 — Windows onedir 실행파일(.exe) 빌드 스크립트
REM  반드시 Windows 에서 실행할 것 (크로스 빌드 불가).
REM  결과물: dist\셔틀버스정산\  폴더 + 셔틀버스정산_win.zip
REM ============================================================
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo [1/4] 앱 의존성 설치...
pip install -r requirements.txt || goto :err

echo [2/4] 빌드 도구 설치 (requirements 와 별개)...
pip install streamlit-desktop-app || goto :err

echo [3/4] onedir 빌드 ( --onefile 미사용 = PyInstaller 기본 onedir )...
REM  settlement.py / excel_format.py 는 app.py 가 import 하므로 보통 자동 포함되지만,
REM  누락 방지를 위해 --add-data 로 명시.
REM  streamlit 메타데이터/정적파일 누락 대비: --copy-metadata / --collect-all 추가.
streamlit-desktop-app build app.py ^
  --name 셔틀버스정산 ^
  --icon icon.ico ^
  --pyinstaller-options --noconfirm ^
    --add-data "settlement.py;." ^
    --add-data "excel_format.py;." ^
    --copy-metadata streamlit ^
    --collect-all streamlit || goto :err

echo [4/4] 모듈 포함 여부 확인 및 zip 패키징...
if not exist "dist\셔틀버스정산\" (
  echo [오류] dist\셔틀버스정산\ 폴더가 생성되지 않았습니다.
  goto :err
)
REM  배포 산출물 zip 생성
powershell -NoProfile -Command "Compress-Archive -Path 'dist\셔틀버스정산\*' -DestinationPath '셔틀버스정산_win.zip' -Force" || goto :err

echo.
echo ✅ 빌드 완료: dist\셔틀버스정산\셔틀버스정산.exe
echo ✅ 배포 zip : 셔틀버스정산_win.zip
echo    (배포 PC 요구사항: Edge WebView2 + .NET 4.x — 보통 Win10/11 기본 포함)
goto :eof

:err
echo.
echo ❌ 빌드 실패. 위 로그를 확인하세요.
exit /b 1
