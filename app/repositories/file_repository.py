from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.file import File


class FileRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, file: File) -> File:
        self.db.add(file)
        self.db.commit()
        self.db.refresh(file)

        return file

    def get_by_id(
        self,
        file_id: str,
    ) -> File | None:
        return self.db.get(File, file_id)

    def get_user_file(
        self,
        file_id: str,
        user_id: str,
    ) -> File | None:

        result = self.db.execute(
            select(File).where(
                File.id == file_id,
                File.user_id == user_id,
                File.deleted_at.is_(None),
            )
        )

        return result.scalar_one_or_none()

    def list_user_files(
        self,
        user_id: str,
    ) -> list[File]:

        result = self.db.execute(
            select(File)
            .where(
                File.user_id == user_id,
                File.deleted_at.is_(None),
            )
            .order_by(File.created_at.desc())
        )

        return list(result.scalars().all())

    def get_user_files(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 50,
        search: str | None = None,
        status: str | None = None,
        sort: str = "created_at",
    ) -> tuple[list[File], int]:

        # -------------------------------------------------
        # VALIDATE PAGINATION
        # -------------------------------------------------

        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)

        offset = (page - 1) * page_size

        # -------------------------------------------------
        # BASE FILTER
        # -------------------------------------------------

        conditions = [
            File.user_id == user_id,
            File.deleted_at.is_(None),
        ]

        # -------------------------------------------------
        # SEARCH
        # -------------------------------------------------

        if search:
            conditions.append(
                File.name.ilike(f"%{search}%")
            )

        # -------------------------------------------------
        # STATUS
        # -------------------------------------------------

        if status:
            conditions.append(
                File.status == status.upper()
            )

        # -------------------------------------------------
        # TOTAL COUNT
        # -------------------------------------------------

        count_statement = (
            select(func.count(File.id))
            .where(*conditions)
        )

        total = self.db.scalar(count_statement) or 0

        # -------------------------------------------------
        # SORT
        # -------------------------------------------------

        if sort == "name":
            order_by = File.name.asc()

        elif sort == "size":
            order_by = File.size.desc()

        elif sort == "updated_at":
            order_by = File.updated_at.desc()

        else:
            # Default: newest first
            order_by = File.created_at.desc()

        # -------------------------------------------------
        # FILES
        # -------------------------------------------------

        statement = (
            select(File)
            .where(*conditions)
            .order_by(order_by)
            .offset(offset)
            .limit(page_size)
        )

        files = list(
            self.db.scalars(statement).all()
        )

        return files, total