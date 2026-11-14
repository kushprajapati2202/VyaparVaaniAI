from typing import Dict, Any, List, Optional
from app.core.config import settings

class BusinessRuleResult:
    def __init__(self, is_allowed: bool, requires_approval: bool = False, reason: Optional[str] = None, risk_level: str = "LOW"):
        self.is_allowed = is_allowed
        self.requires_approval = requires_approval
        self.reason = reason
        self.risk_level = risk_level

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_allowed": self.is_allowed,
            "requires_approval": self.requires_approval,
            "reason": self.reason,
            "risk_level": self.risk_level
        }

class BusinessRuleEngine:
    @staticmethod
    def validate_stock_availability(requested_items: List[Dict[str, Any]], inventory_map: Dict[str, float]) -> BusinessRuleResult:
        for item in requested_items:
            product_id = item["product_id"]
            product_name = item.get("product_name", product_id)
            qty = item["quantity"]
            available = inventory_map.get(product_id, 0.0)

            if qty <= 0:
                return BusinessRuleResult(is_allowed=False, reason=f"Invalid quantity {qty} for {product_name}.")
            
            if available < qty:
                return BusinessRuleResult(
                    is_allowed=False,
                    reason=f"Insufficient stock for {product_name}. Requested: {qty}, Available: {available}."
                )

        return BusinessRuleResult(is_allowed=True)

    @staticmethod
    def validate_order_policies(
        order_total: float,
        customer_credit_limit: float,
        customer_outstanding_balance: float,
        payment_method: str,
        discount_percent: float = 0.0
    ) -> BusinessRuleResult:
        # 1. High value order check
        if order_total > settings.MAX_UNAPPROVED_ORDER_AMOUNT:
            return BusinessRuleResult(
                is_allowed=True,
                requires_approval=True,
                risk_level="HIGH",
                reason=f"Order amount ₹{order_total:,.2f} exceeds threshold of ₹{settings.MAX_UNAPPROVED_ORDER_AMOUNT:,.2f}."
            )

        # 2. Credit check for credit purchases
        if payment_method.upper() == "CREDIT":
            projected_balance = customer_outstanding_balance + order_total
            if customer_credit_limit > 0:
                utilization = projected_balance / customer_credit_limit
                if projected_balance > customer_credit_limit:
                    return BusinessRuleResult(
                        is_allowed=True,
                        requires_approval=True,
                        risk_level="CRITICAL",
                        reason=f"Customer credit limit of ₹{customer_credit_limit:,.2f} exceeded. Projected balance: ₹{projected_balance:,.2f}."
                    )
                elif utilization > settings.MAX_CREDIT_UTILIZATION_PERCENT:
                    return BusinessRuleResult(
                        is_allowed=True,
                        requires_approval=True,
                        risk_level="MEDIUM",
                        reason=f"High credit utilization ({utilization*100:.1f}%). Limit: ₹{customer_credit_limit:,.2f}."
                    )

        # 3. Discount check
        if discount_percent > settings.MAX_UNAPPROVED_DISCOUNT_PERCENT:
            return BusinessRuleResult(
                is_allowed=True,
                requires_approval=True,
                risk_level="MEDIUM",
                reason=f"Discount of {discount_percent*100:.1f}% exceeds permitted {settings.MAX_UNAPPROVED_DISCOUNT_PERCENT*100:.1f}%."
            )

        return BusinessRuleResult(is_allowed=True, requires_approval=False)
