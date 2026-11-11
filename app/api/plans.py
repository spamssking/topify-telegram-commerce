from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.plan import PlanResponse
from app.services.plan_service import PlanService


router = APIRouter(
    prefix="/api/plans",
    tags=["Plans"],
)


@router.get(
    "",
    response_model=list[PlanResponse],
)
def get_plans(
    db: Session = Depends(get_db),
):
    service = PlanService(db)

    return service.list_active_plans()


@router.get(
    "/{plan_id}",
    response_model=PlanResponse,
)
def get_plan(
    plan_id: str,
    db: Session = Depends(get_db),
):
    service = PlanService(db)

    plan = service.get_plan(plan_id)

    if not plan:
        raise HTTPException(
            status_code=404,
            detail="Plan not found.",
        )

    return plan
