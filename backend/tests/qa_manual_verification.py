"""Live end-to-end QA against a RUNNING backend with a real Gemini Live session.

    python tests/qa_manual_verification.py            # backend on http://127.0.0.1:8000

Typed utterances are sent over the same WebSocket the microphone uses; Gemini decides which
tools to call. Assertions check tool calls, agent events and database state (not exact wording,
which a generative model varies).
"""
import asyncio
import json
import sys
import time

import httpx
import websockets

BASE = "http://127.0.0.1:8000"
API = f"{BASE}/api/v1"
WS_URL = "ws://127.0.0.1:8000/api/v1/voice/live"


class Counter:
    """One voice-counter WebSocket session."""

    def __init__(self, ws):
        self.ws = ws
        self.events = []
        self.audio_bytes = 0

    async def wait_turn(self, timeout=45.0):
        """Collect events until an agent turn that produced speech completes."""
        spoke, start, collected = False, time.time(), []
        while time.time() - start < timeout:
            try:
                raw = await asyncio.wait_for(self.ws.recv(), timeout=timeout)
            except asyncio.TimeoutError:
                break
            if isinstance(raw, bytes):
                self.audio_bytes += len(raw)
                spoke = True
                continue
            ev = json.loads(raw)
            self.events.append(ev)
            collected.append(ev)
            if ev["type"] == "audio_mp3":
                spoke = True
            if ev["type"] == "turn_complete" and spoke:
                break
        return collected

    async def say(self, text, timeout=45.0):
        await self.ws.send(json.dumps({"type": "user_text", "text": text}))
        evs = await self.wait_turn(timeout)
        agent = " ".join(e["text"] for e in evs if e["type"] == "transcript" and e["role"] == "agent")
        tools = [(e["tool"], e.get("error_code")) for e in evs if e["type"] == "tool_call"]
        print(f"    USER : {text}\n    AGENT: {agent}\n    TOOLS: {tools}")
        return evs

    @staticmethod
    def tools(evs, name):
        return [e for e in evs if e["type"] == "tool_call" and e["tool"] == name]


async def open_counter():
    ws = await websockets.connect(WS_URL, max_size=None)
    c = Counter(ws)
    first = json.loads(await ws.recv())
    assert first["type"] == "session_started", first
    await c.wait_turn()  # greeting
    return c, first


async def run():
    results = []

    def record(tc, name, ok, detail):
        results.append((tc, name, "PASS" if ok else "FAIL", detail))
        print(f"  {'PASS' if ok else 'FAIL'}: {detail}")

    async with httpx.AsyncClient(timeout=15) as http:
        print("\n[TC-01] Health + voice status")
        h = (await http.get(f"{BASE}/health")).json()
        vs = (await http.get(f"{API}/voice/status")).json()
        record("TC-01", "Health & Gemini config", h["status"] == "healthy" and vs["gemini_configured"], f"model={vs['live_model']}")
        await http.post(f"{API}/inventory/restock")
        rice0 = next(p for p in (await http.get(f"{API}/inventory")).json() if p["name"] == "Rice")["current_stock"]

        print("\n[TC-02] Live session handshake + spoken greeting")
        c, started = await open_counter()
        record("TC-02", "Gemini Live session", started["mode"] == "live" and c.audio_bytes > 0,
               f"mode={started['mode']} greeting_audio={c.audio_bytes}B")

        print("\n[TC-03] Gujarati order -> read-back (nothing saved yet)")
        evs = await c.say("રાહુલભાઈને 10 કિલો ચોખા અને 5 કિલો ખાંડ આપવાના છે, ખાતામાં લખજો.")
        prop = Counter.tools(evs, "propose_order")
        orders_before = len((await http.get(f"{API}/orders")).json())
        record("TC-03", "Order proposal + read-back", bool(prop) and prop[-1]["success"] and prop[-1]["result"]["total_amount"] == 825.0,
               "propose_order total ₹825, awaiting confirmation")

        print("\n[TC-04] Hinglish spoken correction")
        evs = await c.say("Nahi nahi, chawal 15 kilo kar do.")
        upd = Counter.tools(evs, "update_pending_order") or Counter.tools(evs, "propose_order")
        record("TC-04", "Correction applied", bool(upd) and upd[-1]["result"].get("total_amount") == 15 * 60 + 5 * 45,
               "items updated to 15 kg rice (₹1125)")

        print("\n[TC-05] Confirm -> DB mutation")
        evs = await c.say("હા, બરાબર છે, કન્ફર્મ કરો.")
        conf = Counter.tools(evs, "confirm_action")
        rice1 = next(p for p in (await http.get(f"{API}/inventory")).json() if p["name"] == "Rice")["current_stock"]
        orders_after = len((await http.get(f"{API}/orders")).json())
        record("TC-05", "Confirmed + stock decremented", bool(conf) and rice1 == rice0 - 15 and orders_after == orders_before + 1,
               f"rice {rice0}->{rice1}")

        print("\n[TC-06] Ambiguous name -> clarification")
        evs = await c.say("કિરણભાઈને 2 લીટર તેલ આપવાનું છે")
        amb = [e for e in evs if e["type"] == "exception" and e["code"] == "MULTIPLE_MATCHES"]
        record("TC-06", "Ambiguity detected", bool(amb), "agent asked Kiran Patel vs Kiran Desai")
        await c.say("Rehne do, cancel karo.")

        print("\n[TC-07] Credit breach -> owner approval -> spoken outcome")
        evs = await c.say("Amit bhai ko 50 kilo chawal udhaar pe de do.")
        evs += await c.say("haan, confirm")
        appr_evt = [e for e in c.events if e["type"] == "approval_required"]
        ok = bool(appr_evt)
        if ok:
            r = await http.post(f"{API}/approvals/{appr_evt[-1]['approval_id']}/resolve", json={"approved": True, "approver_notes": "Regular customer"})
            ok = r.status_code == 200
            evs = await c.wait_turn(45)
            announced = any(e["type"] == "approval_resolved" for e in c.events)
            spoken = " ".join(e["text"] for e in evs if e["type"] == "transcript" and e["role"] == "agent")
            print(f"    AGENT: {spoken}")
            ok = ok and announced and bool(spoken)
        record("TC-07", "Human-in-the-loop approval", ok, "approval raised, resolved by owner, announced by voice")

        print("\n[TC-08] Payment + undo (transaction safety)")
        cust = {x["name"]: x for x in (await http.get(f"{API}/customers")).json()}
        bal0 = cust["Mahesh Provision Store"]["outstanding_balance"]
        await c.say("महेश प्रोविजन स्टोर के 2000 रुपये UPI से जमा करो।")
        await c.say("हाँ, कन्फर्म")
        bal1 = {x["name"]: x for x in (await http.get(f"{API}/customers")).json()}["Mahesh Provision Store"]["outstanding_balance"]
        evs = await c.say("Galti ho gayi, woh payment undo karo.")
        if not Counter.tools(evs, "undo_last_action"):
            evs = await c.say("haan, undo karo")
        bal2 = {x["name"]: x for x in (await http.get(f"{API}/customers")).json()}["Mahesh Provision Store"]["outstanding_balance"]
        record("TC-08", "Payment then undo", bal1 == bal0 - 2000 and bal2 == bal0, f"balance {bal0} -> {bal1} -> {bal2}")

        print("\n[TC-09] Latency + activity visibility")
        lat = [e["ms"] for e in c.events if e["type"] == "latency"]
        steps = [e for e in c.events if e["type"] == "workflow_step"]
        human = [e for e in steps if e["human"]]
        record("TC-09", "Latency & workflow events", bool(lat) and bool(steps) and bool(human),
               f"avg latency {sum(lat) // max(1, len(lat))} ms over {len(lat)} turns, {len(steps)} steps, {len(human)} human checkpoints")
        await c.ws.close()
        await asyncio.sleep(1.5)

        print("\n[TC-10] Impact metrics")
        m = (await http.get(f"{API}/bi/impact")).json()
        record("TC-10", "ROI metrics populated", m["transactions_completed"] >= 2 and m["total_ai_cost_inr"] > 0,
               f"txns={m['transactions_completed']} automation={m['automation_rate_percent']}% cost/txn=₹{m['cost_per_transaction_inr']}")

    print("\n" + "=" * 70)
    for r in results:
        print(f"{r[0]:6} {r[2]:4}  {r[1]:32} {r[3]}")
    failed = [r for r in results if r[2] == "FAIL"]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
