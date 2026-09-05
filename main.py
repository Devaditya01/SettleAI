import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.service import analyze_transaction, chat_transaction

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="SettleLens API")


class ChatRequest(BaseModel):
    transaction_id: str
    question: str


@app.get("/api/analyze/{transaction_id}")
def api_analyze(transaction_id: str):
    try:
        result = analyze_transaction(transaction_id, data_dir="data")
        return result
    except Exception as e:
        logging.exception("Analysis failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
def api_chat(request: ChatRequest):
    try:
        answer = chat_transaction(request.transaction_id, request.question, data_dir="data")
        return {"answer": answer}
    except Exception as e:
        logging.exception("Chat generation failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve the dashboard at /dashboard
app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")

# Serve root-level static assets (index.html, login.html, etc.)
app.mount("/", StaticFiles(directory=".", html=True), name="root")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
