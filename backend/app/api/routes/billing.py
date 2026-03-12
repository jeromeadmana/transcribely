from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.api.deps import get_current_user_organization
from app.services.usage import usage_service


router = APIRouter(prefix="/billing", tags=["billing"])


class UsageResponse(BaseModel):
    plan: str
    limit_minutes: Optional[int]
    used_minutes: float
    remaining_minutes: Optional[float]
    percentage_used: float
    is_unlimited: bool


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_organization),
):
    """Get current month's usage statistics."""
    user, organization, membership = auth

    stats = await usage_service.get_usage_stats_async(db, organization.id)
    return UsageResponse(**stats)


class PlanInfo(BaseModel):
    name: str
    limit_minutes: Optional[int]
    price: str
    features: list[str]


@router.get("/plans")
async def get_plans():
    """Get available subscription plans."""
    return [
        PlanInfo(
            name="free",
            limit_minutes=30,
            price="$0/month",
            features=[
                "30 minutes of transcription/month",
                "Basic export formats (TXT, JSON)",
                "1 team member",
            ],
        ),
        PlanInfo(
            name="starter",
            limit_minutes=300,
            price="$19/month",
            features=[
                "5 hours of transcription/month",
                "All export formats (TXT, JSON, SRT, VTT)",
                "5 team members",
                "Priority processing",
            ],
        ),
        PlanInfo(
            name="pro",
            limit_minutes=1200,
            price="$49/month",
            features=[
                "20 hours of transcription/month",
                "All export formats",
                "Unlimited team members",
                "Priority processing",
                "API access",
            ],
        ),
        PlanInfo(
            name="enterprise",
            limit_minutes=None,
            price="Contact us",
            features=[
                "Unlimited transcription",
                "All export formats",
                "Unlimited team members",
                "Dedicated support",
                "Custom integrations",
                "SLA guarantee",
            ],
        ),
    ]
