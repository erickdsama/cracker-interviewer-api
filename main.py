from fastapi import FastAPI
# Trigger reload
from contextlib import asynccontextmanager
from .core.database import init_db
from .routers import auth, sessions, context, speech, code

from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Handle GCP Credentials from Env Var
    import os
    gcp_json = os.getenv("GCP_SERVICE_ACCOUNT_JSON")
    if gcp_json:
        with open("gcp_key.json", "w") as f:
            f.write(gcp_json)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gcp_key.json"

    init_db()
    from .services.knowledge_base import seed_knowledge_base
    seed_knowledge_base()
    yield

app = FastAPI(title="Recruiting Practice API", lifespan=lifespan)

import os
origins = os.getenv("ALLOW_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add ProxyHeadersMiddleware to trust X-Forwarded-Proto from reverse proxy (Coolify/Traefik)
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(context.router)
app.include_router(speech.router)
app.include_router(code.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Recruiting Practice API"}
