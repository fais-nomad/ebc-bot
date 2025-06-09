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
    "persons_per_car": 14,
    "trek_days": 12,
}

EXCHANGE_RATE = 1.6
ALL_SERVICES = ["pickup", "flight", "guide", "porter", "permit", "food"]

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
        buttons = [[InlineKeyboardButton(f"{s.capitalize()} (₹{PRICES[s]})", callback_data=s)] for s in ALL_SERVICES]
        await query.message.reply_text("Select a service to update:", reply_markup=InlineKeyboardMarkup(buttons))
        return UPDATE_CHOICE

async def update_cost_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["update_target"] = query.data
    await query.message.reply_text(f"Enter new cost for {query.data} (in NPR):")
    return UPDATE_INPUT

async def apply_cost_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_price = int(update.message.text)
        target = context.user_data["update_target"]
        PRICES[target] = new_price
        await update.message.reply_text(f"✅ Updated {target} cost to ₹{new_price} NPR.")
    except:
        await update.message.reply_text("❌ Invalid input. Try again.")
    return ConversationHandler.END

async def show_service_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected = set(context.user_data.get("selected_services", []))
    buttons = [[
        InlineKeyboardButton(f"{'✅' if s in selected else '☐'} {s.capitalize()}", callback_data=f"toggle_{s}")
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

async def handle_service_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    selected = set(context.user_data.get("selected_services", []))

    if data.startswith("toggle_"):
        service = data.split("_", 1)[1]
        selected.symmetric_difference_update([service])
    elif data == "select_all":
        selected = set(ALL_SERVICES)
    elif data == "deselect_all":
        selected = set()
    elif data == "proceed":
        context.user_data["selected_services"] = list(selected)
        await query.message.reply_text("👥 How many people are going?")
        return ASK_PEOPLE

    context.user_data["selected_services"] = list(selected)
    return await show_service_selection(update, context)

async def calculate_cost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        num_people = int(update.message.text)
        services = set(context.user_data.get("selected_services", []))
        days = PRICES["trek_days"]
        total_npr = 0
        breakdown = []

        if "pickup" in services:
            cars = (num_people + PRICES["persons_per_car"] - 1) // PRICES["persons_per_car"]
            cost = cars * PRICES["pickup"]
            breakdown.append(f"• 🚘 *Pickup & Drop* ({cars} car): ₹{cost}")
            total_npr += cost

        if "flight" in services:
            cost = PRICES["flight"] * num_people
            breakdown.append(f"• ✈️ *Flight Tickets* (x{num_people}): ₹{cost}")
            total_npr += cost

        if "guide" in services:
            cost = PRICES["guide"] * days
            breakdown.append(f"• 🧭 *Guide* ({days} days): ₹{cost}")
            total_npr += cost

        if "porter" in services:
            porters = max(1, (num_people + 1) // 2)
            cost = PRICES["porter"] * porters * days
            breakdown.append(f"• 💼 *Porters* ({porters}): ₹{cost}")
            total_npr += cost

        if "permit" in services:
            cost = PRICES["permit"] * num_people
            breakdown.append(f"• 🪪 *Permits* (x{num_people}): ₹{cost}")
            total_npr += cost

        if "food" in services:
            cost = PRICES["food"] * num_people * days
            breakdown.append(f"• 🍽️ *Food* ({days} days): ₹{cost}")
            total_npr += cost

        total_inr = total_npr / EXCHANGE_RATE
        per_person_inr = total_inr / num_people

        context.user_data["cost_summary"] = {
            "num_people": num_people,
            "breakdown": breakdown,
            "total_npr": total_npr,
            "total_inr": total_inr,
            "per_person_inr": per_person_inr
        }

        keyboard = [[InlineKeyboardButton("➕ Add Profit", callback_data="add_profit")]]
        await update.message.reply_markdown(
            f"📝 *Everest Base Camp Trek Cost Estimate*\n"
            f"──────────────────────────────\n"
            f"🔢 *Number of Persons:* {num_people}\n\n"
            + "\n".join(breakdown) +
            f"\n\n💰 *Total Cost:* ₹{total_npr} NPR ≈ ₹{total_inr:.2f} INR\n"
            f"👤 *Per Person:* ₹{per_person_inr:.2f} INR",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ASK_PROFIT

    except Exception as e:
        print(f"ERROR in calculate_cost: {e}")
        await update.message.reply_text("❌ Invalid number. Try again.")
        return ASK_PEOPLE

async def ask_profit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("💸 Enter profit amount per person (INR):")
    return ASK_PROFIT

async def apply_profit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        profit = float(update.message.text)
        summary = context.user_data.get("cost_summary")

        if not summary:
            await update.message.reply_text("❌ Cost data missing. Start again with /start.")
            return ConversationHandler.END

        num = summary["num_people"]
        base_pp = summary["per_person_inr"]
        new_pp = base_pp + profit
        new_total = new_pp * num

        summary["profit"] = profit
        summary["final_total"] = new_total
        summary["final_per_person"] = new_pp

        msg = (
            f"🧾 *Final Trek Summary with Profit*\n"
            f"──────────────────────────────\n"
            f"🔢 *Number of Persons:* {num}\n\n"
            + "\n".join(summary["breakdown"]) +
            f"\n\n➕ *Profit/Person:* ₹{profit:.2f}\n"
            f"👤 *New Per Person Cost:* ₹{new_pp:.2f} INR\n"
            f"💰 *Total Cost with Profit:* ₹{new_total:.2f} INR"
        )

        keyboard = [[InlineKeyboardButton("📄 Get Full Itinerary", callback_data="get_itinerary")]]
        await update.message.reply_markdown(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END

    except Exception as e:
        print(f"ERROR in apply_profit: {e}")
        await update.message.reply_text("❌ Please enter a valid number.")
        return ASK_PROFIT

async def send_itinerary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # If you have a static file, send it here
    try:
        with open("itinerary_everest_base_camp.pdf", "rb") as pdf:
            await query.message.reply_document(
                document=pdf,
                filename="Everest_Base_Camp_Itinerary.pdf",
                caption="📄 Here is your Everest Base Camp itinerary."
            )
    except FileNotFoundError:
        await query.message.reply_text("❌ Itinerary file not found.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Operation cancelled.")
    return ConversationHandler.END

# Flask webserver for Render port binding

from flask import Flask
app_web = Flask("web")

@app_web.route("/")
def home():
    return "Everest Base Camp Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_web.run(host="0.0.0.0", port=port)

# Main entrypoint

if __name__ == "__main__":
    import asyncio

    print("✅ Bot is starting...")

    persistence = PicklePersistence(filepath="ebc_bot_data.pkl")
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN") or "7511879334:AAGdDBsUp24Hm2TT6G1OazbhR5-ogcAkIJ4")\
        .persistence(persistence).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECT_ACTION: [CallbackQueryHandler(handle_start_option)],
            SELECT_SERVICES: [CallbackQueryHandler(handle_service_selection, pattern=r"^(toggle_.*|select_all|deselect_all|proceed)$")],
            ASK_PEOPLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, calculate_cost)],
            ASK_PROFIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_profit)],
            UPDATE_CHOICE: [CallbackQueryHandler(update_cost_choice)],
            UPDATE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_cost_update)],
        },
        fallbacks=[],
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(ask_profit, pattern="^add_profit$"))
    app.add_handler(CallbackQueryHandler(send_itinerary, pattern="^get_itinerary$"))

    # Start Flask webserver in a separate thread for Render
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Run the Telegram bot polling loop
    app.run_polling()