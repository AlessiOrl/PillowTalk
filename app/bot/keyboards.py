from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def prompt_actions_keyboard(prompt_session_id: int, can_answer_with_buttons: bool) -> None:
    return None


def choice_question_keyboard(prompt_session_id: int, options: list[str], *, columns: int = 2) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for option_index, label in enumerate(options):
        row.append(InlineKeyboardButton(label, callback_data=f"choice:{prompt_session_id}:{option_index}"))
        if len(row) == columns:
            rows.append(row)
            row = []

    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def closed_question_keyboard(prompt_session_id: int, members: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for member_id, label in members:
        row.append(InlineKeyboardButton(f"  {label[:28]}  ", callback_data=f"pick:{prompt_session_id}:{member_id}"))
        if len(row) == 2:
            rows.append(row)
            row = []

    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def _answer_reaction_buttons(prompt_session_id: int, rating: str | None = None) -> list[InlineKeyboardButton]:
    return [
        InlineKeyboardButton(
            "👍 like" if rating != "like" else "✅ like",
            callback_data=f"react:{prompt_session_id}:like",
        ),
        InlineKeyboardButton(
            "😐 neutral" if rating != "neutral" else "✅ neutral",
            callback_data=f"react:{prompt_session_id}:neutral",
        ),
        InlineKeyboardButton(
            "👎 dislike" if rating != "dislike" else "✅ dislike",
            callback_data=f"react:{prompt_session_id}:dislike",
        ),
    ]


def answer_saved_keyboard(prompt_session_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💬 read answers", callback_data=f"answers:{prompt_session_id}:0")],
        ]
    )


def answer_feed_keyboard(
    prompt_session_id: int,
    *,
    rating: str | None = None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    rows.append(_answer_reaction_buttons(prompt_session_id, rating))
    return InlineKeyboardMarkup(rows)


def action_done_keyboard(prompt_session_id: int, assignment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("✅ done", callback_data=f"actiondone:{prompt_session_id}:{assignment_id}")]]
    )


def action_completed_keyboard(prompt_session_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💬 read answers", callback_data=f"answers:{prompt_session_id}:0")],
        ]
    )


def help_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔧 admin commands", callback_data="helpadmin")]]
    )
