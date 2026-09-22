$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

$python312 = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"

if (Test-Path $python312) {
    $python = $python312
    $pythonArgs = @()
}
elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $python = "py"
    $pythonArgs = @("-3.12")
}
else {
    $python = "python"
    $pythonArgs = @()
}

Write-Host ""
Write-Host "[1/3] Python 확인"
& $python @pythonArgs --version

Write-Host ""
Write-Host "[2/3] Chapter 07 패키지 확인"
& $python @pythonArgs -c "import pandas, numpy, streamlit, kiwipiepy"

if ($LASTEXITCODE -ne 0) {
    Write-Host "필요한 패키지를 설치합니다..."
    & $python @pythonArgs -m pip install -r requirements.txt

    if ($LASTEXITCODE -ne 0) {
        throw "패키지 설치에 실패했습니다."
    }
}

Write-Host ""
Write-Host "[3/3] Chapter 07 Streamlit 앱 실행"
Write-Host "SciPy/scikit-learn은 사용하지 않습니다."
Write-Host "브라우저가 자동으로 열리지 않으면 http://localhost:8501 을 여세요."

& $python @pythonArgs -m streamlit run app.py
