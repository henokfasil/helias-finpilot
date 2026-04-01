"""
Bot entry point — assembles the Application, registers handlers, and starts polling.
"""
from __future__ import annotations

import logging
import time

from telegram import BotCommand
from telegram.error import Conflict
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
        BotCommand("income_statement", "Profit & Loss statement"),
        BotCommand("balance_sheet", "Assets, Liabilities & Equity"),
        BotCommand("cashflow", "Cash Flow statement"),
        BotCommand("tag", "Tag transaction as investing/financing"),
        BotCommand("add_asset", "Add asset to Balance Sheet"),
        BotCommand("add_liability", "Add liability to Balance Sheet"),
        BotCommand("add_equity", "Add equity entry to Balance Sheet"),
        BotCommand("bs_entries", "List Balance Sheet manual entries"),
        BotCommand("remove_entry", "Remove a Balance Sheet entry"),
        BotCommand("loan", "Record a loan received (cash + liability)"),
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
    app.add_handler(CommandHandler("income_statement", commands.cmd_income_statement))
    app.add_handler(CommandHandler("balance_sheet", commands.cmd_balance_sheet))
    app.add_handler(CommandHandler("cashflow", commands.cmd_cashflow))
    app.add_handler(CommandHandler("tag", commands.cmd_tag))
    app.add_handler(CommandHandler("add_asset", commands.cmd_add_asset))
    app.add_handler(CommandHandler("add_liability", commands.cmd_add_liability))
    app.add_handler(CommandHandler("add_equity", commands.cmd_add_equity))
    app.add_handler(CommandHandler("bs_entries", commands.cmd_bs_entries))
    app.add_handler(CommandHandler("remove_entry", commands.cmd_remove_entry))
    app.add_handler(CommandHandler("loan", commands.cmd_loan))

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
    app.run_polling(drop_pending_updates=True, timeout=10)
    # On Conflict, the process exits and systemd restarts after 30s —
    # enough time for Telegram to clear the previous session.
