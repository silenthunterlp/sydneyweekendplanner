from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

from sydney_planner.agent.core import PlannerAgent
from sydney_planner.utils.formatting import markdown_to_telegram


def build_telegram_app(token: str, agent: PlannerAgent):
    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_user or not update.message or not update.message.text:
            return
        user_id = f"telegram:{update.effective_user.id}"
        text = update.message.text.strip()
        reply = await agent.chat(user_id, text, "telegram")
        safe_reply = markdown_to_telegram(reply)
        await update.message.reply_text(safe_reply, parse_mode="HTML")

    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app
