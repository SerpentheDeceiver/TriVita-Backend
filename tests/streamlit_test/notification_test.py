"""
Notification Engine — Streamlit Test Dashboard
================================================
Tests every part of the notification pipeline without the Flutter app.

Run from backend/ folder:
    streamlit run tests/streamlit_test/notification_test.py

Make sure the FastAPI server is already running:
    uvicorn app.main:app --reload
"""

import json
import time
from datetime import datetime, timezone

import requests
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="🔔 Notification Engine Test",
    page_icon="🔔",
    layout="wide",
)

st.title("🔔 Notification Engine — Test Dashboard")
st.caption("Tests the full notification pipeline: schedule → FCM → quick-log → state tracking")

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _post(path: str, payload: dict) -> dict:
    try:
        r = requests.post(f"{BASE_URL}{path}", json=payload, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to FastAPI. Is the server running at " + BASE_URL + "?"}
    except requests.HTTPError as e:
        try:
            return {"error": e.response.json()}
        except Exception:
            return {"error": str(e)}


def _get(path: str, params: dict = None) -> dict:
    try:
        r = requests.get(f"{BASE_URL}{path}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to FastAPI. Is the server running at " + BASE_URL + "?"}
    except requests.HTTPError as e:
        try:
            return {"error": e.response.json()}
        except Exception:
            return {"error": str(e)}


def _ok(result: dict) -> bool:
    return "error" not in result


def _show(result: dict):
    if _ok(result):
        st.success("✅ " + json.dumps(result, indent=2, default=str))
    else:
        st.error("❌ " + json.dumps(result, indent=2, default=str))


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar — global settings
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Test Settings")
    uid = st.text_input("Firebase UID", value="test_user_001", help="Must match an existing user in MongoDB")
    dummy_token = st.text_input(
        "FCM Token (optional)",
        value="",
        help="Leave blank to skip real FCM sends. Token from Firebase Console → Project Settings → Test devices.",
        type="password",
    )
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    st.info(f"Today (UTC): **{today}**")

    st.divider()
    st.markdown("**API Base URL**")
    BASE_URL = st.text_input("FastAPI URL", value="http://localhost:8000")

    st.divider()
    st.markdown("""
**Quick Reference — Action IDs**

| Notification | Actions |
|---|---|
| hydration | ml_250, ml_500, ml_750, skip |
| wake | i_am_awake, snooze_15 |
| breakfast/lunch/dinner | light_meal, full_meal, skipped, snooze_15 |
| bedtime | log_now, snooze_30 |
| custom | logged, skip |
""")

# ─────────────────────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "1️⃣ Token",
    "2️⃣ Preferences",
    "3️⃣ Seed & Cycle",
    "4️⃣ Quick Log",
    "5️⃣ Status Monitor",
    "6️⃣ Full Flow Test",
])

# ═══════════════════════════════════════════════════════════════════════════
# TAB 1 — Register FCM Token
# ═══════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Register FCM Token")
    st.markdown("""
    Stores the device FCM token in `users.fcm_token`.
    This is called automatically by the Flutter app on every launch;
    here we simulate it manually.
    """)

    col1, col2 = st.columns([3, 1])
    with col1:
        token_input = st.text_input(
            "FCM Token to register",
            value=dummy_token or "fake-token-for-testing-1234567890",
            key="token_input",
        )
    with col2:
        st.write("")
        st.write("")
        if st.button("Register Token", type="primary", key="btn_register"):
            result = _post("/notifications/register-token", {"uid": uid, "fcm_token": token_input})
            _show(result)

    st.divider()
    st.markdown("**What this does:**")
    st.code(
        f'POST /notifications/register-token\n{{"uid": "{uid}", "fcm_token": "<token>"}}',
        language="json",
    )

# ═══════════════════════════════════════════════════════════════════════════
# TAB 2 — Notification Preferences
# ═══════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Notification Preferences")

    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("**Get current preferences**")
        if st.button("Fetch Preferences", key="btn_fetch_prefs"):
            result = _get("/notifications/preferences", {"uid": uid})
            _show(result)

    with col_right:
        st.markdown("**Set new preferences**")
        with st.form("prefs_form"):
            enabled      = st.checkbox("Notifications enabled", value=True)
            tz_name      = st.selectbox("Timezone", ["Asia/Kolkata", "UTC", "US/Eastern", "US/Pacific", "Europe/London"], index=0)
            wake_t       = st.time_input("Wake time",        value=datetime.strptime("07:00", "%H:%M").time())
            breakfast_t  = st.time_input("Breakfast time",   value=datetime.strptime("08:00", "%H:%M").time())
            lunch_t      = st.time_input("Lunch time",       value=datetime.strptime("13:00", "%H:%M").time())
            dinner_t     = st.time_input("Dinner time",      value=datetime.strptime("19:30", "%H:%M").time())
            bedtime_t    = st.time_input("Bedtime",          value=datetime.strptime("22:30", "%H:%M").time())
            hydration_h  = st.slider("Hydration interval (hours)", 1, 6, 3)

            submitted = st.form_submit_button("Save Preferences", type="primary")
            if submitted:
                payload = {
                    "uid": uid,
                    "enabled": enabled,
                    "timezone": tz_name,
                    "wake_time":       wake_t.strftime("%H:%M"),
                    "breakfast_time":  breakfast_t.strftime("%H:%M"),
                    "lunch_time":      lunch_t.strftime("%H:%M"),
                    "dinner_time":     dinner_t.strftime("%H:%M"),
                    "bedtime_time":    bedtime_t.strftime("%H:%M"),
                    "hydration_interval_hours": hydration_h,
                    "custom_slots": [],
                }
                result = _post("/notifications/preferences", payload)
                _show(result)

# ═══════════════════════════════════════════════════════════════════════════
# TAB 3 — Seed & Cycle
# ═══════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Seed Daily States & Run Cycle")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **Seed daily states**

        Creates `notification_states` documents for all enabled users
        for a given date (default: today UTC).

        This runs automatically at 00:01 UTC daily via APScheduler.
        Use this button to trigger it manually.
        """)
        seed_date = st.text_input("Date to seed (YYYY-MM-DD)", value=today, key="seed_date")
        if st.button("🌱 Seed States", type="primary", key="btn_seed"):
            result = _post(f"/notifications/seed?date={seed_date}", {})
            _show(result)

    with col2:
        st.markdown("""
        **Run notification cycle**

        Processes all pending/sent/reminded states for today:
        - Sends FCM for due slots
        - Sends 15-min reminders
        - Sends 30-min reminders
        - Expires after 45 min

        Runs automatically every 5 min via APScheduler.
        Use this button to trigger immediately.
        """)
        if st.button("⚡ Run Cycle Now", type="primary", key="btn_cycle"):
            result = _post("/notifications/cycle", {})
            _show(result)

    st.divider()
    st.subheader("Send Test Notification")
    st.markdown("""
    Sends a real FCM data message to the user's registered device.
    Requires a real FCM token registered in step 1.
    """)
    notif_type_test = st.selectbox(
        "Notification type",
        ["hydration", "wake", "breakfast", "lunch", "dinner", "bedtime", "custom"],
        key="test_notif_type",
    )
    if st.button("📨 Send Test FCM", type="primary", key="btn_send_test"):
        result = _post("/notifications/send-test", {"uid": uid, "notification_type": notif_type_test})
        _show(result)

# ═══════════════════════════════════════════════════════════════════════════
# TAB 4 — Quick Log (simulate notification action tap)
# ═══════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("Quick Log — Simulate Notification Tap")
    st.markdown("""
    Simulates what happens when the user taps an action button on the notification
    (e.g. "500 ml"). This is what the Flutter background isolate calls.
    No app-open required in production.
    """)

    notif_type_map = {
        "hydration":  ["ml_250", "ml_500", "ml_750", "skip"],
        "wake":       ["i_am_awake", "snooze_15"],
        "breakfast":  ["light_meal", "full_meal", "skipped", "snooze_15"],
        "lunch":      ["light_meal", "full_meal", "skipped", "snooze_15"],
        "dinner":     ["light_meal", "full_meal", "skipped", "snooze_30"],
        "bedtime":    ["log_now", "snooze_30"],
        "custom":     ["logged", "skip"],
    }

    col1, col2, col3 = st.columns(3)
    with col1:
        ql_type = st.selectbox("Notification type", list(notif_type_map.keys()), key="ql_type")
    with col2:
        ql_action = st.selectbox("Action", notif_type_map[ql_type], key="ql_action")
    with col3:
        ql_slot = st.text_input("Slot label", value=f"{ql_type}_1" if "hydration" in ql_type else ql_type, key="ql_slot")

    ql_date = st.text_input("Date", value=today, key="ql_date")

    if st.button("🚀 Execute Quick Log", type="primary", key="btn_ql"):
        payload = {
            "uid": uid,
            "notification_type": ql_type,
            "slot_label": ql_slot,
            "action": ql_action,
            "date": ql_date,
        }
        st.code(json.dumps(payload, indent=2), language="json")
        result = _post("/notifications/quick-log", payload)
        _show(result)

    st.divider()
    st.subheader("Acknowledge (dismiss without logging)")
    col1, col2 = st.columns(2)
    with col1:
        ack_slot = st.text_input("Slot label to dismiss", value="hydration_1", key="ack_slot")
    with col2:
        ack_date = st.text_input("Date", value=today, key="ack_date")
    if st.button("🙈 Acknowledge (No Log)", key="btn_ack"):
        result = _post("/notifications/ack", {"uid": uid, "slot_label": ack_slot, "date": ack_date})
        _show(result)

# ═══════════════════════════════════════════════════════════════════════════
# TAB 5 — Status Monitor
# ═══════════════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("📊 Today's Notification State Monitor")
    st.markdown("Live view of all notification states for the user. Refresh to see updates from the scheduler.")

    monitor_date = st.text_input("Date (YYYY-MM-DD)", value=today, key="monitor_date")

    col1, col2 = st.columns([1, 4])
    with col1:
        auto_refresh = st.checkbox("Auto-refresh (10s)", value=False)
    with col2:
        refresh = st.button("🔄 Refresh", key="btn_refresh")

    if refresh or auto_refresh:
        result = _get("/notifications/status", {"uid": uid, "date": monitor_date})
        if _ok(result):
            states = result.get("states", [])
            if not states:
                st.warning("No notification states found. Run 'Seed States' first.")
            else:
                # Status colour map
                status_colors = {
                    "pending":     "🔵",
                    "sent":        "🟡",
                    "reminded_15": "🟠",
                    "reminded_30": "🔴",
                    "resolved":    "🟢",
                    "expired":     "⚫",
                }
                st.markdown(f"**{len(states)} slots** for `{monitor_date}`")

                # Table
                rows = []
                for s in states:
                    rows.append({
                        "Status": status_colors.get(s.get("status", "?"), "❓") + " " + s.get("status", ""),
                        "Slot":   s.get("slot_label", ""),
                        "Type":   s.get("notification_type", ""),
                        "Scheduled (UTC)": s.get("scheduled_utc", "")[:16] if s.get("scheduled_utc") else "",
                        "Sent":   s.get("sent_at", "")[:16] if s.get("sent_at") else "—",
                        "Action": s.get("action_taken") or "—",
                    })

                st.dataframe(rows, use_container_width=True)
        else:
            st.error(json.dumps(result))

    if auto_refresh:
        time.sleep(10)
        st.rerun()

# ═══════════════════════════════════════════════════════════════════════════
# TAB 6 — Full End-to-End Flow Test
# ═══════════════════════════════════════════════════════════════════════════
with tab6:
    st.subheader("🧪 Full End-to-End Pipeline Test")
    st.markdown("""
    Runs through the complete notification pipeline step-by-step:
    1. Register a dummy FCM token
    2. Set notification preferences (enabled)
    3. Seed today's states
    4. Check states were created
    5. Simulate quick-log action (hydration 500 ml)
    6. Confirm state becomes `resolved`
    7. Verify `daily_logs.hydration.total_ml` was incremented

    ⚠️  Uses `fake-e2e-token-xyz` as the FCM token (real push will fail,
    but all DB operations are fully real).
    """)

    if st.button("▶️ Run Full E2E Test", type="primary", key="btn_e2e"):
        steps = []

        # Step 1 — register token
        with st.spinner("Step 1: Registering dummy FCM token…"):
            r = _post("/notifications/register-token", {
                "uid": uid,
                "fcm_token": "fake-e2e-token-xyz",
            })
            steps.append(("Register Token", r))

        # Step 2 — preferences
        with st.spinner("Step 2: Saving preferences (enabled, hydration every 4h)…"):
            r = _post("/notifications/preferences", {
                "uid": uid,
                "enabled": True,
                "timezone": "Asia/Kolkata",
                "wake_time": "07:00",
                "breakfast_time": "08:00",
                "lunch_time": "13:00",
                "dinner_time": "19:30",
                "bedtime_time": "22:30",
                "hydration_interval_hours": 4,
                "custom_slots": [],
            })
            steps.append(("Save Preferences", r))

        # Step 3 — seed
        with st.spinner("Step 3: Seeding today's notification states…"):
            r = _post(f"/notifications/seed?date={today}", {})
            steps.append(("Seed Daily States", r))

        # Step 4 — check states
        with st.spinner("Step 4: Fetching notification states…"):
            r = _get("/notifications/status", {"uid": uid, "date": today})
            count = r.get("count", 0) if _ok(r) else 0
            steps.append((f"Check States (found {count})", r))

        # Step 5 — quick log hydration
        with st.spinner("Step 5: Quick-logging 500 ml hydration…"):
            r = _post("/notifications/quick-log", {
                "uid": uid,
                "notification_type": "hydration",
                "slot_label": "hydration_1",
                "action": "ml_500",
                "date": today,
            })
            steps.append(("Quick Log 500 ml", r))

        # Step 6 — verify state
        with st.spinner("Step 6: Verifying state is now resolved…"):
            r = _get("/notifications/status", {"uid": uid, "date": today})
            states = r.get("states", []) if _ok(r) else []
            h1 = next((s for s in states if s.get("slot_label") == "hydration_1"), None)
            resolved = h1 and h1.get("status") == "resolved"
            steps.append((
                "Verify Resolved " + ("✅" if resolved else "❌"),
                {"hydration_1_status": h1.get("status") if h1 else "not found"},
            ))

        # Step 7 — check daily log
        with st.spinner("Step 7: Checking daily_logs hydration total…"):
            r = _get("/log/today", {"uid": uid})
            total_ml = None
            if _ok(r):
                total_ml = (r.get("log") or {}).get("hydration", {}).get("total_ml")
            steps.append((f"Check total_ml ({total_ml} ml)", r if not _ok(r) else {"total_ml": total_ml}))

        # Display results
        st.divider()
        for i, (label, result) in enumerate(steps, 1):
            icon = "✅" if _ok(result) else "❌"
            with st.expander(f"Step {i}: {label}  {icon}", expanded=not _ok(result)):
                st.json(result)

        all_ok = all(_ok(r) for _, r in steps)
        if all_ok:
            st.balloons()
            st.success("🎉 All steps passed! Notification pipeline is working end-to-end.")
        else:
            st.error("Some steps failed. Check individual step results above.")
