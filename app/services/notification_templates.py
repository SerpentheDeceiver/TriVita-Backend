# Notification templates and actions for the 16 slots.

from dataclasses import dataclass
from typing import Optional


@dataclass
class NotificationTemplate:
    notification_type: str
    title: str
    body: str
    emoji: str = ""
    # All templates use the same 3-action quick-log system
    actions: list[str] = None  # type: ignore

    def __post_init__(self):
        if self.actions is None:
            self.actions = ["yes", "need_15_min", "need_30_min"]

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
            "slot_label":        slot_label,
            "date":              date,
            "uid":               uid,
            "title":             prefix + self.title,
            "body":              self.body,
            "actions":           ",".join(self.actions),  # Flutter splits on ","
            "is_reminder":       str(is_reminder).lower(),
            "reminder_count":    str(reminder_count),
            "emoji":             self.emoji,
        }


# Registry

TEMPLATES: dict[str, NotificationTemplate] = {

    # Scheduler
    "wake": NotificationTemplate(
        notification_type="wake",
        title="Good morning! ☀️",
        body="Time to rise! Tap Yes to log your wake time.",
        emoji="☀️",
    ),
    "bedtime": NotificationTemplate(
        notification_type="bedtime",
        title="Bedtime 🌙",
        body="Heading to bed? Tap Yes to log your sleep.",
        emoji="🌙",
    ),

    # Required in production
    "breakfast": NotificationTemplate(
        notification_type="breakfast",
        title="Breakfast time 🍳",
        body="Start your day right — tap Yes to log breakfast.",
        emoji="🍳",
    ),
    "mid_morning": NotificationTemplate(
        notification_type="mid_morning",
        title="Mid-morning snack 🍎",
        body="Mid-morning bite? Tap Yes to log it.",
        emoji="🍎",
    ),
    "lunch": NotificationTemplate(
        notification_type="lunch",
        title="Lunch time 🥗",
        body="Midday refuel — tap Yes to log your lunch.",
        emoji="🥗",
    ),
    "afternoon_break": NotificationTemplate(
        notification_type="afternoon_break",
        title="Afternoon snack 🍪",
        body="Afternoon snack time! Tap Yes to log it.",
        emoji="🍪",
    ),
    "dinner": NotificationTemplate(
        notification_type="dinner",
        title="Dinner time 🍽️",
        body="Evening meal — tap Yes to log your dinner.",
        emoji="🍽️",
    ),
    "post_dinner": NotificationTemplate(
        notification_type="post_dinner",
        title="Post-dinner 🍵",
        body="After-dinner snack or tea? Tap Yes to log it.",
        emoji="🍵",
    ),

    "hydration": NotificationTemplate(
        notification_type="hydration",
        title="Hydration check 💧",
        body="Time to drink 250 ml of water! Tap Yes to log it.",
        emoji="💧",
    ),
}


def get_template(notification_type: str) -> NotificationTemplate:
    """Return the template for notification_type, defaulting to hydration."""
    return TEMPLATES.get(notification_type, TEMPLATES["hydration"])


# Action mappings

# Human-readable label for each resolved action (stored in action_taken field)
ACTION_LABEL_MAP: dict[str, str] = {
    "yes":          "Logged ✓",
    "need_15_min":  "Snoozed 15 min",
    "need_30_min":  "Snoozed 30 min",
}

# Hydration: "yes" always logs 250 ml (equal portion across 8 slots = 2 L/day)
HYDRATION_ML_PER_SLOT: int = 250

# Snooze durations in minutes — used by the scheduler and quick-log handler
SNOOZE_MINUTES: dict[str, int] = {
    "need_15_min": 15,
    "need_30_min": 30,
}

# Backwards-compat alias (old code may import ML_ACTION_MAP)
ML_ACTION_MAP: dict[str, int] = {
    "yes": HYDRATION_ML_PER_SLOT,
}

# Nutrition meal types that are handled by the quick-log endpoint
NUTRITION_MEAL_TYPES: set[str] = {
    "breakfast", "mid_morning", "lunch", "afternoon_break", "dinner", "post_dinner"
}
