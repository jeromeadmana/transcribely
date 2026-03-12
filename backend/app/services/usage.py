from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.video import UsageRecord
from app.models.user import Organization
from app.core.config import settings


class UsageService:
    @staticmethod
    def get_current_month_range() -> tuple[datetime, datetime]:
        """Get the start and end of the current month."""
        now = datetime.now(timezone.utc)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Get next month
        if now.month == 12:
            end_of_month = start_of_month.replace(year=now.year + 1, month=1)
        else:
            end_of_month = start_of_month.replace(month=now.month + 1)

        return start_of_month, end_of_month

    @staticmethod
    async def get_monthly_usage_async(
        db: AsyncSession,
        organization_id: UUID,
    ) -> float:
        """Get total minutes used this month (async)."""
        start_of_month, end_of_month = UsageService.get_current_month_range()

        result = await db.execute(
            select(func.coalesce(func.sum(UsageRecord.minutes_used), 0))
            .where(
                UsageRecord.organization_id == organization_id,
                UsageRecord.recorded_at >= start_of_month,
                UsageRecord.recorded_at < end_of_month,
            )
        )
        total = result.scalar()
        return float(total) if total else 0.0

    @staticmethod
    def get_monthly_usage_sync(
        db: Session,
        organization_id: UUID,
    ) -> float:
        """Get total minutes used this month (sync)."""
        start_of_month, end_of_month = UsageService.get_current_month_range()

        result = db.execute(
            select(func.coalesce(func.sum(UsageRecord.minutes_used), 0))
            .where(
                UsageRecord.organization_id == organization_id,
                UsageRecord.recorded_at >= start_of_month,
                UsageRecord.recorded_at < end_of_month,
            )
        )
        total = result.scalar()
        return float(total) if total else 0.0

    @staticmethod
    async def get_plan_limit_async(
        db: AsyncSession,
        organization_id: UUID,
    ) -> int:
        """Get the monthly limit for organization's plan (async)."""
        result = await db.execute(
            select(Organization.plan).where(Organization.id == organization_id)
        )
        plan = result.scalar() or "free"
        return settings.plan_limits.get(plan, settings.plan_limits["free"])

    @staticmethod
    def get_plan_limit_sync(
        db: Session,
        organization_id: UUID,
    ) -> int:
        """Get the monthly limit for organization's plan (sync)."""
        result = db.execute(
            select(Organization.plan).where(Organization.id == organization_id)
        )
        plan = result.scalar() or "free"
        return settings.plan_limits.get(plan, settings.plan_limits["free"])

    @staticmethod
    async def check_can_transcribe_async(
        db: AsyncSession,
        organization_id: UUID,
        estimated_minutes: float = 0,
    ) -> tuple[bool, str]:
        """Check if organization can transcribe more content (async)."""
        limit = await UsageService.get_plan_limit_async(db, organization_id)

        # Unlimited plan
        if limit == -1:
            return True, ""

        usage = await UsageService.get_monthly_usage_async(db, organization_id)
        remaining = limit - usage

        if remaining <= 0:
            return False, f"Monthly limit of {limit} minutes reached. Please upgrade your plan."

        if estimated_minutes > 0 and estimated_minutes > remaining:
            return False, f"Not enough remaining quota. You have {remaining:.1f} minutes left this month."

        return True, ""

    @staticmethod
    def check_can_transcribe_sync(
        db: Session,
        organization_id: UUID,
        estimated_minutes: float = 0,
    ) -> tuple[bool, str]:
        """Check if organization can transcribe more content (sync)."""
        limit = UsageService.get_plan_limit_sync(db, organization_id)

        # Unlimited plan
        if limit == -1:
            return True, ""

        usage = UsageService.get_monthly_usage_sync(db, organization_id)
        remaining = limit - usage

        if remaining <= 0:
            return False, f"Monthly limit of {limit} minutes reached. Please upgrade your plan."

        if estimated_minutes > 0 and estimated_minutes > remaining:
            return False, f"Not enough remaining quota. You have {remaining:.1f} minutes left this month."

        return True, ""

    @staticmethod
    def record_usage_sync(
        db: Session,
        organization_id: UUID,
        video_id: UUID,
        minutes_used: float,
    ) -> UsageRecord:
        """Record transcription usage (sync - for background tasks)."""
        record = UsageRecord(
            organization_id=organization_id,
            video_id=video_id,
            minutes_used=Decimal(str(minutes_used)),
        )
        db.add(record)
        db.commit()
        return record

    @staticmethod
    async def get_usage_stats_async(
        db: AsyncSession,
        organization_id: UUID,
    ) -> dict:
        """Get comprehensive usage stats for an organization."""
        usage = await UsageService.get_monthly_usage_async(db, organization_id)
        limit = await UsageService.get_plan_limit_async(db, organization_id)

        # Get organization plan
        result = await db.execute(
            select(Organization.plan).where(Organization.id == organization_id)
        )
        plan = result.scalar() or "free"

        # Calculate remaining and percentage
        if limit == -1:
            remaining = float("inf")
            percentage_used = 0
        else:
            remaining = max(0, limit - usage)
            percentage_used = (usage / limit * 100) if limit > 0 else 0

        return {
            "plan": plan,
            "limit_minutes": limit if limit != -1 else None,
            "used_minutes": round(usage, 2),
            "remaining_minutes": round(remaining, 2) if remaining != float("inf") else None,
            "percentage_used": round(percentage_used, 1),
            "is_unlimited": limit == -1,
        }


usage_service = UsageService()
