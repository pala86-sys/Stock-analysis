"""台股多維度全方位觀測儀 — Web 版（FastAPI + Render）"""

from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from report_export import report_download_filename
from web_service import (
    build_report_pdf,
    get_stock_suggestions,
    resolve_stock,
    run_analysis,
)

ROOT = Path(__file__).parent
STATIC = ROOT / "static"

app = FastAPI(
    title="台股多維度全方位觀測儀",
    description="台股多維度分析 Web 版",
    version="1.0.0",
)

# Android APK（Capacitor WebView）從 https://localhost 呼叫遠端 API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    stock_id: str = Field(default="", description="股票代號")
    query: str = Field(default="", description="代號或名稱")
    display_days: int = Field(default=90, ge=30, le=180)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/stocks/search")
def api_search_stocks(q: str = Query("", min_length=0)):
    q = q.strip()
    if not q:
        return {"results": []}
    return {"results": get_stock_suggestions(q)}


@app.post("/api/analyze")
def api_analyze(body: AnalyzeRequest):
    stock_id = body.stock_id.strip() or resolve_stock(body.query) or ""
    if not stock_id:
        raise HTTPException(status_code=400, detail="找不到符合的股票，請輸入代號或從清單選擇")

    try:
        result = run_analysis(stock_id, display_days=body.display_days)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"分析失敗：{exc}") from exc


@app.post("/api/report")
def api_report(body: AnalyzeRequest):
    stock_id = body.stock_id.strip() or resolve_stock(body.query) or ""
    if not stock_id:
        raise HTTPException(status_code=400, detail="找不到符合的股票")

    try:
        result = run_analysis(stock_id, display_days=body.display_days)
        pdf_bytes = build_report_pdf(stock_id, result)
        advice = result.get("advice") or {}
        filename = report_download_filename(stock_id, advice)
        ascii_name = f"{stock_id}_report.pdf"
        encoded = quote(filename)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{encoded}'
                ),
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"報告產生失敗：{exc}") from exc


@app.get("/")
def index():
    index_file = STATIC / "index.html"
    if not index_file.exists():
        return JSONResponse({"detail": "frontend not deployed"}, status_code=503)
    return FileResponse(index_file)


def _static_file(name: str, media_type: str):
    path = STATIC / name
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"missing {name}")
    return FileResponse(path, media_type=media_type)


@app.get("/app.css")
def app_css():
    return _static_file("app.css", "text/css")


@app.get("/app.js")
def app_js():
    return _static_file("app.js", "application/javascript")


@app.get("/config.js")
def config_js():
    return _static_file("config.js", "application/javascript")


@app.get("/chart.js")
def chart_js():
    return _static_file("chart.js", "application/javascript")


if STATIC.exists():
    app.mount("/assets", StaticFiles(directory=STATIC), name="assets")
