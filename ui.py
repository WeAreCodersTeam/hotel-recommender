# ui.py
from pathlib import Path
from fastapi import Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# ВАЖНО: импортируем существующий app из api.py, а не создаём новый
from api import app  # <-- здесь твой app = FastAPI(...)

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Раздача статики
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Простой health (под требования хакатона)
@app.get("/health")
def health():
    return {"status": "ok"}

# Главная страница
@app.get("/")
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

