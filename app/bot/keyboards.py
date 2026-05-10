from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def prompt_actions_keyboard(prompt_session_id: int, can_answer_with_buttons: bool) -> None:
    return None


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


def answer_saved_keyboard(prompt_session_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("💬 read answers", callback_data=f"answers:{prompt_session_id}:0")]]
    )


def answer_pagination_keyboard(prompt_session_id: int, offset: int, page_size: int, total: int) -> InlineKeyboardMarkup:
    buttons: list[InlineKeyboardButton] = []
    if offset > 0:
        previous_offset = max(offset - page_size, 0)
        buttons.append(InlineKeyboardButton("← prev", callback_data=f"answers:{prompt_session_id}:{previous_offset}"))
    if offset + page_size < total:
        next_offset = offset + page_size
        buttons.append(InlineKeyboardButton("next →", callback_data=f"answers:{prompt_session_id}:{next_offset}"))

    if not buttons:
        return InlineKeyboardMarkup([])
    return InlineKeyboardMarkup([buttons])
