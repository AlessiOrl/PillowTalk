from __future__ import annotations

from html import escape
from math import floor

from app.models.question import QUESTION_CATEGORY_ACTION, QUESTION_CATEGORY_CLOSED


APP_TAG = "<b>pillowtalk</b>"


def welcome_message(display_name: str | None) -> str:
    name = escape(display_name or "you")
    return (
        f"{APP_TAG}\n"
        f"hey {name} ✨\n\n"
        "one question a day.\n"
        "one honest answer.\n"
        "late-night energy only.\n\n"
        "when the question drops, just reply here."
    )


def returning_user_message() -> str:
    return (
        f"{APP_TAG}\n"
        "you’re already in.\n"
        "when tonight’s question lands, just answer here."
    )


def daily_question_message(question_text: str, category: str | None) -> str:
    if category == QUESTION_CATEGORY_CLOSED:
        footer = "tap the name that fits most."
    elif category == QUESTION_CATEGORY_ACTION:
        footer = "action mode isn’t live yet. hang tight."
    else:
        footer = "reply however you want. be honest."

    return "tonight’s question 🌙\n" f"<b>{escape(question_text)}</b>\n\n" f"{footer}"


def answer_saved_message(streak: int, answer_count: int | None, updated: bool, has_group: bool) -> str:
    verb = "updated" if updated else "saved"
    streak_line = f"streak: <b>{streak}</b> 🔥" if streak else "streak reset. start again tomorrow."
    if has_group and answer_count is not None:
        others = max(answer_count - 1, 0)
        social_line = f"you + <b>{others}</b> others answered in your group tonight."
    else:
        social_line = "join a group to unlock everyone else’s answers."

    return (
        f"answer {verb}.\n"
        f"{streak_line}\n"
        f"{social_line}"
    )


def open_answer_cleanup_message(seconds_remaining: int) -> str:
    return f"answer saved.\ncleaning chat in <b>{seconds_remaining}</b>…"


def closed_answer_saved_message(chosen_name: str, streak: int, answer_count: int | None, updated: bool) -> str:
    verb = "updated" if updated else "locked in"
    streak_line = f"streak: <b>{streak}</b> 🔥" if streak else "streak reset. start again tomorrow."
    others = max((answer_count or 0) - 1, 0)
    return (
        f"choice {verb}: <b>{escape(chosen_name)}</b>\n"
        f"{streak_line}\n"
        f"you + <b>{others}</b> others answered in your group tonight."
    )


def skip_message() -> str:
    return "skipped.\nstreak cooled off."


def streak_message(streak: int) -> str:
    if streak <= 0:
        return "no fire yet.\nanswer tonight and start the streak."
    return f"current streak: <b>{streak}</b> 🔥"


def group_required_message() -> str:
    return "you need a group first.\njoin one with <code>/join CODE</code>."


def no_prompt_message() -> str:
    return "nothing live yet.\nfirst question drops soon."


def no_group_answers_message() -> str:
    return "quiet room.\nno one else in your group answered yet."


def closed_question_group_required_message() -> str:
    return "this one needs a group.\njoin one first, then pick from your people."


def closed_question_no_members_message() -> str:
    return "your group is empty right now.\nno names to pick yet."


def closed_question_text_input_message() -> str:
    return "this one is pick-only.\nuse the buttons under the question."


def action_not_implemented_message() -> str:
    return "action questions aren’t live yet.\nthis one’s just a teaser for now."


def anonymous_answer_message(answer_text: str, page: int, total: int) -> str:
    return (
        f"someone in your group said…\n\n"
        f"“{escape(answer_text)}”\n\n"
        f"{page}/{total}"
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
    lines = ["tonight's question 🌙", f"<b>{escape(question_text)}</b>", "", f"answers shown: <b>{page_start}-{page_end}</b> of <b>{total}</b>"]

    if category == QUESTION_CATEGORY_CLOSED and distribution_rows:
        lines.extend(["", "distribution"])
        for label, count, total_answers in distribution_rows:
            lines.append(f"{escape(label)} {distribution_bar(count, total_answers)} {count}")

    lines.extend(["", "answers"])
    lines.extend(answer_lines)
    return "\n".join(lines)


def answer_feed_entry(answer_text: str, *, is_current_user: bool) -> str:
    speaker = "you said" if is_current_user else "someone said"
    return f"{speaker}:\n“{escape(answer_text)}”"


def closed_answer_feed_entry(answer_text: str, *, is_current_user: bool) -> str:
    speaker = "you picked" if is_current_user else "someone picked"
    return f"{speaker}: <b>{escape(answer_text)}</b>"


def distribution_bar(count: int, total: int, *, width: int = 10) -> str:
    if total <= 0:
        return "-" * width
    filled = max(1, floor((count / total) * width)) if count > 0 else 0
    return "█" * filled + "░" * (width - filled)


def group_joined_message(group_name: str) -> str:
    return f"you’re in <b>{escape(group_name)}</b> ✨\nnow you’ll only see answers from this group."


def group_left_message() -> str:
    return "you left the group.\nno more group answers until you join another one."


def my_group_message(group_name: str, member_count: int) -> str:
    return f"your group: <b>{escape(group_name)}</b>\npeople inside: <b>{member_count}</b>"


def group_created_message(group_name: str, invite_code: str) -> str:
    return (
        f"group made: <b>{escape(group_name)}</b>\n"
        f"invite code: <code>{escape(invite_code)}</code>"
    )


def member_added_message(telegram_id: int, group_name: str) -> str:
    return f"added <code>{telegram_id}</code> to <b>{escape(group_name)}</b>."


def invalid_group_code_message() -> str:
    return "that code doesn’t hit.\ncheck it and try again."


def admin_only_message() -> str:
    return "admin only.\nno sneaking in."


def force_next_done_message(question_text: str) -> str:
    return f"new question sent.\n<b>{escape(question_text)}</b>"


def closed_question_member_label(display_name: str | None, username: str | None, telegram_id: int) -> str:
    if display_name:
        return display_name
    if username:
        return f"@{username}"
    return f"user {telegram_id}"


def usage_message(command: str, example: str) -> str:
    return f"use it like this:\n<code>{escape(command)} {escape(example)}</code>"


def join_group_prompt_message() -> str:
    return "send the invite code for the group you want to join."


def create_group_prompt_message() -> str:
    return "send the name for the new group."


def add_member_prompt_message() -> str:
    return "send the member details as:\n<code>123456789 ABCD1234</code>"
