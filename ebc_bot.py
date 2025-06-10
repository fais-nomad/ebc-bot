print("🔧 Bot script loaded...")

import os
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters, PicklePersistence
)

# States
SELECT_ACTION, SELECT_SERVICES, ASK_PEOPLE, ASK_PROFIT, UPDATE_CHOICE, UPDATE_INPUT = range(6)

PRICES = {
    "pickup": 5000,
    "flight": 25000,
    "guide": 3000,
    "porter": 1800,
    "permit": 3500,
    "food": 3500,
    "ramechhap": 2500,
    "kathmandu_room": 6600,
    "persons_per_car": 14,
    "trek_days": 12,
}

EXCHANGE_RATE = 1.6
ALL_SERVICES = ["pickup", "flight", "guide", "porter", "permit", "food", "ramechhap", "kathmandu_room"]

# Telegram bot handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("DEBUG: /start triggered")
    keyboard = [
        [InlineKeyboardButton("🧮 Start Calculation", callback_data="start_calc")],
        [InlineKeyboardButton("🛠 Update Cost of Service", callback_data="update_costs")],
    ]
    await update.message.reply_text("Welcome! What do you want to do?", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_ACTION

async def handle_start_option(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "start_calc":
        context.user_data["selected_services"] = []
        return await show_service_selection(update, context)
    elif query.data == "update_costs":
        buttons = [[InlineKeyboardButton(f"{s.replace('_', ' ').capitalize()} (₹{PRICES[s]})", callback_data=s)] for s in ALL_SERVICES]
        await query.message.reply_text("Select a service to update:", reply_markup=InlineKeyboardMarkup(buttons))
        return UPDATE_CHOICE

async def update_cost_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["update_target"] = query.data
    await query.message.reply_text(f"Enter new cost for {query.data.replace('_', ' ')} (in NPR):")
    return UPDATE_INPUT

async def apply_cost_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_price = int(update.message.text)
        target = context.user_data["update_target"]
        PRICES[target] = new_price
        await update.message.reply_text(f"✅ Updated {target.replace('_', ' ')} cost to ₹{new_price} NPR.")
    except:
        await update.message.reply_text("❌ Invalid input. Try again.")
    return ConversationHandler.END

async def show_service_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected = set(context.user_data.get("selected_services", []))
    buttons = [[
        InlineKeyboardButton(f"{'✅' if s in selected else '☐'} {s.replace('_', ' ').capitalize()}", callback_data=f"toggle_{s}")
    ] for s in ALL_SERVICES]
    buttons.append([
        InlineKeyboardButton("✅ Select All", callback_data="select_all"),
        InlineKeyboardButton("❌ Deselect All", callback_data="deselect_all"),
    ])
    buttons.append([InlineKeyboardButton("➡️ Proceed", callback_data="proceed")])
    markup = InlineKeyboardMarkup(buttons)

    if update.callback_query:
        await update.callback_query.edit_message_text("🛠 Select services:", reply_markup=markup)
    else:
        await update.message.reply_text("🛠 Select services:", reply_markup=markup)
    return SELECT_SERVICES

# Other handlers remain unchanged...

# Don't forget to include the new services in all necessary logic like calculation, summary, and update handlers.