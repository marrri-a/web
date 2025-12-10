from fastapi import FastAPI
from app.pages import router as pages_router
from app import routes
from app.storage import store

app = FastAPI(title="Blog API (11 класс)", version="1.0")

app.include_router(pages_router)
app.include_router(routes.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
async def on_startup():
    store.load_from_json()


@app.on_event("shutdown")
async def on_shutdown():
    store.save_to_json()

# запуск:
# cd /Users/mariazeleznova/Blog-api
# source .venv/bin/activate
# uvicorn main:app --reload --host 0.0.0.0 --port 8000
# http://localhost:8000
