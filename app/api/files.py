# app/api/files.py

from fastapi import (
    APIRouter,
    Depends,
    Query,
    File as FastAPIFile,
    HTTPException,
    UploadFile,
)

from fastapi.responses import Response

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user

from app.models.user import User
from app.models.upload_job import UploadJob

from app.schemas.file import FileListResponse, FileResponse
from app.schemas.upload_job import UploadJobResponse

from app.services.file_service import FileService

from app.services.staging_storage import (
    StagingStorage,
)

from app.services.telegram_storage import (
    TelegramStorageError,
)
import shutil


router = APIRouter(
    prefix="/api/files",
    tags=["Files"],
)


# =========================================================
# UPLOAD
# =========================================================

@router.post(
    "",
    response_model=UploadJobResponse,
)
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):

    staging = StagingStorage()

    staging_path = None

    try:

        # -------------------------------------------------
        # ACCOUNT VALIDATION
        # -------------------------------------------------

        if not current_user.is_active:

            raise HTTPException(
                status_code=403,
                detail="Account is disabled.",
            )

        if not current_user.is_verified:

            raise HTTPException(
                status_code=403,
                detail=(
                    "Email address is not verified."
                ),
            )

        # -------------------------------------------------
        # PLAN
        # -------------------------------------------------

        if not current_user.plan:

            raise HTTPException(
                status_code=400,
                detail="No active plan.",
            )

        plan = current_user.plan

                # -------------------------------------------------
        # TEMPORARY STORAGE CHECK
        # -------------------------------------------------

        # Leave a safety buffer so the system does not
        # completely consume the filesystem.
        MIN_FREE_SPACE = 500 * 1024 * 1024  # 500 MB

        #staging_dir = staging.staging_dir

        free_space = shutil.disk_usage(
            staging.base_path
        ).free

        if free_space < MIN_FREE_SPACE:
            raise HTTPException(
                status_code=507,
                detail=(
                    "Temporary upload storage is full. "
                    "Please try again later."
                ),
            )


        # -------------------------------------------------
        # STAGE FILE
        # -------------------------------------------------

        staging_path, file_size = (
            await staging.save_upload(
                file
            )
        )

        # -------------------------------------------------
        # EMPTY FILE
        # -------------------------------------------------

        if file_size <= 0:

            staging.delete(
                staging_path
            )

            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty.",
            )

        # -------------------------------------------------
        # PLAN FILE SIZE LIMIT
        # -------------------------------------------------

        if (
            file_size
            > plan.max_file_size_bytes
        ):

            staging.delete(
                staging_path
            )

            max_mb = (
                plan.max_file_size_bytes
                / 1024
                / 1024
            )

            raise HTTPException(
                status_code=413,
                detail=(
                    f"File is too large for "
                    f"your {plan.name} plan. "
                    f"Maximum file size is "
                    f"{max_mb:.2f} MB."
                ),
            )

        # -------------------------------------------------
        # STORAGE QUOTA
        # -------------------------------------------------
        #
        # This first check prevents obvious over-quota
        # uploads.
        #
        # The worker performs the authoritative check
        # again before committing the stored file.
        # -------------------------------------------------

        if (
            current_user.storage_used
            + file_size
            > plan.storage_quota_bytes
        ):

            staging.delete(
                staging_path
            )

            raise HTTPException(
                status_code=413,
                detail="Storage quota exceeded.",
            )

        # -------------------------------------------------
        # CREATE UPLOAD JOB
        # -------------------------------------------------

        job = UploadJob(
            user_id=current_user.id,

            staging_path=staging_path,

            original_filename=(
                file.filename
                or "file"
            ),

            file_size=file_size,

            mime_type=file.content_type,

            status="QUEUED",

            attempts=0,

            max_attempts=10,

            storage_backend="LOCAL_BOT",
        )

        db.add(job)

        db.commit()

        db.refresh(job)

        # -------------------------------------------------
        # RETURN JOB
        # -------------------------------------------------

        return UploadJobResponse(
            id=job.id,
            status=job.status,
            filename=job.original_filename,
            size=job.file_size,
            attempts=job.attempts,
            error=job.last_error,
            file_id=job.file_id,
        )

    except HTTPException:
        raise

    except OSError as exc:

        # Disk is full while staging the upload
        if exc.errno == 28:
            if staging_path:
                staging.delete(staging_path)

            db.rollback()

            print(
                "UPLOAD STORAGE FULL: "
                f"{type(exc).__name__}: {exc}"
            )

            raise HTTPException(
                status_code=507,
                detail=(
                    "Temporary upload storage is full. "
                    "Please try again later."
                ),
            )

        # Other operating-system errors
        if staging_path:
            staging.delete(staging_path)

        db.rollback()

        print(
            "UPLOAD OS ERROR: "
            f"{type(exc).__name__}: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to stage upload.",
        )

    except Exception as exc:

        if staging_path:
            staging.delete(staging_path)

        db.rollback()

        print(
            "UPLOAD STAGING ERROR: "
            f"{type(exc).__name__}: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to stage upload.",
        )



# =========================================================
# LIST FILES
# =========================================================

@router.get(
    "",
    response_model=FileListResponse,
)
async def list_files(
    page: int = Query(
        1,
        ge=1,
    ),
    page_size: int = Query(
        50,
        ge=1,
        le=100,
    ),
    search: str | None = Query(
        None,
        max_length=200,
    ),
    status: str | None = Query(
        None,
        max_length=20,
    ),
    sort: str = Query(
        "created_at",
    ),
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
):

    service = FileService(db)

    return service.list_files(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        search=search,
        status=status,
        sort=sort,
    )


# =========================================================
# UPLOAD JOB STATUS
# =========================================================

@router.get(
    "/jobs/{job_id}",
    response_model=UploadJobResponse,
)
def get_upload_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):

    job = (
        db.query(UploadJob)
        .filter(
            UploadJob.id == job_id,
            UploadJob.user_id
            == current_user.id,
        )
        .first()
    )

    if not job:

        raise HTTPException(
            status_code=404,
            detail="Upload job not found.",
        )

    return UploadJobResponse(
        id=job.id,
        status=job.status,
        filename=job.original_filename,
        size=job.file_size,
        attempts=job.attempts,
        error=job.last_error,
        file_id=job.file_id,
    )


# =========================================================
# GET FILE
# =========================================================

@router.get(
    "/{file_id}",
    response_model=FileResponse,
)
def get_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):

    service = FileService(db)

    file = (
        service.file_repository
        .get_user_file(
            file_id=file_id,
            user_id=current_user.id,
        )
    )

    if not file:

        raise HTTPException(
            status_code=404,
            detail="File not found.",
        )

    return file


# =========================================================
# DOWNLOAD
# =========================================================

@router.get(
    "/{file_id}/download",
)
async def download_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):

    service = FileService(db)

    try:

        file, file_bytes = (
            await service.download(
                file_id=file_id,
                user_id=current_user.id,
            )
        )

    except FileNotFoundError:

        raise HTTPException(
            status_code=404,
            detail="File not found.",
        )

    except TelegramStorageError as exc:

        raise HTTPException(
            status_code=502,
            detail=(
                f"Telegram storage error: "
                f"{exc}"
            ),
        )

    return Response(
        content=file_bytes,

        media_type=(
            file.mime_type
            or "application/octet-stream"
        ),

        headers={
            "Content-Disposition": (
                'attachment; filename="'
                f'{file.name}'
                '"'
            )
        },
    )


# =========================================================
# DELETE
# =========================================================

@router.delete(
    "/{file_id}",
)
async def delete_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):

    service = FileService(db)

    try:

        await service.delete(
            file_id=file_id,
            user_id=current_user.id,
        )

    except FileNotFoundError:

        raise HTTPException(
            status_code=404,
            detail="File not found.",
        )

    except TelegramStorageError as exc:

        raise HTTPException(
            status_code=502,
            detail=(
                f"Telegram storage error: "
                f"{exc}"
            ),
        )

    return {
        "message": "File deleted successfully."
    }