#!/usr/bin/env python3
"""
Telegram Bot using python-telegram-bot library
"""

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text("Hello! I'm a bot. How can I help you?")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = """
    Available commands:
    /start - Start the bot
    /help - Show this help message
    """
    await update.message.reply_text(help_text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regular messages."""
    await update.message.reply_text(f"You said: {update.message.text}")


def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token("YOUR_BOT_TOKEN_HERE").build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()
