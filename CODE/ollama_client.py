import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2")

def ensure_model(model: str) -> None:
    # Check if model exists
    models_url = f"{OLLAMA_BASE_URL}/api/tags"
    resp = requests.get(models_url)
    if resp.status_code == 200:
        models = resp.json().get("models", [])
        if any(m.get("name") == model for m in models):
            return
    # Pull model if not present
    pull_url = f"{OLLAMA_BASE_URL}/api/pull"
    requests.post(pull_url, json={"name": model})

def query_ollama(prompt: str, model: str = None) -> str:
    model = model or OLLAMA_MODEL
    ensure_model(model)
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {"model": model, "prompt": prompt}
    response = requests.post(url, json=payload, stream=True)
    import sys
    fragments = []
    for line in response.iter_lines():
        if line:
            try:
                decoded = line.decode('utf-8')
                obj = json.loads(decoded)
                fragment = obj.get("response", "")
                fragments.append(fragment)
            except Exception:
                continue
    answer = "".join(fragments)
    return {"response": answer}
