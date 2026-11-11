# app/main.py

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text
from app.core.database import engine

from app.api.channels import router as channels_router
from app.api.files import router as files_router
from app.api.auth import router as auth_router
from app.api.plans import router as plans_router
from app.api.subscriptions import router as subscriptions_router
from app.api.payments import router as payments_router
from app.api.paystack_webhook import router as paystack_webhook_router

from app.workers.upload_worker import UploadWorker


# =========================================================
# GLOBAL WORKER
# =========================================================

upload_worker_task: asyncio.Task | None = None


# =========================================================
# APPLICATION LIFESPAN
# =========================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    global upload_worker_task

    print("=" * 60)
    print("Starting Telegram Cloud Storage...")
    print("=" * 60)

    # -----------------------------------------------------
    # START UPLOAD WORKER
    # -----------------------------------------------------

    worker = UploadWorker()

    upload_worker_task = asyncio.create_task(
        worker.run()
    )

    print("Upload worker started.")

    try:

        yield

    finally:

        # -------------------------------------------------
        # SHUT DOWN WORKER
        # -------------------------------------------------

        print("Stopping upload worker...")

        if upload_worker_task:

            upload_worker_task.cancel()

            try:

                await upload_worker_task

            except asyncio.CancelledError:

                pass

        print("Upload worker stopped.")

        print("Application shutdown complete.")


# =========================================================
# FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="Telegram Cloud Storage",
    version="0.3.0",
    lifespan=lifespan,
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# =========================================================
# ROUTERS
# =========================================================

app.include_router(
    auth_router
)

app.include_router(
    channels_router
)

app.include_router(
    files_router
)

app.include_router(
    plans_router
)

app.include_router(
    subscriptions_router
)

app.include_router(
    payments_router
)

app.include_router(paystack_webhook_router)




# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health():

    try:

        # Actually test the database connection
        with engine.connect() as connection:

            connection.execute(text("SELECT 1"))

        return {
            "status": "ok",
            "database": "ok"
        }

    except Exception as e:

        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "database": "unavailable",
                "error": str(e)
            }
        )
