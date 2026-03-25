"""
Bot entry point — assembles the Application, registers handlers, and starts polling.
"""
from __future__ import annotations

import logging

from telegram import BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from app.bot import commands, handlers
from app.config import settings

logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Set bot command menu in Telegram UI."""
    await application.bot.set_my_commands([
        BotCommand("start", "Register / get started"),
        BotCommand("help", "Show all commands"),
        BotCommand("transactions", "List recent transactions"),
        BotCommand("pending", "Show unconfirmed items"),
        BotCommand("summary", "Quick financial snapshot"),
        BotCommand("monthly_report", "Generate monthly report"),
        BotCommand("annual_report", "Generate annual report"),
        BotCommand("search", "Search transactions"),
        BotCommand("export", "Export as CSV"),
        BotCommand("tax_summary", "VAT & withholding tax obligations"),
        BotCommand("delete", "Delete a transaction by ID"),
        BotCommand("receipts", "List stored receipts by period"),
        BotCommand("export_receipts", "Download all receipts as ZIP"),
    ])


def build_application() -> Application:
    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .post_init(post_init)
        .build()
    )

    # Command handlers
    app.add_handler(CommandHandler("start", commands.cmd_start))
    app.add_handler(CommandHandler("help", commands.cmd_help))
    app.add_handler(CommandHandler("transactions", commands.cmd_transactions))
    app.add_handler(CommandHandler("pending", commands.cmd_pending))
    app.add_handler(CommandHandler("summary", commands.cmd_summary))
    app.add_handler(CommandHandler("monthly_report", commands.cmd_monthly_report))
    app.add_handler(CommandHandler("report", commands.cmd_monthly_report))
    app.add_handler(CommandHandler("annual_report", commands.cmd_annual_report))
    app.add_handler(CommandHandler("search", commands.cmd_search))
    app.add_handler(CommandHandler("export", commands.cmd_export))
    app.add_handler(CommandHandler("tax_summary", commands.cmd_tax_summary))
    app.add_handler(CommandHandler("delete", commands.cmd_delete))
    app.add_handler(CommandHandler("receipts", commands.cmd_receipts))
    app.add_handler(CommandHandler("export_receipts", commands.cmd_export_receipts))

    # Message handlers
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message)
    )
    app.add_handler(
        MessageHandler(filters.Document.ALL | filters.PHOTO, handlers.handle_document)
    )

    return app


def run() -> None:
    logger.info("Starting Helias FinPilot bot…")
    app = build_application()
    app.run_polling(drop_pending_updates=True)
