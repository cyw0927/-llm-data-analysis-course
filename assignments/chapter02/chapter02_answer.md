# Chapter 02 확장 실습 답안

> **과제:** 데이터와 DBMS의 기본 개념  
> **작성 위치:** `assignments/chapter02/chapter02_answer.md`  
> **이미지 위치:** `assignments/chapter02/images/`

---

## 제출 전 개인정보 주의

```text
GitHub 계정 또는 별칭: cyw0927
과제 작성일: 2026-09-03
사용한 AI 도구: ChatGPT
```

> 실제 비밀번호, API Key, 전체 DB 접속 URL, 개인정보가 포함된 화면은 올리지 않는다.

---

# 1. PostgreSQL에서 현재 위치 확인

## 1-1. 실행한 SQL

```sql
SELECT version();
SELECT current_database();
SELECT current_user;
SELECT current_schema();
SHOW search_path;
```

## 1-2. 실행 결과 기록

```text
PostgreSQL 버전:
현재 데이터베이스:
현재 사용자:
현재 스키마:
search_path:
```

## 1-3. 구조를 내 말로 설명

```text
PostgreSQL은:

현재 접속한 데이터베이스는:

스키마는:

DBeaver 또는 psql 같은 도구는:
```

## 1-4. 계층 구조 완성

```text
사용자
→ ____________________
→ PostgreSQL DBMS
→ ____________________
→ ____________________
→ ____________________
→ 행 / 열
```

## 1-5. 증거 화면

![PostgreSQL 현재 위치 확인](./images/step01_environment.png)

---

# 2. 데이터베이스 안의 스키마와 테이블 관찰

## 2-1. 스키마 조회 결과

```sql
SELECT schema_name
FROM information_schema.schemata
ORDER BY schema_name;
```

```text
1.
2.
3.
```

### `public`은 무엇인가요?

```text
나의 설명:
```

### 데이터베이스와 스키마는 같은 것인가요?

```text
나의 설명:
```

## 2-2. 현재 보이는 테이블 조회

```sql
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_type = 'BASE TABLE'
  AND table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY table_schema, table_name;
```

```text
조회된 사용자 테이블 수 또는 눈에 띈 테이블:

아직 테이블이 거의 없어도 괜찮은 이유:
```

## 2-3. 관찰 정리

```text
PostgreSQL 서버 안에는 여러 ____________________가 있을 수 있다.
한 데이터베이스 안에는 여러 ____________________가 있을 수 있다.
스키마 안에는 테이블과 같은 ____________________가 존재한다.
```

---

# 3. TEMP TABLE로 테이블·행·열·키 직접 확인

## 3-1. 임시 테이블 생성 완료 확인

- [ ] `ch02_students` 생성
- [ ] `ch02_courses` 생성
- [ ] `ch02_enrollments` 생성

| 테이블 | 한 행의 의미 |
| --- | --- |
| `ch02_students` |  |
| `ch02_courses` |  |
| `ch02_enrollments` |  |

## 3-2. 열의 의미 확인

### `ch02_students`

| 열 | 값의 의미 | 내부 식별자 / 업무 식별자 / 일반 속성 |
| --- | --- | --- |
| `id` |  |  |
| `student_number` |  |  |
| `name` |  |  |
| `major` |  |  |

### `ch02_enrollments`

| 열 | 값의 의미 | PK / FK / 일반 속성 |
| --- | --- | --- |
| `id` |  |  |
| `student_id` |  |  |
| `course_id` |  |  |
| `status` |  |  |

## 3-3. 입력된 행 수

```text
students 행 수:
courses 행 수:
enrollments 행 수:
```

## 3-4. 내부 식별자와 업무 식별자

```text
students.id가 필요한 이유:

student_number가 필요한 이유:

둘을 항상 같은 값으로 사용하지 않아도 되는 이유:
```

## 3-5. 숫자처럼 보이는 학번을 문자열로 저장한 이유

```text
나의 설명:
```

---

# 4. 테이블과 조회 결과는 다르다

## 4-1. 원본 테이블 행 수

```text
ch02_students 전체 행 수:
```

## 4-2. 일부 열만 조회

```sql
SELECT name, major
FROM ch02_students
ORDER BY id;
```

```text
원본 테이블의 열 수와 조회 결과의 열 수가 다른 이유:
```

## 4-3. 조건을 적용한 조회

```sql
SELECT id, student_number, name, major
FROM ch02_students
WHERE major = '컴퓨터공학'
ORDER BY id;
```

```text
원본 테이블 행 수:
조회 결과 행 수:
원본 테이블의 데이터가 삭제된 것인가?:
그렇게 판단한 이유:
```

## 4-4. 정렬 결과 비교

```sql
SELECT id, name
FROM ch02_students
ORDER BY name ASC;

SELECT id, name
FROM ch02_students
ORDER BY name DESC;
```

```text
ASC 결과의 첫 학생:
DESC 결과의 첫 학생:

이 실험을 통해 ORDER BY에 대해 알게 된 점:
```

## 4-5. 증거 화면

![테이블과 조회 결과 비교](./images/step04_result_set.png)

---

# 5. PK와 FK를 실제로 관찰

## 5-1. 정상 데이터의 관계 읽기

```sql
SELECT
    e.id AS enrollment_id,
    s.name AS student_name,
    c.title AS course_title,
    e.status
FROM ch02_enrollments AS e
JOIN ch02_students AS s
    ON s.id = e.student_id
JOIN ch02_courses AS c
    ON c.id = e.course_id
ORDER BY e.id;
```

```text
한 행이 의미하는 것:

같은 student_id가 여러 enrollment 행에서 반복될 수 있는 이유:

같은 course_id가 여러 enrollment 행에서 반복될 수 있는 이유:
```

## 5-2. 기본키 중복 오류 관찰

```text
실행 성공 / 실패:
오류 메시지에서 확인한 핵심 단어:
왜 실패했다고 생각하는가:
```

## 5-3. 존재하지 않는 학생을 참조하는 FK 오류 관찰

```text
실행 성공 / 실패:
오류 메시지에서 확인한 핵심 단어:
왜 실패했다고 생각하는가:
```

## 5-4. PK와 FK의 차이 정리

```text
PK는 _________________________________________________ 하기 위한 키이다.

FK는 _________________________________________________ 하기 위한 키이다.

FK 값이 여러 행에서 반복될 수 있는 이유는
______________________________________________________ 때문이다.
```

## 5-5. 증거 화면

![PK와 FK 관찰](./images/step05_pk_fk.png)

---

# 6. 관계와 카디널리티를 자연어로 설명

```text
학생 한 명은 여러 수강신청을 가질 수 있는가?:

강의 한 개는 여러 수강신청을 가질 수 있는가?:

수강신청 한 건은 학생 몇 명을 참조하는가?:

수강신청 한 건은 강의 몇 개를 참조하는가?:
```

```text
students 1 ── ______ enrollments ______ ── 1 courses
```

### 학생과 강의가 N:M 관계라고 볼 수 있는 이유

```text
나의 설명:
```

---

# 7. AI가 만든 테이블 구조 직접 검토

## 7-1. AI에게 묻기 전에 내가 먼저 찾은 문제

```sql
CREATE TABLE student_courses (
    student_name VARCHAR(50),
    student_email VARCHAR(100),
    course_title VARCHAR(100),
    instructor_name VARCHAR(50)
);
```

```text
문제 1.
문제 2.
문제 3.
문제 4.
```

## 7-2. AI 검토 요청 프롬프트

```text

```

## 7-3. AI 제안과 나의 판단

| AI의 지적 또는 제안 | 동의 / 수정 / 보류 | 나의 근거 |
| --- | --- | --- |
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |

## 7-4. 본문과 대조한 항목

```text
AI가 설명한 내용:

본문에서 확인한 내용:

일치 / 부분 일치 / 수정 필요:

내가 최종적으로 이해한 내용:
```

## 7-5. 증거 화면

![AI 구조 검토](./images/step07_ai_review.png)

---

# 8. 개인 서비스 아이디어를 DB 용어로 다시 표현

## 8-1. 서비스 기본 정보

```text
서비스 이름:
서비스 목적:
```

## 8-2. PostgreSQL 구조 후보

```text
데이터베이스 이름 후보:
스키마 이름 후보:
```

## 8-3. 테이블 후보와 한 행 의미

| 테이블 후보 | 한 행의 의미 | 내부 ID 후보 | 업무 식별자 후보 |
| --- | --- | --- | --- |
|  |  |  |  |
|  |  |  |  |
|  |  |  |  |

## 8-4. FK 후보

```text
1. ________.________ → ________.________
   이유:

2. ________.________ → ________.________
   이유:
```

## 8-5. 자연어 관계 문장

```text
1.
2.
3.
```

## 8-6. 아직 확정하지 않을 정책

```text
Q1.
Q2.
Q3.
```

---

# 9. AI를 개인 구조의 검토자로 사용

## 9-1. 사용한 프롬프트

```text

```

## 9-2. AI가 질문한 내용 중 유용했던 것

```text
1.
2.
3.
```

## 9-3. AI가 너무 빨리 결정한 내용 또는 내가 보류한 내용

```text
1.
2.
```

## 9-4. 검토 후 수정한 구조

| 수정 전 | 수정 후 | 수정 이유 |
| --- | --- | --- |
|  |  |  |
|  |  |  |
|  |  |  |

---

# 10. 최종 개념 정리

```text
PostgreSQL은 ________________________________________________ 이다.

DBeaver 또는 psql은 _________________________________________ 이다.

데이터베이스와 스키마의 차이는 ______________________________ 이다.

테이블 한 행은 ______________________________________________ 이다.

조회 결과가 원본 테이블과 다른 이유는 ________________________ 이다.

내부 식별자와 업무 식별자의 차이는 ___________________________ 이다.

PK는 _______________________________________________________ 이다.

FK는 _______________________________________________________ 이다.
```

---

# 11. 이번 Chapter에서 새롭게 알게 된 점

```text
1.
2.
3.
```

## 아직 헷갈리는 내용

```text
1.
2.
```

## AI에게 다시 질문하고 싶은 내용

```text

```

---

# 12. 제출 전 자기 점검

- [ ] PostgreSQL에서 현재 database / schema / search_path를 확인했다.
- [ ] DBMS, database, schema, table을 구분해서 설명할 수 있다.
- [ ] TEMP TABLE 3개를 생성하고 직접 데이터를 조회했다.
- [ ] 각 테이블의 한 행 의미를 작성했다.
- [ ] 테이블과 조회 결과가 다르다는 것을 실제 SQL로 확인했다.
- [ ] `ORDER BY`를 사용하지 않으면 업무 순서를 가정하면 안 된다는 점을 이해했다.
- [ ] 내부 식별자와 업무 식별자의 차이를 설명할 수 있다.
- [ ] PK 중복 입력 실패를 직접 확인했다.
- [ ] 존재하지 않는 FK 참조 실패를 직접 확인했다.
- [ ] FK 값이 반복될 수 있는 이유를 설명할 수 있다.
- [ ] AI가 만든 테이블을 내가 먼저 검토했다.
- [ ] AI 설명 중 최소 하나를 본문과 대조했다.
- [ ] 개인 서비스의 테이블 후보를 3개 이상 작성했다.
- [ ] 개인 서비스의 FK 후보와 미확정 정책을 기록했다.
- [ ] 실제 비밀번호·API Key·민감한 접속 정보가 포함되지 않았는지 확인했다.
- [ ] 이미지 링크가 GitHub에서 정상적으로 보이는지 확인했다.

---

# 13. GitHub 제출 정보

답안 파일:

```text
assignments/chapter02/chapter02_answer.md
```

이미지 폴더:

```text
assignments/chapter02/images/
```

최종 제출 URL:

```text
https://github.com/cyw0927/-llm-data-analysis-course/blob/main/assignments/chapter02/chapter02_answer.md
```

## 최종 확인

- [ ] 위 URL을 로그아웃 상태 또는 다른 브라우저에서 열어도 확인 가능하다.
- [ ] Markdown이 정상 렌더링된다.
- [ ] 이미지가 깨지지 않는다.
- [ ] LMS에 교수자 템플릿 URL이 아니라 **내 답안 파일 URL**을 제출했다.
