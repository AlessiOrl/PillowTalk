from __future__ import annotations

from html import escape
from math import floor
from random import choice as pick

from app.models.question import QUESTION_CATEGORY_ACTION, QUESTION_CATEGORY_CLOSED


# ── branding ────────────────────────────────────────────────────
APP_TAG = "☽ <b>pillowtalk</b>"
SEP = "─   ─   ─   ─   ─  "
SEP_LIGHT = "  "

# ── micro-copy pools ───────────────────────────────────────────
_SAVED_REACTIONS = ["noted. 🤫", "locked in. 💫", "heard you. ✨", "saved. 🫧"]
_STREAK_HYPE = [
    "you're on fire rn 🔥",
    "don't break the chain ✨",
    "streak is alive 🔥",
    "keep going, it's glowing 🌙",
]


def _rand_saved() -> str:
    return pick(_SAVED_REACTIONS)


def _rand_streak_hype() -> str:
    return pick(_STREAK_HYPE)


def _streak_display(streak: int) -> str:
    if streak <= 0:
        return "🕯 streak reset — answer tonight to start fresh"
    flames = "🔥" * min(streak, 5)
    return f"{flames} <b>{streak}</b>-day streak"


def _social_count(answer_count: int | None, has_group: bool) -> str:
    if has_group and answer_count is not None:
        others = max(answer_count - 1, 0)
        if others == 0:
            return "you're the first one tonight 👀"
        return f"you + <b>{others}</b> others answered tonight"
    return "join a group to see what others said"


def welcome_message(display_name: str | None) -> str:
    name = escape(display_name or "you")
    return (
        f"{APP_TAG}\n"
        f"{SEP}\n\n"
        f"hey {name} 🫧\n\n"
        "one question a day.\n"
        "one honest answer.\n"
        "late-night energy only.\n\n"
        f"{SEP_LIGHT}\n\n"
        "when the question drops — just reply here.\n"
        "no names. no judgement."
    )


def returning_user_message() -> str:
    return (
        f"{APP_TAG}\n"
        f"{SEP}\n\n"
        "welcome back ✨\n\n"
        "you're already in.\n"
        "tonight's question will land soon — just answer here."
    )


def daily_question_message(question_text: str, category: str | None) -> str:
    if category == QUESTION_CATEGORY_CLOSED:
        footer = "tap the name that fits most 👇"
    elif category == QUESTION_CATEGORY_ACTION:
        footer = "action mode isn't live yet — hang tight 🛸"
    else:
        footer = "reply with whatever comes to mind.\nbe honest. 🤫"

    return (
        f"today's question 🌙\n"
        f"{SEP}\n\n"
        f"<b>{escape(question_text)}</b>\n\n"
        f"{SEP_LIGHT}\n"
        f"{footer}"
    )


def answer_saved_message(streak: int, answer_count: int | None, updated: bool, has_group: bool) -> str:
    header = "answer updated 🔄" if updated else _rand_saved()
    return (
        f"{header}\n\n"
        f"{_streak_display(streak)}\n"
        f"{_social_count(answer_count, has_group)}"
    )


def open_answer_cleanup_message(seconds_remaining: int) -> str:
    dots = "•" * seconds_remaining
    return f"✓ answer saved\n\n{dots}"


def closed_answer_saved_message(chosen_name: str, streak: int, answer_count: int | None, updated: bool) -> str:
    header = "choice updated 🔄" if updated else "choice locked in 💫"
    others = max((answer_count or 0) - 1, 0)
    social = f"you + <b>{others}</b> others answered tonight" if others else "you're the first one tonight 👀"
    return (
        f"{header}\n\n"
        f"→ <b>{escape(chosen_name)}</b>\n\n"
        f"{_streak_display(streak)}\n"
        f"{social}"
    )


def skip_message() -> str:
    return "skipped 🕯\nstreak cooled off."


def streak_message(streak: int) -> str:
    if streak <= 0:
        return (
            "no streak yet 🕯\n\n"
            "answer tonight to light it up."
        )
    return (
        f"{_streak_display(streak)}\n"
        f"{_rand_streak_hype()}"
    )


def group_required_message() -> str:
    return (
        "you need a group first 🫧\n\n"
        "ask a friend for a code, then:\n"
        "<code>/join CODE</code>"
    )


def no_prompt_message() -> str:
    return (
        "nothing live yet 🌙\n\n"
        "the first question drops soon.\nwe'll ping you."
    )


def no_group_answers_message() -> str:
    return (
        "quiet room 🤫\n\n"
        "no one else in your group answered yet.\n"
        "you could be the first."
    )


def closed_question_group_required_message() -> str:
    return (
        "this one needs a group 🫧\n"
        "join one first — then pick from your people."
    )


def closed_question_no_members_message() -> str:
    return "your group is empty rn — no names to pick yet."


def closed_question_text_input_message() -> str:
    return "this one is pick-only 👆\nuse the buttons under the question."


def action_not_implemented_message() -> str:
    return "action mode isn't live yet 🛸\njust a teaser for now."


def anonymous_answer_message(answer_text: str, page: int, total: int) -> str:
    return (
        f"💬 someone in your group said…\n\n"
        f"<i>{escape(answer_text)}</i>\n\n"
        f"{SEP_LIGHT}\n"
        f"{page} / {total}"
    )



def read_answers_message(
    question_text: str,
    category: str | None,
    answer_lines: list[str],
    *,
    page_start: int,
    page_end: int,
    total: int,
    distribution_rows: list[tuple[str, int, int]] | None = None,
) -> str:
    lines = [
        "tonight's answers 🌙",
        SEP,
        "",
        f"<b>{escape(question_text)}</b>",
        "",
    ]

    if category == QUESTION_CATEGORY_CLOSED and distribution_rows:
        lines.append("")
        for label, count, total_answers in distribution_rows:
            pct = round((count / total_answers) * 100) if total_answers > 0 else 0
            lines.append(f"  {escape(label)}")
            lines.append(f"  {distribution_bar(count, total_answers)}  <b>{pct}%</b>  ({count})")
            lines.append("")
    else:
        lines.extend(["", SEP_LIGHT, ""])
        lines.extend(answer_lines)

    return "\n".join(lines)


def answer_feed_entry(answer_text: str, *, is_current_user: bool) -> str:
    if is_current_user:
        return f"🫵 <b>you</b> said:\n<i>{escape(answer_text)}</i>"
    return f"💬 someone said:\n<i>{escape(answer_text)}</i>"


def closed_answer_feed_entry(answer_text: str, *, is_current_user: bool) -> str:
    if is_current_user:
        return f"🫵 <b>you</b> picked: <b>{escape(answer_text)}</b>"
    return f"💬 someone picked: <b>{escape(answer_text)}</b>"


def distribution_bar(count: int, total: int, *, width: int = 14) -> str:
    if total <= 0:
        return "░" * width
    filled = max(1, floor((count / total) * width)) if count > 0 else 0
    return "▓" * filled + "░" * (width - filled)


def group_joined_message(group_name: str) -> str:
    return (
        f"you're in ✨\n\n"
        f"group: <b>{escape(group_name)}</b>\n"
        "you'll only see answers from your people now."
    )


def group_left_message() -> str:
    return (
        "you left the group 🫧\n\n"
        "no more group answers until you join another one."
    )


def my_group_message(group_name: str, member_count: int) -> str:
    return (
        f"👥 <b>{escape(group_name)}</b>\n"
        f"{SEP_LIGHT}\n"
        f"members: <b>{member_count}</b>"
    )


def group_created_message(group_name: str, invite_code: str) -> str:
    return (
        f"group created ✨\n\n"
        f"<b>{escape(group_name)}</b>\n"
        f"invite code: <code>{escape(invite_code)}</code>\n\n"
        "share it with your people 🫧"
    )


def member_added_message(telegram_id: int, group_name: str) -> str:
    return f"✓ added <code>{telegram_id}</code> → <b>{escape(group_name)}</b>"


def invalid_group_code_message() -> str:
    return "that code doesn't match anything 🤔\ndouble-check and try again."


def admin_only_message() -> str:
    return "🔒 admin only."


def force_next_done_message(question_text: str) -> str:
    return (
        f"✓ new question sent\n\n"
        f"<b>{escape(question_text)}</b>"
    )


def closed_question_member_label(nickname: str | None, display_name: str | None, username: str | None, telegram_id: int) -> str:
    if nickname:
        return nickname
    if display_name:
        return display_name
    if username:
        return f"@{username}"
    return f"user {telegram_id}"


def usage_message(command: str, example: str) -> str:
    return f"use it like this:\n<code>{escape(command)} {escape(example)}</code>"


def join_group_prompt_message() -> str:
    return (
        "drop the invite code 🫧\n\n"
        "<code>/join CODE</code>"
    )


def create_group_prompt_message() -> str:
    return (
        "give your group a name ✨\n\n"
        "<code>/creategroup name</code>"
    )


def add_member_prompt_message() -> str:
    return (
        "add a member like this:\n\n"
        "<code>/addmember 123456789 ABCD1234</code>"
    )


def nickname_set_message(nickname: str) -> str:
    return (
        f"you're now <b>{escape(nickname)}</b> in your group \u2728\n"
        "that's how others will see you."
    )


def nickname_cleared_message() -> str:
    return "nickname cleared \ud83e\udee7\nyour telegram name will be used instead."


def nickname_prompt_message() -> str:
    return (
        "pick a name for your group \u2728\n\n"
        "<code>/nickname yourname</code>\n\n"
        "this is how you'll show up in polls and answers."
    )


def nickname_too_long_message() -> str:
    return "keep it under 32 characters \ud83d\ude45"
