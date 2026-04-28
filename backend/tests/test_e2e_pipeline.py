"""
Test 6a/6b: Full end-to-end pipeline test against a running backend.
Usage:
  Terminal 1:  uvicorn backend.main:app --reload --port 8000
  Terminal 2:  python backend/tests/test_e2e_pipeline.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import httpx

BASE_URL = "http://localhost:8000"
TEST_EMAIL = "test_e2e@taxsathi.pk"
TEST_PASSWORD = "TestPass123!"
TEST_NAME = "Test User E2E"


async def test_full_pipeline():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=120.0) as client:

        # 1. Auth
        print("=== STEP 1: AUTH ===")
        signup_resp = await client.post("/api/v1/auth/signup", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "full_name": TEST_NAME,
        })
        if signup_resp.status_code == 400:
            print("User exists — logging in...")
            login_resp = await client.post("/api/v1/auth/login", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
            })
            assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
            token = login_resp.json()["token"]
        else:
            assert signup_resp.status_code == 200, f"Signup failed: {signup_resp.text}"
            token = signup_resp.json()["token"]

        headers = {"Authorization": f"Bearer {token}"}
        print(f"Auth token obtained: {token[:20]}...")

        # 2. Create session
        print("\n=== STEP 2: CREATE SESSION ===")
        session_resp = await client.post("/api/v1/sessions/", headers=headers, json={"title": "E2E Test"})
        assert session_resp.status_code == 200, f"Create session failed: {session_resp.text}"
        session_id = session_resp.json()["id"]
        print(f"Session created: {session_id}")

        # 3. Send message
        print("\n=== STEP 3: SEND MESSAGE ===")
        message = (
            "I am a software engineer earning 250,000 per month from my company. "
            "My employer deducts 20,000 per month as withholding tax. "
            "I also have 80,000 annual profit from my bank savings account, "
            "with 12,000 withholding deducted by the bank. "
            "I donated 100,000 to Edhi Foundation last year. "
            "I am a filer. Tax year 2025-2026."
        )

        chat_resp = await client.post("/api/v1/pipeline/chat", headers=headers, json={
            "session_id": session_id,
            "message": message,
            "conversation_history": [],
        })
        assert chat_resp.status_code == 200, f"Pipeline failed: {chat_resp.text}"
        response = chat_resp.json()
        print(f"Response keys: {list(response.keys())}")
        print(f"Stage: {response.get('stage')}")

        # Handle clarification
        if response.get("stage") == "clarification_needed":
            print("Pipeline returned clarification — sending follow-up...")
            followup = "My tax year is 2025-2026. I am a resident Pakistani. No other income."
            chat_resp2 = await client.post("/api/v1/pipeline/chat", headers=headers, json={
                "session_id": session_id,
                "message": followup,
                "conversation_history": [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": response.get("assistant_message", "")},
                ],
            })
            assert chat_resp2.status_code == 200, f"Follow-up failed: {chat_resp2.text}"
            response = chat_resp2.json()

        # 4. Verify canvas data
        print("\n=== STEP 4: VERIFY CANVAS DATA ===")
        canvas = response.get("canvas")
        assert canvas is not None, "Canvas data must be present"
        print(f"Canvas keys: {list(canvas.keys())}")

        steps = canvas.get("steps", [])
        print(f"Processing steps: {len(steps)}")
        for step in steps:
            status_sym = "✅" if step.get("status") == "completed" else ("❌" if step.get("status") == "failed" else "⏳")
            print(f"  {status_sym} Step {step.get('step_number')}: {step.get('step_name')} — {step.get('status')}")

        extraction = canvas.get("extraction")
        print(f"Extraction trace: {'✅ present' if extraction else '❌ MISSING'}")

        retrieval = canvas.get("retrieval")
        print(f"Retrieval trace: {'✅ present' if retrieval else '❌ MISSING'}")
        if retrieval:
            print(f"  Sections: {len(retrieval.get('selected_sections', []))}")

        interpretation = canvas.get("interpretation")
        print(f"Interpretation trace: {'✅ present' if interpretation else '❌ MISSING'}")

        calculation = canvas.get("calculation")
        print(f"Calculation trace: {'✅ present' if calculation else '❌ MISSING'}")
        if calculation and calculation.get("status") == "complete":
            print(f"  Gross income:   Rs. {calculation.get('total_gross_income', 0):,}")
            print(f"  Total liability: Rs. {calculation.get('total_tax_liability', 0):,.0f}")
            print(f"  Net payable:    Rs. {calculation.get('net_tax_payable', 0):,.0f}")
            print(f"  Refund due:     Rs. {calculation.get('refund_due', 0):,.0f}")

        # 5. Verify reply text
        print("\n=== STEP 5: VERIFY REPLY ===")
        reply = response.get("assistant_message", "NO REPLY FOUND")
        print(f"Reply: {str(reply)[:400]}")
        assert reply, "Assistant message must not be empty"

        # 6. Verify message persistence
        print("\n=== STEP 6: VERIFY MESSAGE PERSISTENCE ===")
        session_detail_resp = await client.get(f"/api/v1/sessions/{session_id}", headers=headers)
        assert session_detail_resp.status_code == 200, f"Get session failed: {session_detail_resp.text}"
        session_detail = session_detail_resp.json()
        msgs = session_detail.get("messages", [])
        print(f"Messages in session: {len(msgs)}")
        for msg in msgs:
            has_canvas = msg.get("canvas_data") is not None
            print(f"  [{msg.get('role')}]: {str(msg.get('content', ''))[:60]}... | canvas: {'yes' if has_canvas else 'no'}")

        # 7. Verify sessions list
        print("\n=== STEP 7: VERIFY SESSIONS LIST ===")
        sessions_resp = await client.get("/api/v1/sessions/", headers=headers)
        assert sessions_resp.status_code == 200
        sessions = sessions_resp.json()
        print(f"Total sessions: {len(sessions)}")
        our_session = next((s for s in sessions if s["id"] == session_id), None)
        if our_session:
            print(f"Our session title: {our_session.get('title', 'N/A')}")

        # 8. Verify profile
        print("\n=== STEP 8: VERIFY PROFILE ===")
        profile_resp = await client.get("/api/v1/profile/", headers=headers)
        assert profile_resp.status_code == 200
        profile = profile_resp.json()
        print(f"Profile: {profile.get('full_name', 'N/A')} ({profile.get('email', 'N/A')})")

        # 9. Cleanup
        print("\n=== STEP 9: CLEANUP ===")
        del_resp = await client.delete(f"/api/v1/sessions/{session_id}", headers=headers)
        print(f"Session deleted: {'✅' if del_resp.status_code == 200 else '❌'}")

        print("\n" + "=" * 60)
        print("E2E TEST COMPLETE")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
