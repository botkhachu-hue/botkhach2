import logging
import json
import os
import asyncio
import random
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters
import sys
import imaplib
import email
from email.header import decode_header
import re

# Cấu hình log hệ thống
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# File lưu trữ dữ liệu
DATA_FILE = "bot_data.json"

# Danh sách ID Admin của bạn
ADMIN_IDS = [8643692536, 8619503816]

# CẤU HÌNH THÔNG TIN EMAIL VÀ NGÂN HÀNG QUÉT TỰ ĐỘNG
EMAIL_USER = "tienphongtx@gmail.com"
EMAIL_PASS = "ykbphysfymmjjtlw"
IMAP_SERVER = "imap.gmail.com"

# Giá chung 200K cho tất cả game
PRICE = 200000
PRICE_STR = "200K"

# Danh sách game - mỗi game có 2 mức điểm (288-588)
GAMES = [
    {"name": "Fly88", "icon": "🎰", "points": "288-588"},
    {"name": "Okking", "icon": "👑", "points": "288-588"},
    {"name": "88vv", "icon": "💎", "points": "288-588"},
    {"name": "99ok", "icon": "🔥", "points": "288-588"},
    {"name": "Ww88", "icon": "⚡", "points": "288-588"},
    {"name": "79king", "icon": "🎯", "points": "288-588"}
]

# Bank Real config
BANK_REAL_PRICE = 300000
BANK_REAL_PRICE_STR = "300K"
BANK_REAL_NAME = "Bank Real Log Được"

# Xây dựng PRODUCTS
PRODUCTS = {}
for game in GAMES:
    key = game['name'].lower()
    PRODUCTS[key] = {
        "type": "game",
        "game": game['name'],
        "icon": game['icon'],
        "points": game['points'],
        "display": f"{game['icon']} {game['name']} ({game['points']} điểm)",
        "price": PRICE,
        "price_str": PRICE_STR
    }

# Thêm Bank Real
PRODUCTS["bank_real"] = {
    "type": "bank_real",
    "name": BANK_REAL_NAME,
    "display": f"🏦 {BANK_REAL_NAME}",
    "price": BANK_REAL_PRICE,
    "price_str": BANK_REAL_PRICE_STR
}

# Khởi tạo hoặc đọc dữ liệu từ file JSON
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "pending_orders" not in data:
                    data["pending_orders"] = {}
                if "maintenance" not in data:
                    data["maintenance"] = {key: False for key in PRODUCTS.keys()}
                return data
        except json.JSONDecodeError:
            logging.error("File dữ liệu bị lỗi định dạng, đang khởi tạo lại!")
            
    return {
        "users": {},
        "pending_orders": {},
        "maintenance": {key: False for key in PRODUCTS.keys()}
    }

def save_data(data_to_save):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=4)

db = load_data()

def init_user(user_id, username, first_name):
    uid = str(user_id)
    if uid not in db["users"]:
        db["users"][uid] = {
            "username": username or "Không có",
            "name": first_name or "Người dùng",
            "balance": 0,
            "join_date": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "history": []
        }
        save_data(db)

# --- MENU CHÍNH SANG TRỌNG ---
def main_menu_keyboard():
    keyboard = [
        ["💳 NẠP TIỀN", "👤 TÀI KHOẢN", "🏦 BANK REAL"],
        ["🛍️ MUA HÀNG", "📦 ĐƠN HÀNG"],
        ["❓ CÁCH SỬ DỤNG", "📞 LIÊN HỆ ADMIN"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    init_user(user.id, user.username, user.first_name)
    
    welcome_text = (
        f"👑 *CHÀO MỪNG {user.first_name.upper()}!*\n\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"🏆 *HỆ THỐNG CODE UY TÍN SỐ 1*\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"✅ Giao dịch nhanh - Bảo hành tận tâm\n"
        f"✅ Uy tín tạo nên thương hiệu\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"💬 *Hỗ trợ:* @nghientrinhbayy\n"
        f"🔥 *Cảm ơn bạn đã tin tưởng!*"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=main_menu_keyboard())

# Biến lưu trữ trạng thái
user_waiting_for_account = {}
user_pending_confirmation = {}
timeout_tasks = {}
admin_waiting_for_points = {}
admin_waiting_for_reason = {}

async def refund_user(uid, amount, item_display, context):
    await asyncio.sleep(300)
    if uid in user_waiting_for_account:
        item_info = user_waiting_for_account[uid]
        del user_waiting_for_account[uid]
        if uid in db["users"]:
            db["users"][uid]["balance"] += amount
            save_data(db)
            try:
                await context.bot.send_message(
                    chat_id=int(uid),
                    text=f"⏰ *HẾT THỜI GIAN NHẬP THÔNG TIN!*\n▬▬▬▬▬▬▬▬▬▬▬▬\n📦 *Sản phẩm:* {item_display}\n💰 *Hoàn lại:* `{amount:,} VNĐ`\n💳 *Số dư:* `{db['users'][uid]['balance']:,} VNĐ`",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logging.error(f"Lỗi hoàn tiền: {e}")
        if uid in timeout_tasks:
            del timeout_tasks[uid]

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    uid = str(user_id)
    init_user(user_id, update.effective_user.username, update.effective_user.first_name)

    logging.info(f"User {user_id}: {text}")

    # Xử lý admin nhập điểm
    if user_id in ADMIN_IDS and user_id in admin_waiting_for_points:
        order_id = admin_waiting_for_points[user_id]
        del admin_waiting_for_points[user_id]
        try:
            points = int(text.strip())
        except ValueError:
            await update.message.reply_text("❌ Số điểm không hợp lệ!")
            admin_waiting_for_points[user_id] = order_id
            return
        if order_id not in db["pending_orders"]:
            await update.message.reply_text("❌ Không tìm thấy đơn hàng!")
            return
        order = db["pending_orders"][order_id]
        if order["status"] != "pending":
            await update.message.reply_text(f"❌ Đơn hàng đã được {order['status']}!")
            return
        order["status"] = "approved"
        order["approved_at"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        order["approved_by"] = user_id
        order["points"] = points
        save_data(db)
        user_msg = (
            f"🎉 *GIAO DỊCH THÀNH CÔNG!*\n▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"📦 *SP:* {order['display']}\n🔑 *TT:* `{order['account_name']}`\n"
            f"⭐ *Cấp:* `{points}`\n💰 *Giá:* `{order['amount']:,} VNĐ`\n▬▬▬▬▬▬▬▬▬▬▬▬\n✅ Cảm ơn bạn đã mua hàng!"
        )
        try:
            await context.bot.send_message(chat_id=int(order["user_id"]), text=user_msg, parse_mode="Markdown")
            await update.message.reply_text(f"✅ Đã duyệt đơn `{order_id}`!")
        except Exception as e:
            await update.message.reply_text(f"❌ Lỗi: {e}")
        return

    # Xử lý admin từ chối
    if user_id in ADMIN_IDS and user_id in admin_waiting_for_reason:
        order_id = admin_waiting_for_reason[user_id]
        del admin_waiting_for_reason[user_id]
        reason = text.strip()
        if order_id not in db["pending_orders"]:
            await update.message.reply_text("❌ Không tìm thấy đơn hàng!")
            return
        order = db["pending_orders"][order_id]
        if order["status"] != "pending":
            await update.message.reply_text(f"❌ Đơn hàng đã được {order['status']}!")
            return
        u_info = db["users"].get(order["user_id"])
        if u_info:
            u_info["balance"] += order["amount"]
            save_data(db)
        order["status"] = "rejected"
        order["reason"] = reason
        order["rejected_at"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        order["rejected_by"] = user_id
        save_data(db)
        user_msg = (
            f"❌ *ĐƠN HÀNG BỊ TỪ CHỐI*\n▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"📦 *SP:* {order['display']}\n📝 *Lý do:* {reason}\n"
            f"💰 *Hoàn lại:* `{order['amount']:,} VNĐ`"
        )
        try:
            await context.bot.send_message(chat_id=int(order["user_id"]), text=user_msg, parse_mode="Markdown")
            await update.message.reply_text("✅ Đã từ chối đơn hàng!")
        except Exception as e:
            await update.message.reply_text(f"❌ Lỗi: {e}")
        return

    # User nhập thông tin
    if uid in user_waiting_for_account:
        if uid in timeout_tasks:
            timeout_tasks[uid].cancel()
            del timeout_tasks[uid]
        item_info = user_waiting_for_account[uid]
        item_display = item_info["display"]
        account_name = text.strip()
        del user_waiting_for_account[uid]
        order_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{user_id}"
        db["pending_orders"][order_id] = {
            "user_id": uid, "user_name": update.effective_user.first_name,
            "username": update.effective_user.username, "display": item_display,
            "account_name": account_name, "status": "pending",
            "amount": item_info["price"], "created_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        }
        save_data(db)
        admin_msg = (
            f"🆕 *ĐƠN HÀNG MỚI*\n▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"🆔 `{order_id}`\n👤 {update.effective_user.first_name}\n"
            f"📦 {item_display}\n🔑 `{account_name}`\n💰 `{item_info['price']:,} VNĐ`"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ DUYỆT", callback_data=f"admin_approve_{order_id}")],
            [InlineKeyboardButton("❌ TỪ CHỐI", callback_data=f"admin_reject_{order_id}")]
        ])
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(chat_id=admin_id, text=admin_msg, parse_mode="Markdown", reply_markup=keyboard)
            except Exception as e:
                logging.error(f"Lỗi gửi admin {admin_id}: {e}")
        await update.message.reply_text(
            f"✅ *ĐÃ GỬI YÊU CẦU MUA HÀNG!*\n▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"📦 {item_display}\n🔑 `{account_name}`\n💰 Đã trừ: `{item_info['price']:,} VNĐ`\n"
            f"💳 Dư: `{db['users'][uid]['balance']:,} VNĐ`\n▬▬▬▬▬▬▬▬▬▬▬▬\n⏳ Chờ admin duyệt!",
            parse_mode="Markdown"
        )
        return

    # MENU CHÍNH
    if text == "💳 NẠP TIỀN":
        # Cập nhật QR và Thông tin sang Vietcombank
        qr_url = f"https://img.vietqr.io/image/VCB-1068030340-print.jpg?addInfo={user_id}&accountName=BAN%20TIEN%20PHONG"
        msg = (
            "🏦 *HỆ THỐNG NẠP TIỀN TỰ ĐỘNG*\n▬▬▬▬▬▬▬▬▬▬▬▬\n"
            "📌 *Ngân hàng:* VIETCOMBANK (VCB)\n📌 *STK:* `1068030340`\n📌 *Chủ TK:* BAN TIEN PHONG\n"
            f"📌 *Nội dung:* `{user_id}`\n▬▬▬▬▬▬▬▬▬▬▬▬\n"
            "⚠️ *LƯU Ý:* Nhập chính xác mã ID nội dung để được cộng tiền tự động sau 10 giây!\n"
            "📸 *Quét mã QR để chuyển khoản nhanh!*"
        )
        try:
            await update.message.reply_photo(photo=qr_url, caption=msg, parse_mode="Markdown")
        except:
            await update.message.reply_text(msg, parse_mode="Markdown")

    elif text == "👤 TÀI KHOẢN":
        u_info = db["users"][uid]
        msg = (
            f"👤 *THÔNG TIN TÀI KHOẢN*\n▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"🆔 *ID:* `{user_id}`\n👤 *Tên:* {u_info['name']}\n"
            f"💰 *Số dư:* `{u_info['balance']:,} VNĐ`\n📅 *Tham gia:* {u_info['join_date']}\n▬▬▬▬▬▬▬▬▬▬▬▬\n✨ Uy tín tạo nên thương hiệu!"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")

    elif text == "🏦 BANK REAL":
        prod = PRODUCTS["bank_real"]
        u_info = db["users"][uid]
        if u_info["balance"] < prod["price"]:
            await update.message.reply_text(
                f"❌ *Số dư không đủ!*\n💰 Cần: `{prod['price']:,} VNĐ`\n💳 Bạn có: `{u_info['balance']:,} VNĐ`",
                parse_mode="Markdown"
            )
            return
        msg = (
            f"🏦 *{BANK_REAL_NAME}*\n▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"📌 Log Bank Real chất lượng cao\n📌 Cập nhật liên tục\n📌 Bảo hành 24/7\n▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"💰 *Giá:* `{prod['price']:,} VNĐ`\n💳 *Số dư:* `{u_info['balance']:,} VNĐ`"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ MUA NGAY", callback_data="confirm_bank_real")],
            [InlineKeyboardButton("❌ HỦY", callback_data="cancel_buy")]
        ])
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=keyboard)

    elif text == "🛍️ MUA HÀNG":
        keyboard = []
        row = []
        for i, game in enumerate(GAMES):
            button_text = f"{game['icon']} {game['name']} ({game['points']})"
            row.append(InlineKeyboardButton(button_text, callback_data=f"select_{game['name'].lower()}"))
            if len(row) == 2 or i == len(GAMES) - 1:
                keyboard.append(row)
                row = []
        keyboard.append([InlineKeyboardButton("🏦 BANK REAL", callback_data="select_bank_real")])
        
        msg_header = (
            "🛍️ *CỬA HÀNG CODE UY TÍN*\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            "✅ Vui lòng đọc kỹ mô tả trước khi mua\n"
            "✅ Giá đã bao gồm bảo hành 24/7\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            "👇 *Chọn sản phẩm bên dưới:*"
        )
        await update.message.reply_text(msg_header, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif text == "📦 ĐƠN HÀNG":
        history = db["users"][uid].get("history", [])
        if not history:
            await update.message.reply_text("📭 *Bạn chưa có đơn hàng nào!*", parse_mode="Markdown")
            return
        msg = "📜 *LỊCH SỬ GIAO DỊCH*\n▬▬▬▬▬▬▬▬▬▬▬▬\n"
        for item in history[-10:]:
            msg += f"▪️ {item}\n"
        await update.message.reply_text(msg, parse_mode="Markdown")

    elif text == "❓ CÁCH SỬ DỤNG":
        msg = (
            "📖 *HƯỚNG DẪN SỬ DỤNG*\n▬▬▬▬▬▬▬▬▬▬▬▬\n"
            "1️⃣ Bấm *NẠP TIỀN* để nạp ví\n"
            "2️⃣ Bấm *MUA HÀNG* chọn sản phẩm\n"
            "3️⃣ Xác nhận và nhập thông tin\n"
            "4️⃣ Chờ Admin duyệt (1-3 phút)\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬\n"
            "✅ *Bảo hành:* Liên hệ @nghientrinhbayy"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")

    elif text == "📞 LIÊN HỆ ADMIN":
        keyboard = [[InlineKeyboardButton("💬 CHAT VỚI ADMIN", url="https://t.me/cskhcodeminilive")]]
        await update.message.reply_text(
            "📞 *LIÊN HỆ HỖ TRỢ*\n▬▬▬▬▬▬▬▬▬▬▬▬\n👋 Gặp sự cố? Bấm bên dưới để được hỗ trợ ngay!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# --- XỬ LÝ CALLBACK ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    uid = str(user_id)
    data = query.data

    # Admin duyệt
    if data.startswith("admin_approve_"):
        if user_id not in ADMIN_IDS:
            await query.answer("⚠️ Chỉ Admin!", show_alert=True)
            return
        order_id = data.replace("admin_approve_", "")
        if order_id in db["pending_orders"] and db["pending_orders"][order_id]["status"] == "pending":
            admin_waiting_for_points[user_id] = order_id
            await query.edit_message_text(f"✅ Nhập số điểm/ND cho đơn `{order_id}`:", parse_mode="Markdown")
        return

    if data.startswith("admin_reject_"):
        if user_id not in ADMIN_IDS:
            await query.answer("⚠️ Chỉ Admin!", show_alert=True)
            return
        order_id = data.replace("admin_reject_", "")
        if order_id in db["pending_orders"] and db["pending_orders"][order_id]["status"] == "pending":
            admin_waiting_for_reason[user_id] = order_id
            await query.edit_message_text(f"❌ Nhập lý do từ chối đơn `{order_id}`:", parse_mode="Markdown")
        return

    # Xem chi tiết sản phẩm
    if data.startswith("select_"):
        product_key = data.replace("select_", "")
        
        if product_key == "bank_real":
            prod = PRODUCTS["bank_real"]
            msg = (
                f"🏦 *{BANK_REAL_NAME}*\n▬▬▬▬▬▬▬▬▬▬▬▬\n"
                f"📌 Log Bank Real chất lượng cao\n📌 Cập nhật liên tục\n📌 Bảo hành 24/7\n▬▬▬▬▬▬▬▬▬▬▬▬\n"
                f"💰 *Giá:* `{prod['price']:,} VNĐ`\n▬▬▬▬▬▬▬▬▬▬▬▬\n✅ Bấm xác nhận để mua hàng"
            )
        else:
            prod = PRODUCTS.get(product_key)
            if not prod:
                await query.edit_message_text("❌ Sản phẩm không tồn tại!")
                return
            msg = (
                f"{prod['icon']} *{prod['game']}*\n▬▬▬▬▬▬▬▬▬▬▬▬\n"
                f"📌 Code {prod['game']} - {prod['points']} điểm\n📌 Bảo hành 1 đổi 1 nếu lỗi\n"
                f"📌 Nhập tài khoản game sau thanh toán\n▬▬▬▬▬▬▬▬▬▬▬▬\n"
                f"💰 *Giá:* `{prod['price']:,} VNĐ`\n▬▬▬▬▬▬▬▬▬▬▬▬\n✅ Bấm xác nhận để mua hàng"
            )
        
        confirm_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ XÁC NHẬN MUA", callback_data=f"confirm_{product_key}")],
            [InlineKeyboardButton("🔙 QUAY LẠI", callback_data="back_to_shop")]
        ])
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=confirm_keyboard)
        return

    # Quay lại shop
    if data == "back_to_shop":
        keyboard = []
        row = []
        for i, game in enumerate(GAMES):
            button_text = f"{game['icon']} {game['name']} ({game['points']})"
            row.append(InlineKeyboardButton(button_text, callback_data=f"select_{game['name'].lower()}"))
            if len(row) == 2 or i == len(GAMES) - 1:
                keyboard.append(row)
                row = []
        keyboard.append([InlineKeyboardButton("🏦 BANK REAL", callback_data="select_bank_real")])
        msg_header = (
            "🛍️ *CỬA HÀNG CODE UY TÍN*\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            "👇 *Chọn sản phẩm bên dưới:*"
        )
        await query.edit_message_text(msg_header, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Xác nhận mua Bank Real
    if data == "confirm_bank_real":
        prod = PRODUCTS["bank_real"]
        u_info = db["users"].get(uid)
        if not u_info or u_info["balance"] < prod["price"]:
            await query.edit_message_text("❌ *Số dư không đủ!*", parse_mode="Markdown")
            return
        u_info["balance"] -= prod["price"]
        save_data(db)
        user_waiting_for_account[uid] = {"display": prod["display"], "price": prod["price"]}
        task = asyncio.create_task(refund_user(uid, prod["price"], prod["display"], context))
        timeout_tasks[uid] = task
        await query.edit_message_text(
            f"✅ *ĐÃ TRỪ TIỀN!*\n▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"📦 {prod['display']}\n💰 Đã trừ: `{prod['price']:,} VNĐ`\n"
            f"💳 Dư: `{u_info['balance']:,} VNĐ`\n▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"📝 *Nhập THÔNG TIN LOG NHẬN HÀNG:*\n⏰ Có 5 phút - /cancel để hủy",
            parse_mode="Markdown"
        )
        return

    # Xác nhận mua game
    if data.startswith("confirm_") and data != "confirm_bank_real":
        product_key = data.replace("confirm_", "")
        prod = PRODUCTS.get(product_key)
        if not prod:
            await query.edit_message_text("❌ Sản phẩm không tồn tại!")
            return
        u_info = db["users"].get(uid)
        if not u_info or u_info["balance"] < prod["price"]:
            await query.edit_message_text("❌ *Số dư không đủ!*", parse_mode="Markdown")
            return
        u_info["balance"] -= prod["price"]
        save_data(db)
        user_waiting_for_account[uid] = {"display": prod["display"], "price": prod["price"]}
        task = asyncio.create_task(refund_user(uid, prod["price"], prod["display"], context))
        timeout_tasks[uid] = task
        await query.edit_message_text(
            f"✅ *ĐÃ TRỪ TIỀN!*\n▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"🎮 {prod['display']}\n💰 Đã trừ: `{prod['price']:,} VNĐ`\n"
            f"💳 Dư: `{u_info['balance']:,} VNĐ`\n▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"📝 *Nhập TÊN TÀI KHOẢN {prod['game']}:*\n⏰ Có 5 phút - /cancel để hủy",
            parse_mode="Markdown"
        )
        return

    if data == "cancel_buy":
        if uid in user_pending_confirmation:
            del user_pending_confirmation[uid]
        await query.edit_message_text("❌ *Đã hủy giao dịch!*", parse_mode="Markdown")
        return

# Xử lý cancel
async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    uid = str(user_id)
    if uid in user_waiting_for_account:
        if uid in timeout_tasks:
            timeout_tasks[uid].cancel()
            del timeout_tasks[uid]
        item_info = user_waiting_for_account[uid]
        item_display = item_info["display"]
        del user_waiting_for_account[uid]
        if uid in db["users"]:
            db["users"][uid]["balance"] += item_info["price"]
            save_data(db)
            await update.message.reply_text(
                f"❌ *ĐÃ HỦY GIAO DỊCH!*\n▬▬▬▬▬▬▬▬▬▬▬▬\n"
                f"📦 {item_display}\n💰 Hoàn lại: `{item_info['price']:,} VNĐ`\n"
                f"💳 Dư: `{db['users'][uid]['balance']:,} VNĐ`",
                parse_mode="Markdown"
            )
    else:
        await update.message.reply_text("❌ Không có giao dịch nào để hủy!")

# --- LỆNH ADMIN ---
async def cmd_baotri(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bạn không có quyền!")
        return
    keyboard = []
    for key, prod in PRODUCTS.items():
        status = "🔴 OFF" if db["maintenance"].get(key, False) else "🟢 ON"
        keyboard.append([InlineKeyboardButton(prod["display"], callback_data="none"), InlineKeyboardButton(status, callback_data=f"mt_{key}")])
    await update.message.reply_text("🛠️ *BẢO TRÌ SẢN PHẨM*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def cmd_donhang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bạn không có quyền!")
        return
    pending = {k: v for k, v in db["pending_orders"].items() if v["status"] == "pending"}
    if not pending:
        await update.message.reply_text("📭 Không có đơn chờ duyệt!")
        return
    msg = "📋 *ĐƠN CHỜ DUYỆT*\n▬▬▬▬▬▬▬▬▬▬▬▬\n"
    for oid, od in pending.items():
        msg += f"🆔 `{oid}`\n👤 {od['user_name']}\n📦 {od['display']}\n💰 `{od['amount']:,} VNĐ`\n▬▬▬▬▬▬▬▬▬▬▬▬\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def cmd_tong(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bạn không có quyền!")
        return
    await update.message.reply_text(
        f"📊 *THỐNG KÊ*\n▬▬▬▬▬▬▬▬▬▬▬▬\n👥 Users: `{len(db['users'])}`\n⏳ Đơn chờ: `{len([v for v in db['pending_orders'].values() if v['status'] == 'pending'])}`\n🎮 SP: `{len(PRODUCTS)}`",
        parse_mode="Markdown"
    )

async def cmd_nap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bạn không có quyền!")
        return
    if len(context.args) < 2:
        await update.message.reply_text("❌ /nap <user_id> <số_tiền>")
        return
    target = context.args[0]
    try:
        amount = int(context.args[1])
    except:
        await update.message.reply_text("❌ Số tiền không hợp lệ!")
        return
    if target not in db["users"]:
        await update.message.reply_text("❌ Không tìm thấy user!")
        return
    db["users"][target]["balance"] += amount
    save_data(db)
    await update.message.reply_text(f"✅ Đã cộng `+{amount:,} VNĐ` cho `{target}`", parse_mode="Markdown")

async def cmd_thongbao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bạn không có quyền!")
        return
    if not context.args:
        await update.message.reply_text("❌ /thongbao <nội dung>")
        return
    msg = "📢 *THÔNG BÁO TỪ ADMIN*\n▬▬▬▬▬▬▬▬▬▬▬▬\n" + " ".join(context.args)
    count = 0
    for uid in db["users"].keys():
        try:
            await context.bot.send_message(chat_id=int(uid), text=msg, parse_mode="Markdown")
            count += 1
            await asyncio.sleep(0.05)
        except:
            pass
    await update.message.reply_text(f"✅ Đã gửi đến {count}/{len(db['users'])} người!")

# --- HÀM QUÉT EMAIL NẠP TIỀN TỰ ĐỘNG ---
async def check_email_deposits(context: ContextTypes.DEFAULT_TYPE):
    """Hàm chạy ngầm tự động quét email để nạp tiền từ Vietcombank"""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")

        # Quét các Email CHƯA ĐỌC từ Vietcombank gửi về
        status, messages = mail.search(None, 'UNSEEN FROM "vcbnews@vietcombank.com.vn"')
        if status != "OK":
            return

        for num in messages[0].split():
            status, data = mail.fetch(num, "(RFC822)")
            if status != "OK":
                continue
                
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

            if not body:
                continue

            # Đánh dấu email đã xử lý
            mail.store(num, "+FLAGS", "\\Seen")

            # REGEX LỌC SỐ TIỀN VÀ NỘI DUNG CHUYỂN KHOẢN (ID TELEGRAM) CỦA VCB
            # Bắt dạng: +100,000 VND hoặc +50.000 VND hoặc +200000VND
            amount_match = re.search(r"\+([0-9,.]+)\s*(?:VND|đ|VND\.)", body, re.IGNORECASE)
            # Bắt ID người dùng (chuỗi số liên tiếp từ 8 đến 11 ký tự)
            user_id_match = re.search(r"\b([0-9]{8,11})\b", body)

            if amount_match and user_id_match:
                amount_str = amount_match.group(1).replace(",", "").replace(".", "")
                amount = int(amount_str)
                target_uid = user_id_match.group(1)

                current_db = load_data()
                if target_uid in current_db["users"]:
                    current_db["users"][target_uid]["balance"] += amount
                    log_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    current_db["users"][target_uid]["history"].append(f"{log_time}: Nạp tự động +{amount:,} VNĐ qua VCB")
                    save_data(current_db)
                    
                    global db
                    db = current_db

                    success_msg = (
                        f"💳 *THÔNG BÁO NẠP TIỀN TỰ ĐỘNG*\n▬▬▬▬▬▬▬▬▬▬▬▬\n"
                        f"✅ Hệ thống đã nhận được tiền của bạn!\n"
                        f"💰 Số tiền: `+{amount:,} VNĐ`\n"
                        f"💳 Số dư hiện tại: `{db['users'][target_uid]['balance']:,} VNĐ`\n▬▬▬▬▬▬▬▬▬▬▬▬\n"
                        f"✨ Cảm ơn bạn đã sử dụng dịch vụ!"
                    )
                    try:
                        await context.bot.send_message(chat_id=int(target_uid), text=success_msg, parse_mode="Markdown")
                        logging.info(f"Đã nạp tự động thành công {amount} VNĐ cho UID: {target_uid}")
                    except Exception as e:
                        logging.error(f"Không thể gửi tin nhắn cho user {target_uid}: {e}")
                        
        mail.close()
        mail.logout()
    except Exception as e:
        logging.error(f"Lỗi trong quá trình quét Email nạp tiền: {e}")

# --- CHẠY BOT ---
def main():
    TOKEN = "8627628503:AAFm4RPVqu43EwHuu2Rmx8yvCFaUDPIdujo"
    
    # Sử dụng Builder để khởi tạo mặc định đầy đủ các thành phần hệ thống
    application = Application.builder().token(TOKEN).build()
    
    # Kiểm tra an toàn trước khi gọi job_queue tránh lỗi 'NoneType'
    job_queue = application.job_queue
    if job_queue is not None:
        # Cấu hình tự động quét email mỗi 30 giây để kiểm tra giao dịch
        job_queue.run_repeating(check_email_deposits, interval=30, first=10)
        logging.info("Tác vụ chạy ngầm quét Email đã được kích hoạt thành công!")
    else:
        logging.error("Hệ thống chưa thể khởi tạo JobQueue. Vui lòng kiểm tra lại gói cài đặt 'python-telegram-bot[job-queue]'.")
    
    # Đăng ký các bộ xử lý lệnh (Handlers)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("baotri", cmd_baotri))
    application.add_handler(CommandHandler("tong", cmd_tong))
    application.add_handler(CommandHandler("nap", cmd_nap))
    application.add_handler(CommandHandler("thongbao", cmd_thongbao))
    application.add_handler(CommandHandler("donhang", cmd_donhang))
    application.add_handler(CommandHandler("cancel", handle_cancel))
    
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logging.info("Bot đang kết nối dịch vụ...")
    application.run_polling()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Bot dừng.")
    except Exception as e:
        logging.error(f"Lỗi: {e}")
        sys.exit(1)
