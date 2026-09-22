@echo off
setlocal
cd /d "%~dp0"

set "PY312=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"

if exist "%PY312%" (
    set "PYTHON=%PY312%"
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        set "PYTHON=py -3.12"
    ) else (
        set "PYTHON=python"
    )
)

echo.
echo [1/3] Python 확인
%PYTHON% --version
if errorlevel 1 goto :error

echo.
echo [2/3] Chapter 07 패키지 확인
%PYTHON% -c "import pandas, numpy, sklearn, streamlit, kiwipiepy" >nul 2>nul
if errorlevel 1 (
    echo 필요한 패키지를 설치합니다...
    %PYTHON% -m pip install -r requirements.txt
    if errorlevel 1 goto :error
)

echo.
echo [3/3] Chapter 07 Streamlit 앱 실행
echo 브라우저가 자동으로 열리지 않으면 http://localhost:8501 을 여세요.
%PYTHON% -m streamlit run app.py
goto :end

:error
echo.
echo 실행 중 오류가 발생했습니다.
pause

:end
endlocal
