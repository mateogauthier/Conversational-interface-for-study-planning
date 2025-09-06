from fastapi import FastAPI, UploadFile, File
from rag.rag_engine import retrieve_augmented_answer
from ollama_client import query_ollama
from file_utils import save_file, list_files

app = FastAPI()

@app.post("/llm-request/")
async def llm_request(prompt: str):
    response = query_ollama(prompt)
    return response

@app.post("/rag/")
async def rag_request(prompt: str):
    answer = retrieve_augmented_answer(prompt)
    return {"answer": answer}

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    path = save_file(file)
    return {"path": path}

@app.get("/files/")
async def get_files():
    files = list_files()
    return {"files": files}
