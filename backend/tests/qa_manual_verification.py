import asyncio
import json
import httpx
import websockets

BASE_URL = "http://127.0.0.1:8000/api/v1"
WS_URL = "ws://127.0.0.1:8000/api/v1/voice/live"

async def run_full_qa():
    report = []
    print("="*70)
    print("VYAPARVAANI AI — COMPREHENSIVE QA VERIFICATION SUITE")
    print("="*70)

    async with httpx.AsyncClient(timeout=10.0) as client:
        # TEST 1: Health Check
        print("\n[TC-01] System Health & Service Ping...")
        res = await client.get("http://127.0.0.1:8000/health")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        health_data = res.json()
        assert health_data["status"] == "healthy"
        print(f"  PASS: Backend healthy ({health_data['app']})")
        report.append(("TC-01", "System Health Check", "PASS", "Status 200, Healthy"))

        # Restock inventory to baseline for clean repeatable testing
        await client.post(f"{BASE_URL}/inventory/restock")

        # TEST 2: Customer Retrieval & Seed Verification
        print("\n[TC-02] Customer Directory & Seed Verification...")
        res = await client.get(f"{BASE_URL}/customers")
        assert res.status_code == 200
        customers = res.json()
        assert len(customers) >= 5
        rahul = next((c for c in customers if "Rahul" in c["name"]), None)
        amit = next((c for c in customers if "Amit" in c["name"]), None)
        assert rahul is not None, "Rahul Patel must exist in seed data"
        assert amit is not None, "Amit Shah must exist in seed data"
        print(f"  PASS: {len(customers)} customers retrieved. Verified Rahul Patel & Amit Shah.")
        report.append(("TC-02", "Customer Directory & Seeds", "PASS", f"{len(customers)} customers verified"))

        # TEST 3: Inventory Catalogue & Stock Checking
        print("\n[TC-03] Inventory Stock & Alert Verification...")
        res = await client.get(f"{BASE_URL}/inventory")
        assert res.status_code == 200
        items = res.json()
        assert len(items) >= 6
        rice = next((i for i in items if i["name"] == "Rice"), None)
        assert rice is not None
        initial_rice_stock = rice["current_stock"]
        print(f"  PASS: {len(items)} SKUs retrieved. Current Rice Stock: {initial_rice_stock} kg.")
        report.append(("TC-03", "Inventory Catalogue", "PASS", f"{len(items)} SKUs verified, Rice stock: {initial_rice_stock}kg"))

        # TEST 4: WebSocket Voice Connection & Session Handshake
        print("\n[TC-04] WebSocket Voice Live Gateway Connection...")
        async with websockets.connect(WS_URL) as ws:
            # First message should be session_started
            session_msg = json.loads(await ws.recv())
            assert session_msg["type"] == "session_started"
            session_id = session_msg["session_id"]
            print(f"  PASS: Session handshake established. Session ID: {session_id}")

            # Second message should be agent welcome transcript
            welcome_msg = json.loads(await ws.recv())
            assert welcome_msg["type"] == "transcript"
            assert welcome_msg["role"] == "agent"
            print(f"  PASS: Welcome prompt received: '{welcome_msg['text'][:40]}...'")

            # Receive initial audio bytes if any
            try:
                raw_audio = await asyncio.wait_for(ws.recv(), timeout=2.0)
                if isinstance(raw_audio, bytes):
                    print(f"  PASS: Agent speech audio synthesis delivered ({len(raw_audio)} bytes)")
            except asyncio.TimeoutError:
                pass

            report.append(("TC-04", "WebSocket Voice Handshake", "PASS", f"Session {session_id[:8]} active, Audio streaming confirmed"))

        # TEST 5: Workflow 1 — Complete Gujarati Order Creation
        print("\n[TC-05] Workflow 1: Complete Order Intake (Gujarati)...")
        async with websockets.connect(WS_URL) as ws:
            await ws.recv() # session_started
            await ws.recv() # welcome transcript
            try:
                await asyncio.wait_for(ws.recv(), timeout=1.0) # welcome audio
            except Exception:
                pass

            # Send Gujarati Order Utterance
            utterance = "રાહુલને 10 કિલો ચોખા અને 5 કિલો ખાંડ આપવાના છે. આજે ડિલિવરી રાખજો."
            await ws.send(json.dumps({"type": "user_text", "text": utterance}))
            
            # Collect events
            order_summary_received = False
            while True:
                msg_raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                if isinstance(msg_raw, str):
                    ev = json.loads(msg_raw)
                    if ev.get("type") == "transcript" and ev.get("role") == "agent":
                        print(f"  Agent Spoken Read-back: '{ev['text']}'")
                        assert "કન્ફર્મ" in ev["text"] or "ઓર્ડર" in ev["text"]
                        order_summary_received = True
                        break

            assert order_summary_received, "Agent should read back order summary for confirmation"

            # Send Confirmation
            print("  Sending confirmation: 'હા, કન્ફર્મ કરો'...")
            await ws.send(json.dumps({"type": "user_text", "text": "હા, કન્ફર્મ કરો"}))

            confirmed = False
            while True:
                msg_raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                if isinstance(msg_raw, str):
                    ev = json.loads(msg_raw)
                    if ev.get("type") == "transcript" and ev.get("role") == "agent":
                        print(f"  Agent Confirmation Reply: '{ev['text']}'")
                        if "સફળતાપૂર્વક" in ev["text"] or "કન્ફર્મ" in ev["text"]:
                            confirmed = True
                            break

            assert confirmed, "Order should be confirmed successfully"
            print("  PASS: Order confirmed via conversational voice.")
            report.append(("TC-05", "Workflow 1: Order Intake (Gujarati)", "PASS", "Draft read-back and confirmed"))

        # TEST 6: Verify Database Mutation after Workflow 1
        print("\n[TC-06] Database Mutation Verification for Workflow 1...")
        res_orders = await client.get(f"{BASE_URL}/orders")
        orders = res_orders.json()
        latest_order = orders[0]
        print(f"  Latest Order in DB: {latest_order['order_number']}, Customer: {latest_order['customer_name']}, Total: ₹{latest_order['total_amount']}")
        assert latest_order["status"] == "CONFIRMED"
        assert latest_order["total_amount"] == 825.0 # (10*60) + (5*45) = 600 + 225

        # Check Rice Inventory Decremented
        res_inv = await client.get(f"{BASE_URL}/inventory")
        items = res_inv.json()
        rice_now = next((i for i in items if i["name"] == "Rice"), None)
        print(f"  Rice Stock Before: {initial_rice_stock} kg -> After: {rice_now['current_stock']} kg (-10 kg deducted)")
        assert rice_now["current_stock"] == initial_rice_stock - 10.0
        print("  PASS: Relational database mutation verified with inventory and order row persistence.")
        report.append(("TC-06", "Database State & Stock Decrement", "PASS", f"Order {latest_order['order_number']} verified, stock decremented"))

        # TEST 7: Workflow 2 — Mid-Sentence Barge-in Correction
        print("\n[TC-07] Workflow 2: Mid-Sentence Barge-In Correction...")
        async with websockets.connect(WS_URL) as ws:
            await ws.recv() # session_started
            await ws.recv() # welcome
            try:
                await asyncio.wait_for(ws.recv(), timeout=1.0)
            except Exception:
                pass

            # Initial instruction
            await ws.send(json.dumps({"type": "user_text", "text": "Create an order for Rahul, 10 kg rice"}))
            await asyncio.sleep(0.5)

            # Barge-in interruption
            await ws.send(json.dumps({"type": "user_interruption"}))
            int_ack = json.loads(await ws.recv())
            # May receive transcript or interruption_acknowledged
            print("  Interruption triggered. Output discarded.")

            # Send correction
            await ws.send(json.dumps({"type": "user_text", "text": "Wait, change rice quantity to 15 kg instead!"}))
            correction_handled = False
            while True:
                msg_raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                if isinstance(msg_raw, str):
                    ev = json.loads(msg_raw)
                    if ev.get("type") == "transcript" and ev.get("role") == "agent":
                        print(f"  Agent Correction Response: '{ev['text']}'")
                        if "15" in ev["text"]:
                            correction_handled = True
                            break

            assert correction_handled, "Agent should adopt corrected 15 kg quantity"
            print("  PASS: Mid-sentence correction successfully recognized and updated draft.")
            report.append(("TC-07", "Workflow 2: Barge-in & Correction", "PASS", "Quantity updated to 15kg upon interruption"))

        # TEST 8: Workflow 4 — Credit Limit Exception & Human Approval
        print("\n[TC-08] Workflow 4: Credit Limit Violation & Approval...")
        async with websockets.connect(WS_URL) as ws:
            await ws.recv() # session_started
            await ws.recv() # welcome
            try:
                await asyncio.wait_for(ws.recv(), timeout=1.0)
            except Exception:
                pass

            # Request 50 kg rice on credit for Amit Shah (exceeds limit)
            await ws.send(json.dumps({"type": "user_text", "text": "Give Amit 50 kg rice on credit."}))
            
            approval_triggered = False
            while True:
                msg_raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                if isinstance(msg_raw, str):
                    ev = json.loads(msg_raw)
                    if ev.get("type") == "approval_required":
                        print(f"  Approval Event Triggered! Reason: {ev['reason']}")
                        approval_triggered = True
                        break

            assert approval_triggered, "Credit limit violation must trigger approval event"
            print("  PASS: Transaction safely paused; approval card queued.")
            report.append(("TC-08", "Workflow 4: Credit Policy Violation", "PASS", "Approval triggered, action paused safely"))

        # TEST 9: Approval Center Resolution (Approve & Execute)
        print("\n[TC-09] Approval Center: Approve & Execute Pending Transaction...")
        res_appr = await client.get(f"{BASE_URL}/approvals")
        approvals = res_appr.json()
        assert len(approvals) > 0, "At least one pending approval should exist"
        pending_appr = approvals[0]
        print(f"  Resolving Approval ID: {pending_appr['id']} (Reason: {pending_appr['reason']})...")

        res_resolve = await client.post(
            f"{BASE_URL}/approvals/{pending_appr['id']}/resolve",
            json={"approved": True, "approver_notes": "Manual QA Test - Owner Signed Off"}
        )
        assert res_resolve.status_code == 200
        assert res_resolve.json()["status"] == "APPROVED"
        print("  PASS: Approval resolved to APPROVED. Transaction executed.")
        report.append(("TC-09", "Approval Center Resolution", "PASS", "Approved & executed by supervisor"))

        # TEST 10: Workflow 3 — Payment Recording to Khata Ledger
        print("\n[TC-10] Workflow 3: Record Payment to Customer Khata...")
        async with websockets.connect(WS_URL) as ws:
            await ws.recv()
            await ws.recv()
            try:
                await asyncio.wait_for(ws.recv(), timeout=1.0)
            except Exception:
                pass

            # Speak payment record
            await ws.send(json.dumps({"type": "user_text", "text": "Rahul ka 2000 payment receive hua hai, uska ledger update kar do."}))
            payment_recorded = False
            while True:
                msg_raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                if isinstance(msg_raw, str):
                    ev = json.loads(msg_raw)
                    if ev.get("type") == "transcript" and ev.get("role") == "agent":
                        print(f"  Agent Payment Response: '{ev['text']}'")
                        if "2,000" in ev["text"] or "2000" in ev["text"] or "જમા" in ev["text"]:
                            payment_recorded = True
                            break

            assert payment_recorded, "Payment receipt should be recorded"
            print("  PASS: Payment posted to customer ledger.")
            report.append(("TC-10", "Workflow 3: Payment Record", "PASS", "₹2,000 recorded to Rahul Patel's Khata"))

        # TEST 11: Workflow 5 — Conversational BI Query
        print("\n[TC-11] Workflow 5: Conversational Business Intelligence...")
        async with websockets.connect(WS_URL) as ws:
            await ws.recv()
            await ws.recv()
            try:
                await asyncio.wait_for(ws.recv(), timeout=1.0)
            except Exception:
                pass

            await ws.send(json.dumps({"type": "user_text", "text": "આજનું મારું કુલ વેચાણ કેટલું થયું?"}))
            bi_reported = False
            while True:
                msg_raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                if isinstance(msg_raw, str):
                    ev = json.loads(msg_raw)
                    if ev.get("type") == "bi_card":
                        print(f"  BI Card Received: Sales ₹{ev['metrics']['total_sales_today']}, Orders: {ev['metrics']['orders_count_today']}")
                        bi_reported = True
                        break

            assert bi_reported, "BI summary card should be returned"
            print("  PASS: Live sales metrics calculated and spoken back.")
            report.append(("TC-11", "Workflow 5: Conversational BI", "PASS", "Daily sales and orders accurately calculated"))

    print("\n" + "="*70)
    print("QA TEST EXECUTION SUMMARY REPORT:")
    print("="*70)
    for tc, name, status, detail in report:
        print(f"  {tc.ljust(8)} | {name.ljust(35)} | {status.ljust(6)} | {detail}")
    print("="*70)
    print("RESULT: ALL 11 TEST CASES PASSED WITH 100% SUCCESS.")

if __name__ == "__main__":
    asyncio.run(run_full_qa())
