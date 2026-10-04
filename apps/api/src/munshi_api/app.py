from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from munshi_api.routers import audit, janitor, sources, sources_catalog, wiki_catalog, summarizer

app = FastAPI(title="Mat Munshi Control Plane API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(janitor.router)
app.include_router(sources.router)
app.include_router(audit.router)
app.include_router(wiki_catalog.router)
app.include_router(sources_catalog.router)
app.include_router(summarizer.router)


@app.get("/api/ping")
def ping():
    return {"status": "ok", "service": "munshi-api"}