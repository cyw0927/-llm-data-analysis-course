@echo off
setlocal
cd /d "%~dp0"

set "PY314=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"

if exist "%PY314%" (
    set "PYTHON=%PY314%"
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        set "PYTHON=py -3.14"
    ) else (
        set "PYTHON=python"
    )
)

echo.
echo [1/3] Python 확인
%PYTHON% --version
if errorlevel 1 goto :error

echo.
echo [2/3] 필요한 패키지 확인
%PYTHON% -c "import streamlit, pandas, sklearn, openpyxl, kiwipiepy" >nul 2>nul
if errorlevel 1 (
    echo 필요한 패키지를 설치합니다...
    %PYTHON% -m pip install streamlit pandas scikit-learn openpyxl kiwipiepy
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
