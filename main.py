import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

from src.service import analyze_transaction, chat_transaction
from src.llm import generate_chat_result

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="SettleLens API")


class ChatRequest(BaseModel):
    transaction_id: Optional[str] = None
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
        if request.transaction_id and request.transaction_id.strip():
            # Transaction-specific question — use evidence grounding
            answer = chat_transaction(
                request.transaction_id.strip(),
                request.question,
                data_dir="data"
            )
        else:
            # General question — no evidence packet needed
            answer = generate_chat_result(None, request.question)
        return {"answer": answer}
    except Exception as e:
        logging.exception("Chat generation failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve the dashboard at /dashboard
app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")

# Serve root-level static assets
app.mount("/", StaticFiles(directory=".", html=True), name="root")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
