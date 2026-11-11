from pydantic import BaseModel, ConfigDict


class PlanResponse(BaseModel):
    id: str
    code: str
    name: str
    description: str | None

    storage_quota_bytes: int
    max_file_size_bytes: int
    max_files: int | None

    thumbnail_enabled: bool

    price: int
    currency: str
    billing_interval: str | None

    sort_order: int
    is_active: bool
    is_default: bool

    model_config = ConfigDict(
        from_attributes=True,
    )
