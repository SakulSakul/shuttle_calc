@echo off
REM ============================================================
REM  셔틀버스 정산 - tkinter 데스크톱 앱(gui.py) Windows 빌드
REM  반드시 Windows 에서 실행할 것 (크로스 빌드 불가).
REM  결과물: dist\셔틀버스정산\ 폴더 + 셔틀버스정산_win.zip
REM ============================================================
chcp 949 >nul
cd /d "%~dp0"

echo [1/3] 의존성 및 빌드 도구 설치 (py -m 으로 PATH 문제 회피)...
py -m pip install pandas openpyxl pyinstaller || goto :err

echo [2/3] PyInstaller 빌드 ( --windowed = 콘솔창 없음 )...
REM  settlement.py / excel_format.py 는 gui.py 가 import 하므로 자동 포함.
REM  누락 시 --add-data "settlement.py;." --add-data "excel_format.py;." 추가.
REM  tkinter 데이터 누락으로 실패하면 --collect-all tkinter 추가.
py -m PyInstaller --noconfirm --windowed ^
  --name 셔틀버스정산 ^
  --icon icon.ico ^
  --add-data "icon.ico;." ^
  gui.py || goto :err

echo [3/3] 결과 확인 및 zip 패키징...
if not exist "dist\셔틀버스정산\" (
  echo [실패] dist\셔틀버스정산\ 폴더가 생성되지 않았습니다.
  goto :err
)
powershell -NoProfile -Command "Compress-Archive -Path 'dist\셔틀버스정산\*' -DestinationPath '셔틀버스정산_win.zip' -Force" || goto :err

echo.
echo [완료] 빌드 성공: dist\셔틀버스정산\셔틀버스정산.exe
echo [완료] 배포 zip : 셔틀버스정산_win.zip
goto :eof

:err
echo.
echo [실패] 빌드 실패. 위 로그를 확인하세요.
exit /b 1
