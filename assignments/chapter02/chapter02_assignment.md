# Chapter 02 제출 답안. VS Code에서 시작하는 데이터 분석 환경

> Chapter 02 실습 결과를 정리한 제출용 답안입니다.  
> 이번 장의 핵심은 **VS Code + Python + `.venv` + Jupyter Notebook + 샘플 데이터**를 하나의 정상 실행 환경으로 연결하고, 실제 실행 결과로 검증하는 것입니다.

---

## 0. 제출 정보

- GitHub ID: `cyw0927`
- 개인 저장소명: `-llm-data-analysis-course`
- 작성일: 2026-09-08
- 사용한 LLM: ChatGPT

### 최종 제출 URL

```text
https://github.com/cyw0927/-llm-data-analysis-course/blob/main/assignments/chapter02/chapter02_assignment.md
```

### 관련 실습 파일

```text
notebooks/ch02_environment_setup.ipynb
scripts/generate_sample_data.py
requirements.txt
data/raw/customers.csv
data/raw/products.csv
data/raw/orders.csv
data/raw/order_items.csv
.env.example
.gitignore
```

---

# 1. 프로젝트 루트와 Python / Git 확인

## 실행한 명령

```powershell
python --version
git --version
Get-Location
Get-ChildItem
```

## 확인 결과

```text
Python 버전: [직접 실행 후 기록]
Git 버전: [직접 실행 후 기록]
현재 작업 폴더: [직접 실행 후 기록]
```

### 내가 확인한 점

프로젝트 루트에서 `requirements.txt`, `notebooks`, `scripts`, `data` 폴더가 보이는지 확인한다. 상대경로를 사용하는 실습이므로 현재 작업 폴더가 어디인지 먼저 확인하는 것이 중요하다.

---

# 2. 프로젝트 전용 `.venv` 생성 및 활성화

## 실행한 명령

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

PowerShell 실행 정책 때문에 활성화가 차단되는 경우, 개인 학습 PC에서 현재 세션에 한해서만 다음과 같이 사용할 수 있다.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 확인 결과

```text
터미널 앞에 (.venv)가 표시되는가?: [예 / 아니오]
```

### 내가 이해한 점

`.venv`는 프로젝트별 Python 패키지를 분리하기 위한 가상환경이다. 다른 프로젝트나 시스템 전체 Python 환경과 패키지가 섞이지 않게 하는 역할을 한다.

---

# 3. 실제 Python 실행 파일 확인

## 실행한 명령

```powershell
python -c "import sys; print(sys.executable)"
```

## 실행 결과

```text
Python 실행 파일 경로: [직접 실행 후 기록]
```

정상이라면 경로 안에 현재 프로젝트의 `.venv`가 포함되어 있어야 한다.

### Evidence 1

> TODO: `.venv` 활성화 상태와 Python 실행 파일 경로가 함께 보이도록 캡처한다.

![터미널 Python 실행 파일 확인](./images/step01_terminal_python.png)

---

# 4. `requirements.txt` 패키지 설치

## 실행한 명령

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 확인 결과

```text
설치 완료 여부: [직접 실행 후 기록]
오류 발생 여부: [없음 / 있음]
```

### 내가 이해한 점

`pip`만 실행하기보다 `python -m pip`를 사용하면 현재 선택된 Python, 즉 프로젝트의 `.venv`에 패키지를 설치한다는 점을 더 명확하게 확인할 수 있다.

---

# 5. VS Code Python 인터프리터와 Notebook 커널 연결

VS Code에서 다음 순서로 프로젝트의 `.venv`를 선택한다.

```text
Ctrl + Shift + P
→ Python: Select Interpreter
→ 현재 프로젝트의 .venv 선택
```

그다음 아래 Notebook을 연다.

```text
notebooks/ch02_environment_setup.ipynb
```

Notebook 오른쪽 위 커널 선택 메뉴에서도 같은 `.venv` 환경을 선택한다.

### 핵심 원칙

```text
패키지를 설치한 Python
=
VS Code Python 인터프리터
=
Jupyter Notebook 커널
```

### 확인 결과

```text
VS Code 인터프리터가 .venv인가?: [예 / 아니오]
Notebook 커널이 .venv인가?: [예 / 아니오]
```

---

# 6. 샘플 데이터 생성 확인

프로젝트 루트에서 다음 명령을 실행한다.

```powershell
python scripts/generate_sample_data.py
```

생성 또는 확인해야 하는 파일은 다음과 같다.

```text
data/raw/customers.csv
data/raw/products.csv
data/raw/orders.csv
data/raw/order_items.csv
```

## 확인 결과

```text
customers.csv 존재: [예 / 아니오]
products.csv 존재: [예 / 아니오]
orders.csv 존재: [예 / 아니오]
order_items.csv 존재: [예 / 아니오]
```

---

# 7. Notebook에서 실제 실행 환경 확인

`ch02_environment_setup.ipynb`의 실행 환경 확인 셀을 실행한다.

```python
from pathlib import Path
import sys

print('Python 실행 파일:', sys.executable)
print('현재 작업 폴더:', Path.cwd())
```

## 실행 결과

```text
Notebook sys.executable: [직접 실행 후 기록]
Notebook Path.cwd(): [직접 실행 후 기록]
```

### 내가 확인할 점

- `sys.executable` 결과에 현재 프로젝트의 `.venv` 경로가 포함되어 있어야 한다.
- `Path.cwd()`는 상대경로 계산의 기준이므로 실제 실행 위치를 확인해야 한다.

### Evidence 2

> TODO: Notebook의 `sys.executable`과 `Path.cwd()` 출력이 함께 보이도록 캡처한다.

![Notebook 실행 환경 확인](./images/step02_notebook_environment.png)

---

# 8. 데이터 경로 확인

Notebook의 데이터 경로 설정 셀을 실행한다.

```python
PROJECT_ROOT = Path.cwd()
if not (PROJECT_ROOT / 'data' / 'raw').exists() and (PROJECT_ROOT.parent / 'data' / 'raw').exists():
    PROJECT_ROOT = PROJECT_ROOT.parent

DATA_DIR = PROJECT_ROOT / 'data' / 'raw'

print('프로젝트 루트:', PROJECT_ROOT)
print('데이터 폴더:', DATA_DIR)
print('데이터 폴더 존재 여부:', DATA_DIR.exists())
```

## 실행 결과

```text
PROJECT_ROOT: [직접 실행 후 기록]
DATA_DIR: [직접 실행 후 기록]
DATA_DIR.exists(): [직접 실행 후 기록]
```

정상 완료 기준은 다음과 같다.

```text
DATA_DIR.exists() == True
```

---

# 9. `customers.csv` 불러오기

Notebook에서 다음 코드를 실행한다.

```python
customers_path = DATA_DIR / 'customers.csv'
customers = pd.read_csv(customers_path)
customers.head()
```

## 실행 결과

```text
customers.head() 정상 출력 여부: [예 / 아니오]
FileNotFoundError 발생 여부: [없음 / 있음]
ModuleNotFoundError 발생 여부: [없음 / 있음]
```

### 내가 이해한 점

`customers.head()`가 정상적으로 출력되면 Notebook, 커널, 설치된 패키지, 데이터 경로가 서로 정상적으로 연결된 것으로 볼 수 있다.

### Evidence 3

> TODO: `DATA_DIR.exists() == True`와 `customers.head()` 결과가 함께 보이도록 캡처한다.

![데이터 경로와 customers 출력](./images/step03_customers_head.png)

---

# 10. 데이터 기본 구조 확인

Notebook에서 다음 코드를 실행한다.

```python
print('데이터 크기:', customers.shape)
print('컬럼명:', customers.columns.tolist())
customers.info()
```

## 실행 결과

```text
customers.shape: [직접 실행 후 기록]
컬럼명: [직접 실행 후 기록]
customers.info() 실행 여부: [정상 / 오류]
```

### Evidence 4

> TODO: `customers.shape`, 컬럼 목록, `customers.info()`의 핵심 부분이 보이도록 캡처한다.

![customers 기본 구조 확인](./images/step04_customers_structure.png)

---

# 11. `.env`와 Secret 보호 확인

현재 저장소의 `.gitignore`에는 다음 항목을 포함한다.

```text
.env
*.env
!*.env.example
.venv/
__pycache__/
.ipynb_checkpoints/
```

Git 추적 여부를 다음 명령으로 확인한다.

```powershell
git status
git ls-files .env
```

## 실행 결과

```text
.env가 Git 추적 대상인가?: [아니오가 정상]
`git ls-files .env` 출력: [비어 있음이 정상]
```

### 내가 이해한 점

실제 API Key나 비밀번호는 `.env`에 저장하고 GitHub에는 올리지 않는다. `.env.example`에는 변수 이름이나 예시 형식만 남길 수 있다. 이미 Secret을 원격 저장소에 공개했다면 파일 삭제만으로 끝나는 것이 아니라 해당 Key를 폐기하거나 재발급해야 한다.

### Evidence 5

> TODO: 실제 Secret 값은 보이지 않도록 하고, `.env`가 Git 추적 대상이 아님을 확인한 화면을 캡처한다.

![env Git 추적 제외 확인](./images/step05_env_gitignore.png)

---

# 12. 오류를 LLM에 질문할 때의 안전한 방식

오류가 발생했다면 다음처럼 검증 가능한 정보를 제공하되 민감정보는 제거한다.

```text
운영체제: Windows
편집기: VS Code
현재 작업 폴더: [Path.cwd() 결과]
Python 실행 파일: [sys.executable 결과]
실행한 명령 또는 코드: [...]
오류 메시지: [민감정보 제거 후 붙여넣기]

초보자가 이해할 수 있게 원인을 설명하고,
영향이 작은 확인 방법부터 순서대로 알려 주세요.
```

### 내가 이해한 점

단순히 "안 됩니다"라고 질문하는 것보다 실행 환경, 작업 폴더, 실제 Python 경로, 실행 코드, 오류 메시지를 함께 제공해야 원인을 검증하기 쉽다. API Key, Access Token, 비밀번호, 개인정보, 내부 URL은 제거해야 한다.

---

# 13. Chapter 02 최종 정리

이번 Chapter에서 가장 중요하다고 생각한 것은 **같은 Python 환경을 끝까지 사용하고 있는지 직접 확인하는 것**이다.

터미널에 `.venv`가 표시된다고 해서 Notebook이 자동으로 같은 환경을 사용하는 것은 아니다. 따라서 다음 세 가지를 각각 확인해야 한다.

```text
터미널에서 사용하는 Python
VS Code가 선택한 Python 인터프리터
Jupyter Notebook이 사용하는 커널
```

또한 `FileNotFoundError`가 발생하면 무작정 경로 문자열을 바꾸기보다 `Path.cwd()`와 실제 데이터 파일 위치를 먼저 확인해야 한다. `ModuleNotFoundError`가 발생하면 패키지를 설치한 Python과 Notebook 커널이 같은 환경인지 먼저 확인해야 한다.

---

# 14. 최종 Evidence 목록

수업 자료에서 요구하는 Chapter 02 완료 Evidence를 다음과 같이 정리한다.

| 번호 | Evidence | 확인 상태 |
| --- | --- | --- |
| 1 | 터미널의 Python 실행 파일 경로 | [ ] |
| 2 | Notebook의 `sys.executable` 결과 | [ ] |
| 3 | Notebook의 `Path.cwd()` 결과 | [ ] |
| 4 | `DATA_DIR.exists()`가 `True` | [ ] |
| 5 | `customers.head()` 정상 출력 | [ ] |
| 6 | 데이터 `shape`와 컬럼 목록 | [ ] |
| 7 | `.env`가 Git 추적 대상이 아님 | [ ] |

---

# 15. 제출 전 체크리스트

- [ ] 프로젝트 루트에서 작업했다.
- [ ] `.venv`를 생성하고 활성화했다.
- [ ] 터미널의 `sys.executable` 경로가 `.venv`를 가리킨다.
- [ ] `requirements.txt` 설치를 완료했다.
- [ ] VS Code Python 인터프리터를 `.venv`로 선택했다.
- [ ] 샘플 CSV 4개가 `data/raw/`에 존재한다.
- [ ] `notebooks/ch02_environment_setup.ipynb`를 열었다.
- [ ] Notebook 커널을 `.venv`로 선택했다.
- [ ] Notebook의 `sys.executable`에 `.venv`가 포함된다.
- [ ] `Path.cwd()` 결과를 확인했다.
- [ ] `DATA_DIR.exists()`가 `True`이다.
- [ ] `customers.head()`가 정상 표시된다.
- [ ] `customers.shape`, 컬럼명, `info()`를 확인했다.
- [ ] `.env`가 Git 추적 대상이 아니다.
- [ ] Evidence 이미지에 API Key, Token, 비밀번호 등 민감정보가 없다.
- [ ] GitHub에서 Markdown과 이미지가 정상적으로 표시된다.

---

## 교수자 확인용 수행 상태

- [ ] COMPLETE
- [x] PARTIAL

현재 Chapter 02에 필요한 파일과 제출 문서 구조는 준비되어 있다.  
로컬 VS Code에서 `.venv` 및 Notebook을 직접 실행하고 실제 출력값과 Evidence 이미지를 추가한 뒤 `COMPLETE`로 변경한다.
