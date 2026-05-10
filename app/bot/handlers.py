from __future__ import annotations

import asyncio
import logging
from datetime import date

from telegram import InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    Defaults,
    MessageHandler,
    filters,
)

from app.bot import keyboards, messages
from app.config import get_settings
from app.database import get_session
from app.models.answer import ANSWER_RATING_DISLIKE, ANSWER_RATING_LIKE, ANSWER_RATING_NEUTRAL
from app.models.question import (
    BUTTON_QUESTION_CATEGORIES,
    CHOICE_QUESTION_OPTIONS,
    QUESTION_CATEGORY_ACTION,
    QUESTION_CATEGORY_CLOSED,
)
from app.services.action_service import ActionService
from app.services.answer_service import AnswerService
from app.services.app_settings_service import AppSettingsService
from app.services.group_service import GroupService
from app.services.question_service import PromptDispatch, QuestionService
from app.services.scheduler import DailyQuestionScheduler
from app.services.user_service import UserService

logger = logging.getLogger(__name__)


class pillowtalkBot:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.enabled = bool(self.settings.telegram_bot_token)
        self.application: Application | None = None
        self.scheduler: DailyQuestionScheduler | None = None
        if self.enabled:
            defaults = Defaults(parse_mode=self.settings.message_parse_mode)
            self.application = Application.builder().token(self.settings.telegram_bot_token).defaults(defaults).build()
            self._register_handlers()

    def bind_scheduler(self, scheduler: DailyQuestionScheduler) -> None:
        self.scheduler = scheduler

    def _register_handlers(self) -> None:
        if self.application is None:
            return

        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("streak", self.streak_command))
        self.application.add_handler(CommandHandler("read", self.read_command))
        self.application.add_handler(CommandHandler("join", self.join_group_command))
        self.application.add_handler(CommandHandler("mygroup", self.my_group_command))
        self.application.add_handler(CommandHandler("leavegroup", self.leave_group_command))
        self.application.add_handler(CommandHandler("creategroup", self.create_group_command))
        self.application.add_handler(CommandHandler("addmember", self.add_member_command))
        self.application.add_handler(CommandHandler("nickname", self.nickname_command))
        self.application.add_handler(CommandHandler("next", self.force_next_command))
        self.application.add_handler(CommandHandler("reload", self.reload_command))
        self.application.add_handler(CommandHandler("questiontime", self.question_time_command))
        self.application.add_handler(CallbackQueryHandler(self.help_admin_callback, pattern=r"^helpadmin$"))
        self.application.add_handler(CallbackQueryHandler(self.answer_feed_callback, pattern=r"^answers:\d+:\d+$"))
        self.application.add_handler(CallbackQueryHandler(self.answer_reaction_callback, pattern=r"^react:\d+:(like|neutral|dislike)$"))
        self.application.add_handler(CallbackQueryHandler(self.closed_answer_callback, pattern=r"^pick:\d+:\d+$"))
        self.application.add_handler(CallbackQueryHandler(self.choice_answer_callback, pattern=r"^choice:\d+:\d+$"))
        self.application.add_handler(CallbackQueryHandler(self.action_done_callback, pattern=r"^actiondone:\d+:\d+$"))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_message))

    async def start(self) -> None:
        if self.application is None:
            logger.warning("Telegram bot token missing. Bot startup skipped.")
            return
        await self.application.initialize()
        await self.application.start()
        if self.application.updater is not None:
            await self.application.updater.start_polling(drop_pending_updates=False)
        logger.info("Telegram bot started")

    async def stop(self) -> None:
        if self.application is None:
            return
        if self.application.updater is not None:
            await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()
        logger.info("Telegram bot stopped")

    async def dispatch_next_prompt(self, *, force_new: bool = False, source: str = "scheduled") -> PromptDispatch:
        async with get_session() as session:
            question_service = QuestionService(session)
            dispatch = await question_service.create_or_get_daily_prompt(force_new=force_new, source=source)
            users = await UserService(session).list_users()

        if dispatch.created:
            await self._broadcast_prompt(dispatch.prompt_session, users)
        return dispatch

    async def _broadcast_prompt(self, prompt_session, users) -> None:
        if self.application is None:
            return

        is_action = prompt_session.question.category == QUESTION_CATEGORY_ACTION

        for user in users:
            try:
                if is_action:
                    text, reply_markup = await self._build_action_delivery(prompt_session, user)
                else:
                    text, reply_markup = await self._build_prompt_delivery(prompt_session, user.telegram_id)
                await self.application.bot.send_chat_action(chat_id=user.telegram_id, action=ChatAction.TYPING)
                prompt_message = await self.application.bot.send_message(
                    chat_id=user.telegram_id,
                    text=text,
                    reply_markup=reply_markup,
                )
                await self._set_user_prompt_message_id(user.telegram_id, prompt_session.id, prompt_message.message_id)
            except TelegramError as exc:
                logger.warning("Failed to send prompt to %s: %s", user.telegram_id, exc)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user is None or update.message is None:
            return

        telegram_user = update.effective_user
        async with get_session() as session:
            user_service = UserService(session)
            question_service = QuestionService(session)
            user, created = await user_service.register_user(
                telegram_id=telegram_user.id,
                username=telegram_user.username,
                display_name=telegram_user.full_name,
            )
            prompt = await question_service.get_current_prompt()

        if created:
            text = messages.welcome_message(user.display_name)
        else:
            text = messages.returning_user_message()

        if prompt is not None:
            text = f"{text}\n\ntonight's question is already live 🌙\njust reply with your answer."

        await self._reply_with_menu(update.message, telegram_user.id, text, delete_source=True)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user is None or update.message is None:
            return
        is_admin = await self._is_admin(update.effective_user.id)
        reply_markup = keyboards.help_admin_keyboard() if is_admin else None
        await self._reply_with_menu(
            update.message,
            update.effective_user.id,
            messages.help_message(),
            delete_source=True,
            reply_markup=reply_markup,
        )

    async def help_admin_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user is None or update.callback_query is None:
            return
        if not await self._is_admin(update.effective_user.id):
            await update.callback_query.answer(messages.admin_only_message(), show_alert=True)
            return
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            messages.help_admin_message(),
            reply_markup=InlineKeyboardMarkup([]),
        )

    async def streak_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user is None or update.message is None:
            return

        async with get_session() as session:
            user = await UserService(session).get_by_telegram_id(update.effective_user.id)

        if user is None:
            await self._reply_with_menu(
                update.message,
                update.effective_user.id,
                messages.welcome_message(update.effective_user.full_name),
                delete_source=True,
            )
            return

        await self._reply_with_menu(
            update.message,
            update.effective_user.id,
            messages.streak_message(user.streak),
            delete_source=True,
        )

    async def read_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user is None or update.message is None:
            return
        await self._send_answers_page(update.effective_user.id, update.message.reply_text)
        await self._delete_user_message(update.message)

    async def join_group_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user is None or update.message is None:
            return

        if not context.args:
            await self._reply_with_menu(
                update.message,
                update.effective_user.id,
                messages.join_group_prompt_message(),
                delete_source=True,
            )
            return

        await self._join_group(update, context.args[0])

    async def my_group_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user is None or update.message is None:
            return

        async with get_session() as session:
            user_service = UserService(session)
            group_service = GroupService(session)
            user = await user_service.get_by_telegram_id(update.effective_user.id)
            if user is None or user.group_id is None:
                await self._reply_with_menu(
                    update.message,
                    update.effective_user.id,
                    messages.group_required_message(),
                    delete_source=True,
                )
                return

            group = await group_service.get_group_by_id(user.group_id)
            member_count = await group_service.get_member_count(user.group_id)

        if group is None:
            await self._reply_with_menu(
                update.message,
                update.effective_user.id,
                messages.group_required_message(),
                delete_source=True,
            )
            return

        await self._reply_with_menu(
            update.message,
            update.effective_user.id,
            messages.my_group_message(group.name, member_count),
            delete_source=True,
        )

    async def leave_group_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user is None or update.message is None:
            return

        async with get_session() as session:
            user_service = UserService(session)
            user = await user_service.get_by_telegram_id(update.effective_user.id)
            if user is None or user.group_id is None:
                await self._reply_with_menu(
                    update.message,
                    update.effective_user.id,
                    messages.group_required_message(),
                    delete_source=True,
                )
                return
            await user_service.leave_group(user)

        await self._reply_with_menu(update.message, update.effective_user.id, messages.group_left_message(), delete_source=True)

    async def create_group_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user is None or update.message is None:
            return

        if not await self._is_admin(update.effective_user.id):
            await self._reply_with_menu(update.message, update.effective_user.id, messages.admin_only_message(), delete_source=True)
            return
        if not context.args:
            await self._reply_with_menu(
                update.message,
                update.effective_user.id,
                messages.create_group_prompt_message(),
                delete_source=True,
            )
            return

        await self._create_group(update, " ".join(context.args))

    async def add_member_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user is None or update.message is None:
            return

        if not await self._is_admin(update.effective_user.id):
            await self._reply_with_menu(update.message, update.effective_user.id, messages.admin_only_message(), delete_source=True)
            return
        if len(context.args) != 2:
            await self._reply_with_menu(
                update.message,
                update.effective_user.id,
                messages.add_member_prompt_message(),
                delete_source=True,
            )
            return

        await self._add_member(update, context.args[0], context.args[1])

    async def nickname_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user is None or update.message is None:
            return

        if not context.args:
            await self._reply_with_menu(
                update.message,
                update.effective_user.id,
                messages.nickname_prompt_message(),
                delete_source=True,
            )
            return

        nickname = " ".join(context.args).strip()
        if len(nickname) > 32:
            await self._reply_with_menu(
                update.message,
                update.effective_user.id,
                messages.nickname_too_long_message(),
                delete_source=True,
            )
            return

        async with get_session() as session:
            user_service = UserService(session)
            user = await user_service.get_by_telegram_id(update.effective_user.id)
            if user is None:
                user, _ = await user_service.register_user(
                    telegram_id=update.effective_user.id,
                    username=update.effective_user.username,
                    display_name=update.effective_user.full_name,
                )
            await user_service.set_nickname(user, nickname)

        await self._reply_with_menu(
            update.message,
            update.effective_user.id,
            messages.nickname_set_message(nickname),
            delete_source=True,
        )

    async def force_next_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user is None or update.message is None:
            return

        if not await self._is_admin(update.effective_user.id):
            await self._reply_with_menu(update.message, update.effective_user.id, messages.admin_only_message(), delete_source=True)
            return

        dispatch = await self.dispatch_next_prompt(force_new=True, source="manual")
        if self._should_suppress_admin_confirmation(update.effective_user.id):
            await self._delete_user_message(update.message)
            return

        await self._reply_with_menu(
            update.message,
            update.effective_user.id,
            messages.force_next_done_message(dispatch.prompt_session.question.text),
            delete_source=True,
        )

    async def reload_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user is None or update.message is None:
            return

        if not await self._is_admin(update.effective_user.id):
            await self._reply_with_menu(update.message, update.effective_user.id, messages.admin_only_message(), delete_source=True)
            return

        from pathlib import Path

        csv_path = Path(self.settings.resolved_questions_csv_path)
        if not csv_path.exists():
            await self._reply_with_menu(update.message, update.effective_user.id, "❌ questions CSV not found.", delete_source=True)
            return

        async with get_session() as session:
            count = await QuestionService(session).import_questions_from_csv(str(csv_path))

        await self._reply_with_menu(
            update.message,
            update.effective_user.id,
            f"✓ reloaded <b>{count}</b> questions from CSV.",
            delete_source=True,
        )

    async def question_time_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user is None or update.message is None:
            return

        if not await self._is_admin(update.effective_user.id):
            await self._reply_with_menu(update.message, update.effective_user.id, messages.admin_only_message(), delete_source=True)
            return

        current_time = self._format_time(self.settings.daily_question_hour, self.settings.daily_question_minute)
        if not context.args:
            await self._reply_with_menu(
                update.message,
                update.effective_user.id,
                messages.question_time_usage_message(current_time, self.settings.timezone),
                delete_source=True,
            )
            return

        scheduled_time = self._parse_question_time(context.args[0])
        if scheduled_time is None:
            await self._reply_with_menu(
                update.message,
                update.effective_user.id,
                messages.question_time_invalid_message(),
                delete_source=True,
            )
            return

        hour, minute = scheduled_time
        async with get_session() as session:
            await AppSettingsService(session).set_daily_question_time(hour=hour, minute=minute)

        self.settings.daily_question_hour = hour
        self.settings.daily_question_minute = minute
        if self.scheduler is not None:
            self.scheduler.set_daily_time(hour=hour, minute=minute)

        await self._reply_with_menu(
            update.message,
            update.effective_user.id,
            messages.question_time_set_message(self._format_time(hour, minute), self.settings.timezone),
            delete_source=True,
        )

    async def text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user is None or update.message is None or not update.message.text:
            return

        async with get_session() as session:
            user_service = UserService(session)
            question_service = QuestionService(session)
            answer_service = AnswerService(session)
            user, _ = await user_service.register_user(
                telegram_id=update.effective_user.id,
                username=update.effective_user.username,
                display_name=update.effective_user.full_name,
            )
            prompt = await question_service.get_current_prompt()
            if prompt is None:
                await self._reply_with_menu(
                    update.message,
                    update.effective_user.id,
                    messages.no_prompt_message(),
                    delete_source=True,
                )
                return
            if prompt.question.category == QUESTION_CATEGORY_CLOSED:
                await self._reply_with_menu(
                    update.message,
                    update.effective_user.id,
                    messages.closed_question_text_input_message(),
                    delete_source=True,
                )
                return
            if prompt.question.category in CHOICE_QUESTION_OPTIONS:
                await self._reply_with_menu(
                    update.message,
                    update.effective_user.id,
                    messages.choice_question_text_input_message(),
                    delete_source=True,
                )
                return
            if prompt.question.category == QUESTION_CATEGORY_ACTION:
                await self._reply_with_menu(
                    update.message,
                    update.effective_user.id,
                    messages.action_no_assignment_message(),
                    delete_source=True,
                )
                return

            answer, created = await answer_service.save_answer(user, prompt, update.message.text)
            user = await user_service.update_streak(user, date.today())
            answer_count = None
            if user.group_id is not None:
                answer_count = await answer_service.count_group_answers(prompt.id, user.group_id)

        countdown_message = await update.message.reply_text(messages.open_answer_cleanup_message(5))
        await self._set_answer_status_message_id(answer.id, None)
        await self._run_open_answer_cleanup(
            user=user,
            prompt_session_id=prompt.id,
            answer_message=update.message,
            countdown_message=countdown_message,
        )
        if created and user.group_id is not None:
            await self._refresh_group_answer_status_messages(
                prompt.id,
                user.group_id,
                exclude_answer_id=answer.id,
            )

    async def closed_answer_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user is None or update.callback_query is None:
            return

        _, prompt_session_id_text, picked_user_id_text = update.callback_query.data.split(":")
        prompt_session_id = int(prompt_session_id_text)
        picked_user_id = int(picked_user_id_text)

        async with get_session() as session:
            user_service = UserService(session)
            question_service = QuestionService(session)
            answer_service = AnswerService(session)
            group_service = GroupService(session)

            user, _ = await user_service.register_user(
                telegram_id=update.effective_user.id,
                username=update.effective_user.username,
                display_name=update.effective_user.full_name,
            )
            if user.group_id is None:
                await update.callback_query.answer(messages.closed_question_group_required_message(), show_alert=True)
                return

            prompt = await question_service.get_prompt_by_id(prompt_session_id)
            if prompt is None:
                await update.callback_query.answer(messages.no_prompt_message(), show_alert=True)
                return
            if prompt.question.category != QUESTION_CATEGORY_CLOSED:
                await update.callback_query.answer(messages.closed_question_text_input_message(), show_alert=True)
                return

            members = await group_service.list_group_members(user.group_id)
            member_map = {member.id: member for member in members}
            picked_user = member_map.get(picked_user_id)
            if picked_user is None:
                await update.callback_query.answer("that pick expired 💨", show_alert=True)
                return

            chosen_name = messages.closed_question_member_label(
                picked_user.nickname,
                picked_user.display_name,
                picked_user.username,
                picked_user.telegram_id,
            )
            answer, created = await answer_service.save_answer(user, prompt, chosen_name)
            user = await user_service.update_streak(user, date.today())
            answer_count = await answer_service.count_group_answers(prompt.id, user.group_id)

        await update.callback_query.answer("✓ saved")
        await update.callback_query.edit_message_text(
            messages.closed_answer_saved_message(
                chosen_name=chosen_name,
                streak=user.streak,
                answer_count=answer_count,
                updated=not created,
            ),
            reply_markup=keyboards.answer_saved_keyboard(prompt.id),
        )
        if update.callback_query.message is not None:
            await self._set_answer_status_message_id(answer.id, update.callback_query.message.message_id)
        if created:
            await self._refresh_group_answer_status_messages(
                prompt.id,
                user.group_id,
                exclude_answer_id=answer.id,
            )

    async def choice_answer_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user is None or update.callback_query is None:
            return

        _, prompt_session_id_text, option_index_text = update.callback_query.data.split(":")
        prompt_session_id = int(prompt_session_id_text)
        option_index = int(option_index_text)

        async with get_session() as session:
            user_service = UserService(session)
            question_service = QuestionService(session)
            answer_service = AnswerService(session)

            user, _ = await user_service.register_user(
                telegram_id=update.effective_user.id,
                username=update.effective_user.username,
                display_name=update.effective_user.full_name,
            )
            prompt = await question_service.get_prompt_by_id(prompt_session_id)
            if prompt is None:
                await update.callback_query.answer(messages.no_prompt_message(), show_alert=True)
                return

            options = CHOICE_QUESTION_OPTIONS.get(prompt.question.category)
            if options is None:
                await update.callback_query.answer(messages.choice_question_text_input_message(), show_alert=True)
                return
            if option_index < 0 or option_index >= len(options):
                await update.callback_query.answer("that choice expired 💨", show_alert=True)
                return

            choice_label = options[option_index]
            answer, created = await answer_service.save_answer(user, prompt, choice_label)
            user = await user_service.update_streak(user, date.today())
            answer_count = None
            if user.group_id is not None:
                answer_count = await answer_service.count_group_answers(prompt.id, user.group_id)

        await update.callback_query.answer("✓ saved")
        await update.callback_query.edit_message_text(
            messages.choice_answer_saved_message(
                choice_label=choice_label,
                streak=user.streak,
                answer_count=answer_count,
                updated=not created,
            ),
            reply_markup=keyboards.answer_saved_keyboard(prompt.id),
        )
        if update.callback_query.message is not None:
            await self._set_answer_status_message_id(answer.id, update.callback_query.message.message_id)
        if created and user.group_id is not None:
            await self._refresh_group_answer_status_messages(
                prompt.id,
                user.group_id,
                exclude_answer_id=answer.id,
            )

    async def action_done_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user is None or update.callback_query is None:
            return

        _, prompt_session_id_text, assignment_id_text = update.callback_query.data.split(":")
        prompt_session_id = int(prompt_session_id_text)
        assignment_id = int(assignment_id_text)

        async with get_session() as session:
            user_service = UserService(session)
            action_service = ActionService(session)
            question_service = QuestionService(session)
            answer_service = AnswerService(session)

            user, _ = await user_service.register_user(
                telegram_id=update.effective_user.id,
                username=update.effective_user.username,
                display_name=update.effective_user.full_name,
            )

            assignment = await action_service.get_user_assignment(user.id, prompt_session_id)
            if assignment is None or assignment.id != assignment_id:
                await update.callback_query.answer(messages.action_no_assignment_message(), show_alert=True)
                return

            if assignment.completed:
                await update.callback_query.answer(messages.action_already_completed_message(), show_alert=True)
                return

            prompt = await question_service.get_prompt_by_id(prompt_session_id)
            if prompt is None:
                await update.callback_query.answer(messages.no_prompt_message(), show_alert=True)
                return

            await action_service.mark_completed(assignment_id)
            answer, _ = await answer_service.save_answer(user, prompt, assignment.question.text)
            user = await user_service.update_streak(user, date.today())

        await update.callback_query.answer("✅ done!")
        await update.callback_query.edit_message_text(
            messages.action_completed_message(assignment.question.text, user.streak),
            reply_markup=keyboards.action_completed_keyboard(prompt_session_id),
        )
        if update.callback_query.message is not None:
            await self._set_answer_status_message_id(answer.id, update.callback_query.message.message_id)
        if user.group_id is not None:
            await self._refresh_group_answer_status_messages(
                prompt_session_id,
                user.group_id,
                exclude_answer_id=answer.id,
            )

    async def answer_feed_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user is None or update.callback_query is None:
            return

        _, prompt_session_id_text, _ = update.callback_query.data.split(":")
        prompt_session_id = int(prompt_session_id_text)
        await update.callback_query.answer()
        await self._send_answers_page(
            update.effective_user.id,
            update.callback_query.edit_message_text,
            prompt_session_id=prompt_session_id,
        )

    async def answer_reaction_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user is None or update.callback_query is None:
            return

        _, prompt_session_id_text, rating = update.callback_query.data.split(":")
        prompt_session_id = int(prompt_session_id_text)

        async with get_session() as session:
            user_service = UserService(session)
            answer_service = AnswerService(session)
            user = await user_service.get_by_telegram_id(update.effective_user.id)
            if user is None:
                await update.callback_query.answer(messages.no_prompt_message(), show_alert=True)
                return

            answer = await answer_service.get_user_answer(user.id, prompt_session_id)
            if answer is None:
                await update.callback_query.answer("answer first, then react ✍️", show_alert=True)
                return

            answer = await answer_service.set_answer_rating(answer, rating)

        rating_message = {
            ANSWER_RATING_LIKE: "saved: like",
            ANSWER_RATING_NEUTRAL: "saved: neutral",
            ANSWER_RATING_DISLIKE: "saved: dislike",
        }[rating]
        await update.callback_query.answer(rating_message)
        await update.callback_query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup([]),
        )

    async def _send_answers_page(
        self,
        telegram_id: int,
        responder,
        *,
        prompt_session_id: int | None = None,
    ) -> None:
        async with get_session() as session:
            user_service = UserService(session)
            question_service = QuestionService(session)
            answer_service = AnswerService(session)
            action_service = ActionService(session)
            user = await user_service.get_by_telegram_id(telegram_id)
            if user is None or user.group_id is None:
                await responder(messages.group_required_message())
                return

            prompt = await (
                question_service.get_prompt_by_id(prompt_session_id)
                if prompt_session_id is not None
                else question_service.get_current_prompt()
            )
            if prompt is None:
                await responder(messages.no_prompt_message())
                return

            user_answer = await answer_service.get_user_answer(user.id, prompt.id)
            user_rating = user_answer.rating if user_answer is not None else None
            feed_keyboard = keyboards.answer_feed_keyboard(
                prompt.id,
                rating=user_rating,
            )

            if prompt.question.category == QUESTION_CATEGORY_ACTION:
                completed_actions = await action_service.list_completed_group_actions(prompt.id, user.group_id)
                await self._send_action_answers_page(
                    user,
                    prompt,
                    completed_actions,
                    responder,
                    reply_markup=feed_keyboard,
                )
                return

            all_answers = await answer_service.list_group_answers_with_users(prompt.id, user.group_id)

        total = len(all_answers)
        if total == 0:
            await responder(messages.no_group_answers_message(), reply_markup=feed_keyboard)
            return

        answer_lines: list[str] = []
        for answer in all_answers:
            user_label = messages.closed_question_member_label(
                answer.user.nickname if answer.user else None,
                answer.user.display_name if answer.user else None,
                answer.user.username if answer.user else None,
                answer.user.telegram_id if answer.user else 0,
            )
            if prompt.question.category in BUTTON_QUESTION_CATEGORIES:
                answer_lines.append(messages.closed_answer_feed_entry(user_label, answer.text))
            else:
                answer_lines.append(messages.answer_feed_entry(user_label, answer.text))

        await responder(
            messages.read_answers_message(
                prompt.question.text,
                prompt.question.category,
                answer_lines,
            ),
            reply_markup=feed_keyboard,
        )

    async def _build_prompt_delivery(self, prompt_session, telegram_id: int) -> tuple[str, object | None]:
        category = prompt_session.question.category
        if category == QUESTION_CATEGORY_CLOSED:
            async with get_session() as session:
                user = await UserService(session).get_by_telegram_id(telegram_id)
                if user is None or user.group_id is None:
                    text = (
                        messages.daily_question_message(prompt_session.question.text, category)
                        + "\n\n"
                        + messages.closed_question_group_required_message()
                    )
                    return text, keyboards.prompt_actions_keyboard(prompt_session.id, can_answer_with_buttons=False)

                members = await GroupService(session).list_group_members(user.group_id)

            if not members:
                text = (
                    messages.daily_question_message(prompt_session.question.text, category)
                    + "\n\n"
                    + messages.closed_question_no_members_message()
                )
                return text, keyboards.prompt_actions_keyboard(prompt_session.id, can_answer_with_buttons=False)

            member_buttons = [
                (
                    member.id,
                    messages.closed_question_member_label(member.nickname, member.display_name, member.username, member.telegram_id),
                )
                for member in members
            ]
            text = messages.daily_question_message(prompt_session.question.text, category)
            return text, keyboards.closed_question_keyboard(prompt_session.id, member_buttons)

        choice_options = CHOICE_QUESTION_OPTIONS.get(category)
        if choice_options is not None:
            text = messages.daily_question_message(prompt_session.question.text, category)
            return text, keyboards.choice_question_keyboard(prompt_session.id, choice_options, columns=3)

        text = messages.daily_question_message(prompt_session.question.text, category)
        return text, keyboards.prompt_actions_keyboard(prompt_session.id, can_answer_with_buttons=False)

    async def _build_action_delivery(self, prompt_session, user) -> tuple[str, object | None]:
        async with get_session() as session:
            action_service = ActionService(session)
            db_user = await UserService(session).get_by_telegram_id(user.telegram_id)
            if db_user is None:
                text = messages.daily_question_message(prompt_session.question.text, QUESTION_CATEGORY_ACTION)
                return text, keyboards.prompt_actions_keyboard(prompt_session.id, can_answer_with_buttons=False)

            assignment = await action_service.assign_action_to_user(db_user, prompt_session)
            if assignment is None:
                text = messages.daily_question_message(prompt_session.question.text, QUESTION_CATEGORY_ACTION)
                return text, keyboards.prompt_actions_keyboard(prompt_session.id, can_answer_with_buttons=False)

            # Reload to get question relationship
            assignment = await action_service.get_user_assignment(db_user.id, prompt_session.id)
            if assignment is None:
                text = messages.daily_question_message(prompt_session.question.text, QUESTION_CATEGORY_ACTION)
                return text, keyboards.prompt_actions_keyboard(prompt_session.id, can_answer_with_buttons=False)

        text = messages.action_prompt_message(assignment.question.text)
        return text, keyboards.action_done_keyboard(prompt_session.id, assignment.id)

    async def _send_action_answers_page(
        self,
        user,
        prompt,
        completed_actions,
        responder,
        *,
        reply_markup,
    ) -> None:
        total = len(completed_actions)
        if total == 0:
            await responder(messages.no_completed_actions_message(), reply_markup=reply_markup)
            return

        answer_lines: list[str] = []
        for action in completed_actions:
            user_label = messages.closed_question_member_label(
                action.user.nickname if action.user else None,
                action.user.display_name if action.user else None,
                action.user.username if action.user else None,
                action.user.telegram_id if action.user else 0,
            )
            answer_lines.append(messages.action_feed_entry(action.question.text, user_label, is_current_user=False))

        await responder(
            messages.read_answers_message(
                prompt.question.text,
                prompt.question.category,
                answer_lines,
            ),
            reply_markup=reply_markup,
        )

    async def _is_admin(self, telegram_id: int) -> bool:
        return self.settings.admin_telegram_id is not None and telegram_id == self.settings.admin_telegram_id

    def _should_suppress_admin_confirmation(self, telegram_id: int) -> bool:
        return self.settings.admin_telegram_id is not None and telegram_id == self.settings.admin_telegram_id

    @staticmethod
    def _parse_question_time(raw_value: str) -> tuple[int, int] | None:
        time_text = raw_value.strip()
        if not time_text:
            return None

        if ":" not in time_text:
            try:
                hour = int(time_text)
            except ValueError:
                return None
            return (hour, 0) if 0 <= hour <= 23 else None

        hour_text, minute_text = time_text.split(":", maxsplit=1)
        try:
            hour = int(hour_text)
            minute = int(minute_text)
        except ValueError:
            return None
        if not 0 <= hour <= 23 or not 0 <= minute <= 59:
            return None
        return hour, minute

    @staticmethod
    def _format_time(hour: int, minute: int) -> str:
        return f"{hour:02d}:{minute:02d}"

    async def _run_open_answer_cleanup(self, *, user, prompt_session_id: int, answer_message, countdown_message) -> None:
        for seconds_remaining in range(4, 0, -1):
            await asyncio.sleep(1)
            try:
                await countdown_message.edit_text(messages.open_answer_cleanup_message(seconds_remaining))
            except TelegramError as exc:
                logger.debug("Failed to update open-answer countdown for %s: %s", user.telegram_id, exc)

        await asyncio.sleep(1)
        await self._delete_bot_message(countdown_message)
        await self._delete_user_message(answer_message)
        await self._show_read_answers_on_prompt(user.telegram_id, prompt_session_id)

    async def _join_group(self, update: Update, invite_code: str) -> None:
        if update.effective_user is None or update.message is None:
            return

        async with get_session() as session:
            user_service = UserService(session)
            group_service = GroupService(session)
            user = await user_service.get_by_telegram_id(update.effective_user.id)
            if user is None:
                user, _ = await user_service.register_user(
                    telegram_id=update.effective_user.id,
                    username=update.effective_user.username,
                    display_name=update.effective_user.full_name,
                )

            group = await group_service.get_group_by_code(invite_code.upper())
            if group is None:
                await self._reply_with_menu(
                    update.message,
                    update.effective_user.id,
                    messages.invalid_group_code_message(),
                    delete_source=True,
                )
                return
            await user_service.join_group(user, group.id)

        await self._reply_with_menu(update.message, update.effective_user.id, messages.group_joined_message(group.name), delete_source=True)

    async def _create_group(self, update: Update, group_name: str) -> None:
        if update.effective_user is None or update.message is None:
            return

        if not await self._is_admin(update.effective_user.id):
            await self._reply_with_menu(update.message, update.effective_user.id, messages.admin_only_message(), delete_source=True)
            return

        group_name = group_name.strip()
        if not group_name:
            await self._reply_with_menu(
                update.message,
                update.effective_user.id,
                messages.create_group_prompt_message(),
                delete_source=True,
            )
            return

        async with get_session() as session:
            group = await GroupService(session).create_group(group_name, update.effective_user.id)

        await self._reply_with_menu(
            update.message,
            update.effective_user.id,
            messages.group_created_message(group.name, group.invite_code),
            delete_source=True,
        )

    async def _add_member(self, update: Update, telegram_id_text: str, invite_code: str) -> None:
        if update.effective_user is None or update.message is None:
            return

        if not await self._is_admin(update.effective_user.id):
            await self._reply_with_menu(update.message, update.effective_user.id, messages.admin_only_message(), delete_source=True)
            return

        try:
            telegram_id = int(telegram_id_text)
        except ValueError:
            await self._reply_with_menu(
                update.message,
                update.effective_user.id,
                messages.add_member_prompt_message(),
                delete_source=True,
            )
            return

        async with get_session() as session:
            group_service = GroupService(session)
            group = await group_service.get_group_by_code(invite_code.upper())
            if group is None:
                await self._reply_with_menu(
                    update.message,
                    update.effective_user.id,
                    messages.invalid_group_code_message(),
                    delete_source=True,
                )
                return
            user = await group_service.add_member_by_telegram_id(telegram_id, group)
            if user is None:
                await self._reply_with_menu(
                    update.message,
                    update.effective_user.id,
                    "that user hasn't started the bot yet 💨",
                    delete_source=True,
                )
                return

        await self._reply_with_menu(
            update.message,
            update.effective_user.id,
            messages.member_added_message(telegram_id, group.name),
            delete_source=True,
        )

    async def _reply_with_menu(self, message, telegram_id: int, text: str, *, delete_source: bool = False, reply_markup=None):
        response = await message.reply_text(text, reply_markup=reply_markup)
        if delete_source:
            await self._delete_user_message(message)
        return response

    async def _delete_bot_message(self, message) -> None:
        try:
            await message.delete()
        except TelegramError as exc:
            logger.debug("Failed to delete bot message %s in chat %s: %s", message.message_id, message.chat_id, exc)

    async def _delete_user_message(self, message) -> None:
        try:
            await message.delete()
        except TelegramError as exc:
            logger.debug("Failed to delete user message %s in chat %s: %s", message.message_id, message.chat_id, exc)

    async def _set_user_prompt_message_id(self, telegram_id: int, prompt_session_id: int, message_id: int) -> None:
        async with get_session() as session:
            user_service = UserService(session)
            user = await user_service.get_by_telegram_id(telegram_id)
            if user is None:
                return
            await user_service.set_last_prompt_message(user, prompt_session_id, message_id)

    async def _show_read_answers_on_prompt(self, telegram_id: int, prompt_session_id: int) -> None:
        if self.application is None:
            return

        async with get_session() as session:
            user_service = UserService(session)
            answer_service = AnswerService(session)
            user = await user_service.get_by_telegram_id(telegram_id)
            if user is None:
                return
            if user.last_prompt_session_id != prompt_session_id or user.last_prompt_message_id is None:
                return
            answer = await answer_service.get_user_answer(user.id, prompt_session_id)

        try:
            await self.application.bot.edit_message_reply_markup(
                chat_id=telegram_id,
                message_id=user.last_prompt_message_id,
                reply_markup=keyboards.answer_saved_keyboard(prompt_session_id),
            )
        except TelegramError as exc:
            logger.debug("Failed to add read-answers button to prompt for %s: %s", telegram_id, exc)

    async def _set_answer_status_message_id(self, answer_id: int, message_id: int | None) -> None:
        async with get_session() as session:
            await AnswerService(session).set_status_message_id(answer_id, message_id)

    async def _refresh_group_answer_status_messages(
        self,
        prompt_session_id: int,
        group_id: int,
        *,
        exclude_answer_id: int | None = None,
    ) -> None:
        if self.application is None:
            return

        async with get_session() as session:
            question_service = QuestionService(session)
            answer_service = AnswerService(session)
            prompt = await question_service.get_prompt_by_id(prompt_session_id)
            if prompt is None:
                return
            answers = await answer_service.list_group_answers_with_users(prompt_session_id, group_id)

        answer_count = len(answers)
        for answer in answers:
            if answer.id == exclude_answer_id or answer.status_message_id is None:
                continue
            if answer.user is None:
                continue

            if prompt.question.category == QUESTION_CATEGORY_CLOSED:
                message_text = messages.closed_answer_saved_message(
                    chosen_name=answer.text,
                    streak=answer.user.streak,
                    answer_count=answer_count,
                    updated=answer.updated_at > answer.created_at,
                )
            elif prompt.question.category in CHOICE_QUESTION_OPTIONS:
                message_text = messages.choice_answer_saved_message(
                    choice_label=answer.text,
                    streak=answer.user.streak,
                    answer_count=answer_count,
                    updated=answer.updated_at > answer.created_at,
                )
            elif prompt.question.category == QUESTION_CATEGORY_ACTION:
                message_text = messages.action_completed_message(answer.text, answer.user.streak)
            else:
                message_text = messages.answer_saved_message(
                    streak=answer.user.streak,
                    answer_count=answer_count,
                    updated=answer.updated_at > answer.created_at,
                    has_group=True,
                )

            reply_markup = (
                keyboards.action_completed_keyboard(prompt_session_id)
                if prompt.question.category == QUESTION_CATEGORY_ACTION
                else keyboards.answer_saved_keyboard(prompt_session_id)
            )

            try:
                await self.application.bot.edit_message_text(
                    chat_id=answer.user.telegram_id,
                    message_id=answer.status_message_id,
                    text=message_text,
                    reply_markup=reply_markup,
                )
            except TelegramError as exc:
                logger.debug("Failed to refresh answer status message for %s: %s", answer.user.telegram_id, exc)
