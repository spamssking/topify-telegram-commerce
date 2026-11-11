from pathlib import Path
import os
import uuid

from fastapi import UploadFile


class StagingStorage:

    def __init__(
        self,
        base_path: str = "./storage/staging",
    ):
        self.base_path = Path(
            base_path
        )

        self.base_path.mkdir(
            parents=True,
            exist_ok=True,
        )

    def create_path(
        self,
        filename: str,
    ) -> Path:

        safe_filename = (
            Path(filename).name
        )

        job_id = str(
            uuid.uuid4()
        )

        return (
            self.base_path
            / f"{job_id}_{safe_filename}"
        )

    async def save_upload(
        self,
        upload: UploadFile,
    ) -> tuple[str, int]:

        path = self.create_path(
            upload.filename or "file"
        )

        total_size = 0

        with open(
            path,
            "wb",
        ) as output:

            while True:

                chunk = await upload.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                output.write(chunk)

                total_size += len(chunk)

        return (
            str(path),
            total_size,
        )

    def delete(
        self,
        path: str,
    ) -> None:

        try:
            os.remove(path)

        except FileNotFoundError:
            pass
