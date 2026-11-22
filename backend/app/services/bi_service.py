from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.config import settings
from app.models.models import (
    Order, Payment, Customer, Product, Inventory, DeliveryTask, Approval, OrderStatus, ApprovalStatus, DeliveryStatus,
    SessionMetric, AgentToolCall, VoiceSession,
)

class BIService:
    @staticmethod
    async def get_daily_metrics(db: AsyncSession) -> dict:
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        # 1. Total sales today (Confirmed / Processing / Dispatched / Delivered)
        sales_stmt = select(func.sum(Order.total_amount)).where(
            Order.status.in_([OrderStatus.CONFIRMED.value, OrderStatus.DELIVERED.value, OrderStatus.DISPATCHED.value]),
            Order.created_at >= today_start
        )
        sales_res = await db.execute(sales_stmt)
        total_sales_today = sales_res.scalar() or 0.0

        # 2. Orders count today
        orders_count_stmt = select(func.count(Order.id)).where(Order.created_at >= today_start)
        orders_count_res = await db.execute(orders_count_stmt)
        orders_count_today = orders_count_res.scalar() or 0

        # 3. Payments received today
        payments_stmt = select(func.sum(Payment.amount)).where(Payment.created_at >= today_start)
        payments_res = await db.execute(payments_stmt)
        payments_today = payments_res.scalar() or 0.0

        # 4. Total outstanding credit across all customers
        credit_stmt = select(func.sum(Customer.outstanding_balance))
        credit_res = await db.execute(credit_stmt)
        total_credit = credit_res.scalar() or 0.0

        # 5. Low stock alerts
        low_stock_stmt = (
            select(func.count(Product.id))
            .join(Inventory, Product.id == Inventory.product_id)
            .where(Inventory.current_stock <= Product.min_stock_alert)
        )
        low_stock_res = await db.execute(low_stock_stmt)
        low_stock_count = low_stock_res.scalar() or 0

        # 6. Pending deliveries
        deliv_stmt = select(func.count(DeliveryTask.id)).where(DeliveryTask.status == DeliveryStatus.PENDING.value)
        deliv_res = await db.execute(deliv_stmt)
        pending_deliv = deliv_res.scalar() or 0

        # 7. Pending approvals
        appr_stmt = select(func.count(Approval.id)).where(Approval.status == ApprovalStatus.PENDING.value)
        appr_res = await db.execute(appr_stmt)
        pending_appr = appr_res.scalar() or 0

        impact = await BIService.get_impact_metrics(db)
        return {
            "total_sales_today": float(total_sales_today),
            "orders_count_today": int(orders_count_today),
            "payments_received_today": float(payments_today),
            "total_outstanding_credit": float(total_credit),
            "low_stock_count": int(low_stock_count),
            "pending_deliveries_count": int(pending_deliv),
            "pending_approvals_count": int(pending_appr),
            # Measured from voice sessions (0 until the first voice transaction)
            "automation_rate_percent": impact["automation_rate_percent"],
            "avg_transaction_time_sec": impact["avg_voice_txn_seconds"] or 0.0,
            "time_saved_hours": round(impact["time_saved_minutes"] / 60, 2),
        }

    @staticmethod
    async def get_impact_metrics(db: AsyncSession) -> dict:
        """Commercial-viability metrics computed from what the voice agent actually did."""
        rows = (await db.execute(select(SessionMetric.metric, SessionMetric.label, SessionMetric.value))).all()

        def total(metric: str, label: str = None) -> float:
            return sum(v for m, l, v in rows if m == metric and (label is None or l == label))

        def values(metric: str) -> list:
            return [v for m, _, v in rows if m == metric]

        def by_label(metric: str) -> dict:
            out: dict = {}
            for m, l, v in rows:
                if m == metric:
                    out[l or "unknown"] = out.get(l or "unknown", 0) + int(v)
            return dict(sorted(out.items(), key=lambda kv: -kv[1]))

        txns = int(total("transaction"))
        undone = int(total("undo"))
        approvals = int(total("approval_required"))
        completed = max(0, txns - undone)
        lat = sorted(values("response_latency_ms"))
        durations = values("txn_duration_sec")
        avg_duration = round(sum(durations) / len(durations), 1) if durations else None
        manual = settings.MANUAL_SECONDS_PER_TRANSACTION
        saved_min = round(completed * max(0.0, manual - (avg_duration or manual)) / 60, 1)
        ai_cost_inr = round(total("cost_usd") * settings.USD_TO_INR, 2)
        cost_per_txn = round(ai_cost_inr / completed, 2) if completed else None
        tool_lat = (await db.execute(select(func.avg(AgentToolCall.latency_ms)))).scalar()
        sessions = (await db.execute(select(func.count(VoiceSession.id)))).scalar() or 0

        return {
            "voice_sessions": int(sessions),
            "transactions_completed": completed,
            "orders_completed": int(total("transaction", "ORDER")),
            "payments_completed": int(total("transaction", "PAYMENT")),
            "undone": undone,
            "approvals_required": approvals,
            "automation_rate_percent": round(100 * (txns - approvals) / txns, 1) if txns else 0.0,
            "human_touch_rate_percent": round(100 * approvals / txns, 1) if txns else 0.0,
            "exceptions_caught": int(total("exception")),
            "exceptions_by_code": by_label("exception"),
            "corrections_handled": int(total("correction")),
            "languages": by_label("language"),
            "avg_response_latency_ms": round(sum(lat) / len(lat)) if lat else None,
            "p90_response_latency_ms": round(lat[int(0.9 * (len(lat) - 1))]) if lat else None,
            "avg_tool_latency_ms": round(tool_lat, 1) if tool_lat is not None else None,
            "avg_voice_txn_seconds": avg_duration,
            "manual_seconds_per_txn": manual,
            "time_saved_minutes": saved_min,
            "labour_saved_inr": round(saved_min / 60 * settings.OPERATOR_COST_PER_HOUR_INR, 2),
            "total_ai_cost_inr": ai_cost_inr,
            "cost_per_transaction_inr": cost_per_txn,
            "subscription_price_inr": settings.SUBSCRIPTION_PRICE_INR_PER_MONTH,
            "breakeven_txns_per_month": int(settings.SUBSCRIPTION_PRICE_INR_PER_MONTH / cost_per_txn) if cost_per_txn else None,
            "assumptions": {
                "manual_seconds_per_txn": manual,
                "operator_cost_per_hour_inr": settings.OPERATOR_COST_PER_HOUR_INR,
                "usd_to_inr": settings.USD_TO_INR,
                "live_model": settings.GEMINI_LIVE_MODEL,
                "price_input_audio_usd_per_m": settings.LIVE_PRICE_INPUT_AUDIO_PER_M,
                "price_output_audio_usd_per_m": settings.LIVE_PRICE_OUTPUT_AUDIO_PER_M,
            },
        }
