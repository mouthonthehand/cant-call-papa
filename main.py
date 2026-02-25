from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os

from database import init_db, save_encryption, save_restoration, get_history_list, get_history_detail
from query_masker import mask_query, unmask_query

app = FastAPI(title="Work Helper")

BASE_DIR = os.path.dirname(__file__)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

init_db()


# ─── 대시보드 ───────────────────────────────────────────────
FEATURES = [
    {
        "title": "쿼리 마스킹",
        "description": "SQL 쿼리의 테이블명·컬럼명·스키마를 임의 값으로 치환하고, 외부 LLM 결과를 원본으로 복원합니다.",
        "url": "/query-mask",
        "icon": "🔒",
    },
    {
        "title": "마스킹 이력",
        "description": "이전에 수행한 쿼리 마스킹·복원 이력을 확인합니다.",
        "url": "/query-mask/history",
        "icon": "📋",
    },
]


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "features": FEATURES})


# ─── 쿼리 마스킹 ────────────────────────────────────────────
@app.get("/query-mask", response_class=HTMLResponse)
async def query_mask_page(request: Request):
    return templates.TemplateResponse("query_mask.html", {"request": request})


@app.post("/query-mask/encrypt", response_class=HTMLResponse)
async def encrypt_query(request: Request, original_query: str = Form(...)):
    masked, mapping = mask_query(original_query)
    history_id = save_encryption(original_query, masked, mapping)
    return templates.TemplateResponse("query_mask.html", {
        "request": request,
        "step": "encrypted",
        "original_query": original_query,
        "masked_query": masked,
        "history_id": history_id,
        "mapping": mapping,
    })


@app.post("/query-mask/decrypt", response_class=HTMLResponse)
async def decrypt_query(request: Request, modified_query: str = Form(...), history_id: int = Form(...)):
    detail = get_history_detail(history_id)
    if not detail:
        return templates.TemplateResponse("query_mask.html", {
            "request": request,
            "error": "해당 이력을 찾을 수 없습니다.",
        })

    restored = unmask_query(modified_query, detail["mapping"])
    save_restoration(history_id, restored)

    return templates.TemplateResponse("query_mask.html", {
        "request": request,
        "step": "decrypted",
        "modified_query": modified_query,
        "restored_query": restored,
        "history_id": history_id,
    })


# ─── 이력 ───────────────────────────────────────────────────
@app.get("/query-mask/history", response_class=HTMLResponse)
async def history_list(request: Request):
    rows = get_history_list()
    return templates.TemplateResponse("history.html", {"request": request, "rows": rows})


@app.get("/query-mask/history/{history_id}", response_class=HTMLResponse)
async def history_detail(request: Request, history_id: int):
    detail = get_history_detail(history_id)
    if not detail:
        return templates.TemplateResponse("history.html", {
            "request": request,
            "rows": get_history_list(),
            "error": "해당 이력을 찾을 수 없습니다.",
        })
    return templates.TemplateResponse("history_detail.html", {"request": request, "detail": detail})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
