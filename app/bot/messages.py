from __future__ import annotations

from html import escape
from random import choice as pick

from app.models.question import QUESTION_CATEGORY_ACTION, QUESTION_CATEGORY_CLOSED, QUESTION_CATEGORY_WOULD


APP_TAG = "☽ <b>Pillow Talk</b>"
SEP = "─   ─   ─   ─   ─  "
SEP_LIGHT = "  "

_SAVED_REACTIONS = ["Kept for tonight. ✨", "Held close. 🤍", "Saved for later. 🌙", "Softly noted. 🫧"]
_STREAK_HYPE = [
    "Keep the rhythm going 🔥",
    "Still warm tonight ✨",
    "The streak is still glowing 🌙",
    "Come back tomorrow night 🤍",
]
_QUESTION_INTROS = [
    "Tonight's little question 🌙",
    "A little question for tonight 🌙",
    "Something soft for tonight 🌙",
    "Tonight's quiet question 🌙",
    "A small question before sleep 🌙",
    "One for the night 🌙",
]


def _rand_saved() -> str:
    return pick(_SAVED_REACTIONS)


def _rand_streak_hype() -> str:
    return pick(_STREAK_HYPE)


def _rand_question_intro() -> str:
    return pick(_QUESTION_INTROS)


def _streak_display(streak: int) -> str:
    if streak <= 0:
        return "No streak yet"
    flames = "🔥" * min(streak, 5)
    return f"{flames} <b>{streak}</b>-day streak"


def _social_count(answer_count: int | None, has_group: bool) -> str:
    if has_group and answer_count is not None:
        others = max(answer_count - 1, 0)
        if others == 0:
            return "You're the first voice tonight 👀"
        return f"You + <b>{others}</b> shared something tonight"
    return "Join a group to read what others shared"


def welcome_message(display_name: str | None) -> str:
    name = escape(display_name or "you")
    return (
        f"{APP_TAG}\n"
        f"{SEP}\n\n"
        f"Hi {name}.\n\n"
        "One question each night.\n"
        "A small moment to share something real.\n\n"
        "Begin with:\n"
        "• <code>/join CODE</code>\n"
        "• <code>/creategroup NAME</code>\n\n"
        "Use <code>/help</code> anytime."
    )


def returning_user_message() -> str:
    return (
        f"{APP_TAG}\n"
        f"{SEP}\n\n"
        "You're back. Right on time. 🌙\n\n"
        "When tonight's question arrives, answer here.\n"
        "Use <code>/help</code> if you need anything."
    )


def help_message() -> str:
    return (
        f"{APP_TAG}\n"
        f"{SEP}\n\n"
        "<b>Commands</b>\n\n"
        "<code>/read</code> read tonight's answers\n"
        "<code>/streak</code> check your streak\n"
        "<code>/nickname NAME</code> choose how you appear\n\n"
        "<b>Groups</b>\n\n"
        "<code>/join CODE</code> join a group\n"
        "<code>/creategroup NAME</code> create a group\n"
        "<code>/addmember ID</code> add someone\n"
        "<code>/mygroup</code> view your group\n"
        "<code>/leavegroup</code> leave your group\n\n"
        "A new question arrives each night.\n"
        "Reply here when you're ready."
    )


def help_admin_message() -> str:
    return (
        f"{APP_TAG}\n"
        f"{SEP}\n\n"
        "<b>Admin commands</b>\n\n"
        "<code>/next</code> send the next question now\n"
        "<code>/reload</code> reload questions from CSV\n"
        "<code>/ratingscsv</code> export rated answers as CSV\n"
        "<code>/questiontime HH</code> set drop time\n"
        "<code>/questiontime HH:MM</code> set drop time with minutes\n"
        "<code>/addmember ID</code> add a user to your group"
    )


def daily_question_message(question_text: str, category: str | None) -> str:
    if category == QUESTION_CATEGORY_CLOSED:
        footer = "Tap the name that feels right."
    elif category == QUESTION_CATEGORY_WOULD:
        footer = "Choose the answer that feels closest."
    elif category == QUESTION_CATEGORY_ACTION:
        footer = "Check your DM for your little mission."
    else:
        footer = "Answer when you're ready."

    return (
        f"{_rand_question_intro()}\n\n"
        f"<b><tg-spoiler>{escape(question_text)}</tg-spoiler></b>\n\n"
        f"{footer}"
    )


def answer_saved_message(streak: int, answer_count: int | None, updated: bool, has_group: bool) -> str:
    header = "Answer updated." if updated else _rand_saved()
    return (
        f"{header}\n\n"
        f"{_streak_display(streak)}\n"
        f"{_social_count(answer_count, has_group)}"
    )


def open_answer_cleanup_message(seconds_remaining: int) -> str:
    dots = "•" * seconds_remaining
    return f"Kept for tonight.\n\n{dots}"


def closed_answer_saved_message(chosen_name: str, streak: int, answer_count: int | None, updated: bool) -> str:
    header = "Choice updated." if updated else "Choice kept."
    others = max((answer_count or 0) - 1, 0)
    social = f"You + <b>{others}</b> shared something tonight" if others else "You're the first voice tonight 👀"
    return (
        f"{header}\n\n"
        f"→ <b>{escape(chosen_name)}</b>\n\n"
        f"{_streak_display(streak)}\n"
        f"{social}"
    )


def choice_answer_saved_message(choice_label: str, streak: int, answer_count: int | None, updated: bool) -> str:
    header = "Choice updated." if updated else "Choice kept."
    others = max((answer_count or 0) - 1, 0)
    social = f"You + <b>{others}</b> shared something tonight" if others else "You're the first voice tonight 👀"
    return (
        f"{header}\n\n"
        f"→ <b>{escape(choice_label)}</b>\n\n"
        f"{_streak_display(streak)}\n"
        f"{social}"
    )


def skip_message() -> str:
    return "Skipped for tonight.\nYour streak ended."


def streak_message(streak: int) -> str:
    if streak <= 0:
        return "No streak yet.\n\nAnswer tonight to begin one."
    return f"{_streak_display(streak)}\n{_rand_streak_hype()}"


def group_required_message() -> str:
    return (
        "You need a group first.\n\n"
        "Use an invite code:\n"
        "<code>/join CODE</code>"
    )


def no_prompt_message() -> str:
    return "Nothing live just yet.\n\nThe next question will arrive here tonight."


def no_group_answers_message() -> str:
    return "No one else has answered yet.\n\nFor now, it's just you."


def closed_question_group_required_message() -> str:
    return "This question needs a group.\nJoin one first, then choose a name."


def closed_question_no_members_message() -> str:
    return "Your group is quiet right now. No names to pick yet."


def closed_question_text_input_message() -> str:
    return "Use the buttons under the question."


def choice_question_text_input_message() -> str:
    return "Use the buttons under the question."


def action_not_implemented_message() -> str:
    return "Action mode isn't live yet."


def action_prompt_message(action_text: str) -> str:
    return (
        f"Tonight's action 🎯\n\n"
        f"<b><tg-spoiler>{escape(action_text)}</tg-spoiler></b>\n\n"
        "Do it, then tap done when it's yours."
    )


def action_completed_message(action_text: str, streak: int) -> str:
    return (
        f"Done for tonight. ✅\n\n"
        f"<i>{escape(action_text)}</i>\n\n"
        f"{_streak_display(streak)}"
    )


def action_already_completed_message() -> str:
    return "Already marked as done tonight."


def action_no_assignment_message() -> str:
    return "No action waiting for you yet."


def action_feed_entry(action_text: str, user_label: str, *, is_current_user: bool) -> str:
    if is_current_user:
        return f"<b>you</b> did:\n<i>{escape(action_text)}</i>"
    return f"<b>{escape(user_label)}</b> did:\n<i>{escape(action_text)}</i>"


def no_completed_actions_message() -> str:
    return "No one has completed theirs yet.\n\nBe the first tonight."


def anonymous_answer_message(answer_text: str, page: int, total: int) -> str:
    return (
        f"Someone in your group whispered:\n\n"
        f"<i>{escape(answer_text)}</i>\n\n"
        f"{SEP_LIGHT}\n"
        f"{page} / {total}"
    )


def read_answers_message(
    question_text: str,
    category: str | None,
    answer_lines: list[str],
) -> str:
    lines = [
        "Tonight's answers 🌙",
        "",
        f"<b>{escape(question_text)}</b>",
    ]

    lines.extend(["", *answer_lines])

    return "\n".join(lines)


def _answer_feed_item(user_label: str, content: str) -> str:
    return f"• <b>{escape(user_label)}</b>\n<i>{content}</i>"


def answer_feed_entry(user_label: str, answer_text: str) -> str:
    return _answer_feed_item(user_label, escape(answer_text))


def closed_answer_feed_entry(user_label: str, answer_text: str) -> str:
    return f"• <b>{escape(user_label)}</b> answered: <i>{escape(answer_text)}</i>"


def group_joined_message(group_name: str) -> str:
    return (
        f"You're in. ✨\n\n"
        f"<b>{escape(group_name)}</b>\n"
        "You'll now see what your group shares each night."
    )


def group_left_message() -> str:
    return "You left the group.\n\nJoin another one to keep sharing answers."


def my_group_message(group_name: str, member_count: int) -> str:
    return f"👥 <b>{escape(group_name)}</b>\n{SEP_LIGHT}\n<b>{member_count}</b> hearts in the room"


def group_created_message(group_name: str, invite_code: str) -> str:
    return (
        f"Your group is ready. ✨\n\n"
        f"<b>{escape(group_name)}</b>\n"
        f"Code: <code>{escape(invite_code)}</code>\n\n"
        "Share the code with the people you want here."
    )


def member_added_message(telegram_id: int, group_name: str) -> str:
    return f"Added <code>{telegram_id}</code> to <b>{escape(group_name)}</b>."


def invalid_group_code_message() -> str:
    return "That invite code doesn't feel right.\nCheck it and try again."


def admin_only_message() -> str:
    return "Admin only."


def force_next_done_message(question_text: str) -> str:
    return f"New question sent into the night.\n\n<b>{escape(question_text)}</b>"


def question_time_usage_message(current_time: str, timezone: str) -> str:
    return (
        f"Current question time: <b>{escape(current_time)}</b> ({escape(timezone)})\n\n"
        "Use 24h format:\n"
        "<code>/questiontime 22</code>\n"
        "<code>/questiontime 22:30</code>"
    )


def question_time_invalid_message() -> str:
    return "Use a valid 24h time, like <code>/questiontime 22</code> or <code>/questiontime 22:30</code>."


def question_time_set_message(time_text: str, timezone: str) -> str:
    return f"Question time set for <b>{escape(time_text)}</b> ({escape(timezone)})."


def closed_question_member_label(nickname: str | None, display_name: str | None, username: str | None, telegram_id: int) -> str:
    if nickname:
        return nickname
    if display_name:
        return display_name
    if username:
        return f"@{username}"
    return f"user {telegram_id}"


def usage_message(command: str, example: str) -> str:
    return f"Use it like this:\n<code>{escape(command)} {escape(example)}</code>"


def join_group_prompt_message() -> str:
    return "Send the invite code.\n\n<code>/join CODE</code>"


def create_group_prompt_message() -> str:
    return "Choose a name for your little circle.\n\n<code>/creategroup name</code>"


def add_member_prompt_message() -> str:
    return "Add a member like this:\n\n<code>/addmember 123456789 ABCD1234</code>"


def nickname_set_message(nickname: str) -> str:
    return (
        f"You'll appear as <b>{escape(nickname)}</b>.\n"
        "That's how your group will know you tonight."
    )


def nickname_cleared_message() -> str:
    return "Nickname cleared.\nYour Telegram name will be used tonight."


def nickname_prompt_message() -> str:
    return (
        "Choose a name for tonight.\n\n"
        "<code>/nickname yourname</code>\n\n"
        "This is how you'll appear in answers."
    )


def nickname_too_long_message() -> str:
    return "Keep it under 32 characters."
