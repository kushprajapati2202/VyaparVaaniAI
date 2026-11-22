"""Tools for the VyaparVaani Owner Agent.

They call the VyaparVaani backend (Cloud Run) `/api/v1/enterprise/*` API, the same system of record
the counter voice agent (Gemini Live) writes to. Every tool returns a dict and never raises, so the
model always gets a structured result it can explain.
"""
import os
from typing import Any, Dict, Optional
from urllib.parse import quote

import httpx

_TIMEOUT = httpx.Timeout(15.0, connect=5.0)


def _base() -> str:
    return os.environ.get("VYAPARVAANI_API_URL", "http://localhost:8000").rstrip("/") + "/api/v1/enterprise"


def _headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {os.environ.get('VYAPARVAANI_AGENT_TOKEN', '')}"}


async def _call(method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.request(method, _base() + path, headers=_headers(), **kwargs)
    except httpx.HTTPError as e:
        return {"success": False, "error_code": "SHOP_SYSTEM_UNREACHABLE",
                "error": f"Could not reach the VyaparVaani shop system: {type(e).__name__}"}
    if r.status_code >= 400:
        detail = r.json().get("detail") if r.headers.get("content-type", "").startswith("application/json") else r.text
        if isinstance(detail, dict):
            return {"success": False, **detail}
        return {"success": False, "error_code": f"HTTP_{r.status_code}", "error": str(detail)[:300]}
    body = r.json()
    return body if isinstance(body, dict) else {"success": True, "data": body}


# ------------------------------------------------------------------ read-only
async def get_shop_briefing() -> Dict[str, Any]:
    """Today's snapshot of the shop: sales, orders, payments collected, total udhaar (credit) outstanding,
    orders waiting for the owner's approval, low-stock items with a reorder suggestion, and the top debtors.
    Use this first for any general question like "how is the shop doing" or "what needs my attention"."""
    return await _call("GET", "/briefing")


async def list_pending_approvals() -> Dict[str, Any]:
    """Orders the counter voice agent could not complete on its own because they break credit policy
    (credit limit / order size). Each has an order_number, customer, amount, items, reason and the
    customer's current outstanding vs credit limit. The owner must approve or reject each one."""
    return await _call("GET", "/approvals")


async def list_top_debtors(limit: int = 10) -> Dict[str, Any]:
    """Customers with the highest outstanding udhaar (khata credit), with credit-limit utilization and
    days since their last payment. Use for collection follow-ups.

    Args:
        limit: How many customers to return (1-50).
    """
    return await _call("GET", "/khata/debtors", params={"limit": max(1, min(int(limit), 50))})


async def get_customer_khata(customer_name: str) -> Dict[str, Any]:
    """A single customer's khata: credit limit, outstanding balance, recent ledger entries and orders.

    Args:
        customer_name: Customer name, partial name or phone number (Latin script; transliterate
            Gujarati/Hindi names, e.g. "રાહુલ" -> "Rahul").
    """
    return await _call("GET", f"/customers/{quote(customer_name.strip(), safe='')}")


async def get_low_stock_reorder_plan() -> Dict[str, Any]:
    """Products at or below their alert level, with a suggested reorder quantity and the estimated
    purchase cost at current purchase prices."""
    return await _call("GET", "/inventory/low-stock")


async def get_voice_agent_activity(limit: int = 10) -> Dict[str, Any]:
    """Audit trail of what the counter voice agent did: each workflow (voice order / khata payment) with
    every step - customer identified, stock checked, credit policy, shopkeeper confirmation, execution,
    undo. Use when the owner asks what happened at the counter or wants to verify an entry.

    Args:
        limit: Number of most recent workflows (1-50).
    """
    return await _call("GET", "/activity", params={"limit": max(1, min(int(limit), 50))})


async def get_automation_impact() -> Dict[str, Any]:
    """Measured ROI of the voice agent: transactions automated, average time per voice transaction vs
    manual entry, time and money saved, AI cost per transaction, languages used."""
    return await _call("GET", "/impact")


# ------------------------------------------------------------------ owner decisions (two-step)
async def decide_approval(order_number: str, approve: bool, note: Optional[str] = None,
                          owner_confirmed: bool = False) -> Dict[str, Any]:
    """Approve or reject an order waiting for owner approval. The decision is announced by voice at the
    shop counter immediately.

    TWO-STEP: first call with owner_confirmed=false - this changes nothing and returns a preview. Show the
    preview and ask the owner to confirm. Only after the owner explicitly says yes, call again with
    owner_confirmed=true.

    Args:
        order_number: Order number from list_pending_approvals, e.g. "ORD-20261122-0007".
        approve: True to approve, False to reject.
        note: Short reason, also spoken at the counter (e.g. "Pays every month end").
        owner_confirmed: True only after the owner confirmed this exact decision.
    """
    if not owner_confirmed:
        pending = await _call("GET", "/approvals")
        if pending.get("success") is False:
            return pending
        match = next((p for p in pending.get("pending_approvals", [])
                      if (p.get("order_number") or "").upper() == order_number.strip().upper()), None)
        if not match:
            return {"success": False, "error_code": "APPROVAL_NOT_FOUND",
                    "error": f"No pending approval for {order_number}.",
                    "pending_order_numbers": [p.get("order_number") for p in pending.get("pending_approvals", [])]}
        return {"success": True, "preview": True, "nothing_changed_yet": True,
                "decision": "APPROVE" if approve else "REJECT", "note": note, "approval": match,
                "instruction": "Summarize this decision and ask the owner to confirm. Then call again with owner_confirmed=true."}
    return await _call("POST", f"/approvals/{order_number.strip()}/resolve", json={"approved": bool(approve), "note": note})


async def record_restock(product_name: str, quantity: float, supplier_note: Optional[str] = None,
                         owner_confirmed: bool = False) -> Dict[str, Any]:
    """Record goods received from a supplier, increasing stock.

    TWO-STEP: call with owner_confirmed=false first to get a preview (nothing changes), confirm with the
    owner, then call with owner_confirmed=true.

    Args:
        product_name: Product, English or vernacular (e.g. "Rice", "chawal", "ચોખા").
        quantity: Quantity received, in the product's unit (kg / litre / packet). Must be > 0.
        supplier_note: Optional supplier / bill reference.
        owner_confirmed: True only after the owner confirmed this exact restock.
    """
    try:
        quantity = float(quantity)
    except (TypeError, ValueError):
        return {"success": False, "error_code": "INVALID_QUANTITY", "error": f"'{quantity}' is not a number."}
    if quantity <= 0:
        return {"success": False, "error_code": "INVALID_QUANTITY", "error": "Quantity must be greater than zero."}
    if not owner_confirmed:
        return {"success": True, "preview": True, "nothing_changed_yet": True, "product_name": product_name,
                "quantity": quantity, "supplier_note": supplier_note,
                "instruction": "Confirm product and quantity with the owner, then call again with owner_confirmed=true."}
    return await _call("POST", "/inventory/restock",
                       json={"product_name": product_name, "quantity": quantity, "supplier_note": supplier_note})
