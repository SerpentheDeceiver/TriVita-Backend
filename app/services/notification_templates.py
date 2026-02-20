"""
Notification payload templates.

Each template defines:
  - title / body text for the notification
  - `actions`: list of action_ids the Flutter client will show as buttons
  - `data` fields that are always included in the FCM data payload

Action IDs understood by the Flutter quick-log handler:
  Hydration:  ml_250 | ml_500 | ml_750 | skip
  Wake:       i_am_awake | snooze_15 | snooze_30
  Meals:      light_meal | full_meal | skipped | snooze_15
  Bedtime:    log_now | snooze_30
  Custom:     logged | skip

The FCM data dict that gets sent to the device must contain only strings.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NotificationTemplate:
    notification_type: str
    title: str
    body: str
    actions: list[str]          # ordered list of action_ids for the client
    emoji: str = ""             # leading emoji for display

    def to_fcm_data(
        self,
        *,
        uid: str,
        slot_label: str,
        date: str,
        is_reminder: bool = False,
        reminder_count: int = 0,
    ) -> dict[str, str]:
        """
        Build the dict that goes into the FCM `data` payload.
        All values must be strings.
        """
        prefix = "⏰ Reminder: " if is_reminder else ""
        return {
            "notification_type": self.notification_type,
            "slot_label": slot_label,
            "date": date,
            "uid": uid,
            "title": prefix + self.title,
            "body": self.body,
            "actions": ",".join(self.actions),   # Flutter splits on ","
            "is_reminder": str(is_reminder).lower(),
            "reminder_count": str(reminder_count),
            "emoji": self.emoji,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Template registry
# ─────────────────────────────────────────────────────────────────────────────

TEMPLATES: dict[str, NotificationTemplate] = {
    "wake": NotificationTemplate(
        notification_type="wake",
        title="Good morning! ☀️",
        body="How was your sleep last night? Tap to log it.",
        actions=["i_am_awake", "snooze_15"],
        emoji="☀️",
    ),
    "breakfast": NotificationTemplate(
        notification_type="breakfast",
        title="Breakfast time 🍳",
        body="Start the day right — log your morning meal.",
        actions=["light_meal", "full_meal", "skipped", "snooze_15"],
        emoji="🍳",
    ),
    "lunch": NotificationTemplate(
        notification_type="lunch",
        title="Lunch check 🥗",
        body="Midday refuel — what did you eat?",
        actions=["light_meal", "full_meal", "skipped", "snooze_15"],
        emoji="🥗",
    ),
    "dinner": NotificationTemplate(
        notification_type="dinner",
        title="Dinner time 🍽️",
        body="Evening meal — log it to track your nutrition.",
        actions=["light_meal", "full_meal", "skipped", "snooze_30"],
        emoji="🍽️",
    ),
    "hydration": NotificationTemplate(
        notification_type="hydration",
        title="Hydration check 💧",
        body="Time to drink some water! How much will you log?",
        actions=["ml_250", "ml_500", "ml_750", "skip"],
        emoji="💧",
    ),
    "bedtime": NotificationTemplate(
        notification_type="bedtime",
        title="Winding down? 🌙",
        body="Nearly time for bed — log your bedtime now.",
        actions=["log_now", "snooze_30"],
        emoji="🌙",
    ),
    "custom": NotificationTemplate(
        notification_type="custom",
        title="Health reminder 📋",
        body="Don't forget to log your health data.",
        actions=["logged", "skip"],
        emoji="📋",
    ),
}


def get_template(notification_type: str) -> NotificationTemplate:
    return TEMPLATES.get(notification_type, TEMPLATES["custom"])


# ─────────────────────────────────────────────────────────────────────────────
# Action → log mapping  (used by /quick-log route)
# ─────────────────────────────────────────────────────────────────────────────

# Maps (notification_type, action_id) → what to write in daily_logs
ACTION_LABEL_MAP: dict[str, str] = {
    "ml_250":      "Added 250 ml water",
    "ml_500":      "Added 500 ml water",
    "ml_750":      "Added 750 ml water",
    "skip":        "Skipped",
    "i_am_awake":  "Wake time logged",
    "snooze_15":   "Snoozed 15 min",
    "snooze_30":   "Snoozed 30 min",
    "light_meal":  "Logged light meal",
    "full_meal":   "Logged full meal",
    "skipped":     "Meal skipped",
    "log_now":     "Bedtime logged",
    "logged":      "Logged",
}

ML_ACTION_MAP: dict[str, int] = {
    "ml_250": 250,
    "ml_500": 500,
    "ml_750": 750,
}

SNOOZE_MINUTES: dict[str, int] = {
    "snooze_15": 15,
    "snooze_30": 30,
}
