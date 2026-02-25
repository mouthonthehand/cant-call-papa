# CANT-CALL-PAPA (아버지를 아버지라 부르지 못하고)

> *"아버지를 아버지라 부르지 못하고, ChatGPT를 ChatGPT라 쓰지 못하는..."*

폐쇄 사내망에서 근무하며 외부 시스템을 자유롭게 활용하지 못하는 모든 직장인을 위한 프로젝트입니다.

홍길동이 서자라는 이유로 아버지를 아버지라 부르지 못했듯, 우리는 보안이라는 굴레 속에서 외부 AI·클라우드 서비스를 마음껏 쓰지 못합니다. 그래서 이 프로젝트의 이름을 **CANT-CALL-PAPA**라 지었습니다.

---

## 이런 분들을 위해 만들었습니다

- 사내 보안 정책 때문에 외부 LLM에 업무 쿼리를 그대로 붙여넣지 못하는 분
- DB 테이블명, 컬럼명이 사내 기밀이라 외부에 노출할 수 없는 분
- 그럼에도 LLM의 도움을 받아 SQL을 작성하고 싶은 분

---

## 주요 기능

### 쿼리 마스킹 / 복원

SQL 쿼리의 **스키마명·테이블명·컬럼명**을 자동으로 식별하여 임의의 별칭(`SCH_001`, `TBL_001`, `COL_001` 등)으로 치환합니다.

**사용 흐름:**

1. **마스킹** — 원본 SQL을 입력하면 식별자가 마스킹된 안전한 쿼리가 생성됩니다.
2. **외부 활용** — 마스킹된 쿼리를 외부 LLM(ChatGPT 등)에 붙여넣어 도움을 받습니다.
3. **복원** — LLM이 수정한 쿼리를 다시 붙여넣으면 원본 식별자로 자동 복원됩니다.

이렇게 하면 사내 DB 구조를 외부에 노출하지 않으면서도 LLM의 도움을 받을 수 있습니다.

### 마스킹 이력 관리

모든 마스킹·복원 작업은 이력으로 저장되어, 이전에 수행한 작업을 언제든 다시 확인할 수 있습니다.

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| Backend | Python, FastAPI |
| Frontend | Jinja2 Templates, HTML/CSS |
| Database | SQLite |
| Server | Uvicorn |

---

## 설치 및 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 서버 실행
python main.py
```

서버가 실행되면 브라우저에서 `http://localhost:8000` 으로 접속합니다.

---

## 프로젝트 구조

```
cant-call-papa/
├── main.py              # FastAPI 애플리케이션 (라우팅)
├── query_masker.py      # SQL 쿼리 마스킹·복원 엔진
├── database.py          # SQLite DB 관리
├── requirements.txt     # Python 의존성
├── work_helper.db       # SQLite DB 파일 (자동 생성)
├── templates/           # Jinja2 HTML 템플릿
│   ├── base.html
│   ├── index.html
│   ├── query_mask.html
│   ├── history.html
│   └── history_detail.html
└── static/
    └── style.css
```

---

## 라이선스

이 프로젝트는 보안의 굴레에 휘둘리는 모든 직장인에게 자유롭게 공개됩니다.

---

> *홍길동은 끝내 활빈당을 이끌고 율도국의 왕이 되었습니다.*
> *우리도 언젠가는 아버지를 아버지라 부를 수 있는 날이 오길...*
