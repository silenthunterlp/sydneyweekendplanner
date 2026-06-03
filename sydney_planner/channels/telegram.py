import logging

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from sydney_planner.agent.core import PlannerAgent
from sydney_planner.utils.formatting import markdown_to_telegram

logger = logging.getLogger(__name__)

# Quick-reply keyboard shown after onboarding completes
PLAN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["📅 Plan my weekend", "🌤 What's the weather?"],
        ["🎵 Live music", "🥗 Food & markets"],
        ["🏖️ Beaches & outdoors", "⚙️ Update my preferences"],
    ],
    resize_keyboard=True,
    one_time_keyboard=False,
)


def build_telegram_app(token: str, agent: PlannerAgent):
    async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start — reset onboarding or greet returning user."""
        if not update.effective_user or not update.message:
            return
        user_id = f"telegram:{update.effective_user.id}"
        first_name = update.effective_user.first_name or "there"
        reply = await agent.chat(
            user_id,
            f"Hi! I'm {first_name}. Please introduce yourself and help me plan a great Sydney weekend.",
            "telegram",
        )
        safe_reply = markdown_to_telegram(reply)
        await update.message.reply_text(safe_reply, parse_mode="HTML", reply_markup=PLAN_KEYBOARD)

    async def cmd_plan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /plan — immediately request a weekend plan."""
        if not update.effective_user or not update.message:
            return
        user_id = f"telegram:{update.effective_user.id}"
        reply = await agent.chat(user_id, "Plan my weekend please!", "telegram")
        safe_reply = markdown_to_telegram(reply)
        await update.message.reply_text(safe_reply, parse_mode="HTML", reply_markup=PLAN_KEYBOARD)

    async def cmd_prefs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /prefs — show and update preferences."""
        if not update.effective_user or not update.message:
            return
        user_id = f"telegram:{update.effective_user.id}"
        reply = await agent.chat(user_id, "Show me my current preferences and let me update them.", "telegram")
        safe_reply = markdown_to_telegram(reply)
        await update.message.reply_text(safe_reply, parse_mode="HTML")

    async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /reset — restart onboarding."""
        if not update.effective_user or not update.message:
            return
        user_id = f"telegram:{update.effective_user.id}"
        reply = await agent.chat(
            user_id,
            "Please reset my preferences and start fresh with onboarding.",
            "telegram",
        )
        safe_reply = markdown_to_telegram(reply)
        await update.message.reply_text(safe_reply, parse_mode="HTML")

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle all plain text messages."""
        if not update.effective_user or not update.message or not update.message.text:
            return
        user_id = f"telegram:{update.effective_user.id}"
        text = update.message.text.strip()

        # Show typing indicator
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action="typing"
        )

        reply = await agent.chat(user_id, text, "telegram")
        safe_reply = markdown_to_telegram(reply)
        await update.message.reply_text(safe_reply, parse_mode="HTML", reply_markup=PLAN_KEYBOARD)

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("plan", cmd_plan))
    app.add_handler(CommandHandler("prefs", cmd_prefs))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Telegram bot configured with commands: /start /plan /prefs /reset")
    return app
