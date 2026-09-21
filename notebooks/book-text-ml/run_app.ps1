$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

$python314 = Join-Path $env:LOCALAPPDATA "Programs\Python\Python314\python.exe"

if (Test-Path $python314) {
    $python = $python314
    $pythonArgs = @()
}
elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $python = "py"
    $pythonArgs = @("-3.14")
}
else {
    $python = "python"
    $pythonArgs = @()
}

Write-Host ""
Write-Host "[1/3] Python 확인"
& $python @pythonArgs --version

Write-Host ""
Write-Host "[2/3] 필요한 패키지 확인"
& $python @pythonArgs -c "import streamlit, pandas, sklearn, openpyxl"
if ($LASTEXITCODE -ne 0) {
    Write-Host "필요한 패키지를 설치합니다..."
    & $python @pythonArgs -m pip install streamlit pandas scikit-learn openpyxl
}

Write-Host ""
Write-Host "[3/3] Streamlit 앱 실행"
Write-Host "브라우저가 자동으로 열리지 않으면 http://localhost:8501 을 여세요."

& $python @pythonArgs -m streamlit run app.py
