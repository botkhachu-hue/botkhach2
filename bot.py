import logging
import json
import os
import asyncio
import random
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters
import sys

# Cấu hình log hệ thống
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# File lưu trữ dữ liệu
DATA_FILE = "bot_data.json"

# Danh sách ID Admin của bạn
ADMIN_IDS = [8643692536, 8619503816]

# Đồng giá 288K cho tất cả game
PRICE = 288000
PRICE_STR = "288K"

# Danh sách game MỚI với mệnh giá 588điểm
GAMES = [
    {"name": "99ok", "value": "588điểm"},
    {"name": "33win", "value": "588điểm"},
    {"name": "88vv", "value": "588điểm"},
    {"name": "Kl99", "value": "588điểm"},
    {"name": "Okking", "value": "588điểm"},
    {"name": "79king", "value": "588điểm"}
]

# Map game key cho dễ xử lý
PRODUCTS = {}
for game in GAMES:
    key = f"{game['name'].lower()}_{game['value'].replace('điểm', 'diem')}"
    PRODUCTS[key] = {
        "game": game['name'], 
        "value": game['value'],
        "display": f"{game['name']}({game['value']})",
        "price": PRICE, 
        "price_str": PRICE_STR
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

# Hàm kiểm tra và tạo user mới nếu chưa có trong data
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

# --- MENU CHÍNH ---
def main_menu_keyboard():
    keyboard = [
        ["⚡ NẠP TIỀN", "🧑‍💻 TÀI KHOẢN"],
        ["🛍️ KHO CODE", "📦 ĐƠN HÀNG"],
        ["🔥 HỖ TRỢ ADMIN"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Lệnh /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    init_user(user.id, user.username, user.first_name)
    
    welcome_text = (
        f"👑 *Chào mừng {user.first_name} đã đến với Hệ Thống Code Uy Tín!*\n\n"
        "🚀 Chuyên cung cấp code chất lượng, hỗ trợ tận tình, giao dịch nhanh gọn.\n"
        "📌 Vui lòng chọn tính năng bên dưới để bắt đầu.\n\n"
        "💬 *Nhóm hỗ trợ & bảo hành:* https://t.me/nghientrinhbayy\n"
        "🔥 *Cảm ơn bạn đã tin tưởng đồng hành cùng hệ thống!*"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=main_menu_keyboard())

# Biến lưu trữ trạng thái
user_waiting_for_account = {}          # User chờ nhập tên tài khoản
user_pending_confirmation = {}         # User chờ xác nhận mua
timeout_tasks = {}                     # Task timeout hoàn tiền
admin_waiting_for_points = {}          # Admin đang chờ nhập số điểm cho order_id
admin_waiting_for_reason = {}          # Admin đang chờ nhập lý do từ chối cho order_id

async def refund_user(uid, amount, game_display, context):
    """Hoàn tiền cho user sau timeout"""
    await asyncio.sleep(300)  # 5 phút = 300 giây
    
    if uid in user_waiting_for_account:
        game_info = user_waiting_for_account[uid]
        del user_waiting_for_account[uid]
        
        if uid in db["users"]:
            db["users"][uid]["balance"] += PRICE
            save_data(db)
            
            try:
                await context.bot.send_message(
                    chat_id=int(uid),
                    text=f"⏰ *HẾT THỜI GIAN NHẬP TÊN TÀI KHOẢN!*\n"
                         f"───────────────────\n"
                         f"🎮 *Game:* {game_display}\n"
                         f"💰 *Số tiền đã được hoàn lại:* `{PRICE_STR}`\n"
                         f"💳 *Số dư hiện tại:* `{db['users'][uid]['balance']:,} VNĐ`\n"
                         f"───────────────────\n"
                         f"⚠️ Vui lòng thực hiện lại giao dịch nếu vẫn muốn mua hàng!",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logging.error(f"Không thể gửi thông báo hoàn tiền cho {uid}: {e}")
        
        if uid in timeout_tasks:
            del timeout_tasks[uid]

# --- XỬ LÝ MENU CHÍNH ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    uid = str(user_id)
    init_user(user_id, update.effective_user.username, update.effective_user.first_name)

    logging.info(f"User {user_id} gửi: {text}")

    # Xử lý admin đang chờ nhập số điểm
    if user_id in ADMIN_IDS and user_id in admin_waiting_for_points:
        order_id = admin_waiting_for_points[user_id]
        del admin_waiting_for_points[user_id]
        
        try:
            points = int(text.strip())
        except ValueError:
            await update.message.reply_text("❌ Số điểm không hợp lệ! Vui lòng nhập một số nguyên.")
            admin_waiting_for_points[user_id] = order_id
            return
        
        if order_id not in db["pending_orders"]:
            await update.message.reply_text("❌ Không tìm thấy đơn hàng!")
            return
        
        order = db["pending_orders"][order_id]
        if order["status"] != "pending":
            await update.message.reply_text(f"❌ Đơn hàng này đã được {order['status']} rồi!")
            return
        
        order["status"] = "approved"
        order["approved_at"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        order["approved_by"] = user_id
        order["points"] = points
        save_data(db)
        
        user_msg = (
            f"🎉 *NAP ĐIỂM THÀNH CÔNG!* 🎉\n"
            f"───────────────────\n"
            f"🎮 *Game:* {order['display']}\n"
            f"🔑 *Tên tài khoản:* `{order['account_name']}`\n"
            f"⭐ *Số điểm đã nạp:* `{points} điểm`\n"
            f"💰 *Đơn giá:* `{PRICE_STR}`\n"
            f"───────────────────\n"
            f"✅ *Giao dịch thành công! Cảm ơn bạn đã sử dụng dịch vụ!*"
        )
        
        try:
            await context.bot.send_message(chat_id=int(order["user_id"]), text=user_msg, parse_mode="Markdown")
            await update.message.reply_text(f"✅ Đã duyệt đơn hàng và nạp `{points} điểm` thành công cho {order['user_name']}!", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Đã duyệt đơn hàng nhưng không thể gửi thông báo: {e}")
        return

    # Xử lý admin đang chờ nhập lý do từ chối
    if user_id in ADMIN_IDS and user_id in admin_waiting_for_reason:
        order_id = admin_waiting_for_reason[user_id]
        del admin_waiting_for_reason[user_id]
        reason = text.strip()
        
        if order_id not in db["pending_orders"]:
            await update.message.reply_text("❌ Không tìm thấy đơn hàng!")
            return
        
        order = db["pending_orders"][order_id]
        if order["status"] != "pending":
            await update.message.reply_text(f"❌ Đơn hàng này đã được {order['status']} rồi!")
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
            f"❌ *YÊU CẦU NẠP ĐIỂM BỊ TỪ CHỐI*\n"
            f"───────────────────\n"
            f"🎮 *Game:* {order['display']}\n"
            f"🔑 *Tên tài khoản:* `{order['account_name']}`\n"
            f"💰 *Số tiền đã được hoàn lại:* {PRICE_STR}\n"
            f"───────────────────\n"
            f"📝 *Lý do từ chối:* {reason}\n"
            f"───────────────────\n"
            f"💡 Vui lòng liên hệ Admin để được hỗ trợ thêm!"
        )
        
        if u_info:
            user_msg += f"\n💳 *Số dư hiện tại:* `{u_info['balance']:,} VNĐ`"
        
        try:
            await context.bot.send_message(chat_id=int(order["user_id"]), text=user_msg, parse_mode="Markdown")
            await update.message.reply_text(f"✅ Đã từ chối đơn hàng `{order_id}` và hoàn tiền cho người dùng!", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Đã từ chối đơn hàng nhưng không thể gửi thông báo: {e}")
        return

    # Kiểm tra xem user có đang chờ nhập tên tài khoản không
    if uid in user_waiting_for_account:
        if uid in timeout_tasks:
            timeout_tasks[uid].cancel()
            del timeout_tasks[uid]
        
        game_info = user_waiting_for_account[uid]
        game_name = game_info["game"]
        game_value = game_info["value"]
        account_name = text.strip()
        del user_waiting_for_account[uid]
        
        order_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{user_id}"
        db["pending_orders"][order_id] = {
            "user_id": uid,
            "user_name": update.effective_user.first_name,
            "username": update.effective_user.username,
            "game": game_name,
            "value": game_value,
            "display": f"{game_name}({game_value})",
            "account_name": account_name,
            "status": "pending",
            "amount": PRICE,
            "created_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        }
        save_data(db)
        
        admin_msg = (
            f"🆕 *YÊU CẦU NẠP ĐIỂM MỚI*\n"
            f"───────────────────\n"
            f"🆔 *Mã lệnh:* `{order_id}`\n"
            f"👤 *Người dùng:* {update.effective_user.first_name}\n"
            f"📝 *Username:* @{update.effective_user.username or 'Không có'}\n"
            f"🎮 *Game:* {game_name}({game_value})\n"
            f"🔑 *Tên tài khoản:* `{account_name}`\n"
            f"💰 *Giá trị:* {PRICE_STR}\n"
            f"⏰ *Thời gian:* {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
            f"───────────────────\n"
            f"👉 *Vui lòng xử lý lệnh bên dưới:*"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ DUYỆT LỆNH", callback_data=f"admin_approve_{order_id}")],
            [InlineKeyboardButton("❌ TỪ CHỐI", callback_data=f"admin_reject_{order_id}")]
        ])
        
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(chat_id=admin_id, text=admin_msg, parse_mode="Markdown", reply_markup=keyboard)
            except Exception as e:
                logging.error(f"Không thể gửi tin nhắn đến admin {admin_id}: {e}")
        
        await update.message.reply_text(
            f"✅ *Đã gửi yêu cầu nạp điểm {game_name}({game_value}) đến Admin!*\n\n"
            f"🔑 *Tên tài khoản:* `{account_name}`\n"
            f"💰 *Đã trừ tiền:* {PRICE_STR}\n"
            f"💳 *Số dư hiện tại:* `{db['users'][uid]['balance']:,} VNĐ`\n\n"
            f"⏳ Vui lòng chờ Admin duyệt và nạp điểm vào tài khoản game của bạn!",
            parse_mode="Markdown"
        )
        return

    # --- CÁC TÙY CHỌN MENU CHÍNH ---
    if text == "⚡ NẠP TIỀN":
        bank_id = "MB"
        account_no = "0003456712345"
        template = "print"
        qr_url = f"https://img.vietqr.io/image/{bank_id}-{account_no}-{template}.jpg?addInfo={user_id}&accountName=LY%20THI%20CHAM"

        msg = (
            "🏦 *HỆ THỐNG NẠP TIỀN TỰ ĐỘNG*\n"
            "───────────────────\n"
            "📌 *Ngân hàng:* MBBANK (Ngân hàng Quân Đội)\n"
            "📌 *Số tài khoản:* `0003456712345`\n"
            "📌 *Chủ tài khoản:* LY THI CHAM\n"
            f"📌 *Nội dung chuyển khoản:* `{user_id}`\n"
            "───────────────────\n"
            "📸 *Quét mã QR bên dưới để tự động điền thông tin!*\n"
            "⚠️ *Lưu ý:* Vui lòng giữ nguyên nội dung chuyển khoản là **ID tài khoản** của bạn để hệ thống tự động xử lý chính xác."
        )
        try:
            await update.message.reply_photo(photo=qr_url, caption=msg, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Lỗi gửi QR: {e}")
            await update.message.reply_text(msg, parse_mode="Markdown")

    elif text == "🧑‍💻 TÀI KHOẢN":
        u_info = db["users"][uid]
        msg = (
            "👑 *THÔNG TIN TÀI KHOẢN* 👑\n"
            "───────────────────\n"
            f"🆔 *ID cá nhân:* `{user_id}`\n"
            f"👤 *Tên hiển thị:* {u_info['name']}\n"
            f"💰 *Số dư hiện tại:* `{u_info['balance']:,} VNĐ`\n"
            f"⏳ *Ngày tham gia:* {u_info['join_date']}\n"
            "───────────────────\n"
            "✨ *Uy tín tạo nên thương hiệu!*"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")

    elif text == "🛍️ KHO CODE":
        keyboard = []
        msg_header = (
            "🛒 *DANH SÁCH GAME*\n"
            "───────────────────\n"
            "👉 Chọn game cần nạp điểm:"
        )
        
        for game in GAMES:
            key = f"{game['name'].lower()}_{game['value'].replace('điểm', 'diem')}"
            is_mainten = db.get("maintenance", {}).get(key, False)
            status = "🔴 Bảo trì" if is_mainten else "🟢 Hoạt động"
            button_text = f"🎁 {game['name']}({game['value']})-{PRICE_STR} [{status}]"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"select_{key}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(msg_header, parse_mode="Markdown", reply_markup=reply_markup)

    elif text == "📦 ĐƠN HÀNG":
        history = db["users"][uid].get("history", [])
        if not history:
            await update.message.reply_text("❌ Bạn chưa có lịch sử đơn hàng nào.")
            return
        
        msg = "📜 *LỊCH SỬ GIAO DỊCH GẦN ĐÂY*\n"
        msg += "───────────────────\n"
        for item in history[-10:]:
            msg += f"▪️ {item}\n"
        await update.message.reply_text(msg, parse_mode="Markdown")

    elif text == "🔥 HỖ TRỢ ADMIN":
        support_msg = (
            "☎️ *TRUNG TÂM CHĂM SÓC KHÁCH HÀNG*\n"
            "───────────────────────────\n"
            "👋 Chào bạn! Nếu gặp bất kỳ vấn đề gì, vui lòng liên hệ bộ phận CSKH.\n\n"
            "👉 Nhấn nút bên dưới để kết nối với Admin!"
        )
        keyboard = [[InlineKeyboardButton("💬 LIÊN HỆ ADMIN", url="https://t.me/cskhcodeminilive")]]
        await update.message.reply_text(support_msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# --- XỬ LÝ CALLBACK ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    uid = str(user_id)
    data = query.data

    logging.info(f"Callback từ user {user_id}: {data}")

    # Xử lý bảo trì (admin)
    if data.startswith("mt_"):
        if user_id not in ADMIN_IDS:
            await query.answer("Bạn không có quyền!", show_alert=True)
            return
        game_key = data.replace("mt_", "")
        if game_key in db["maintenance"]:
            db["maintenance"][game_key] = not db["maintenance"][game_key]
            save_data(db)
            
            keyboard = []
            for key, prod in PRODUCTS.items():
                status = "🔴 OFF" if db["maintenance"].get(key, False) else "🟢 ON"
                keyboard.append([
                    InlineKeyboardButton(prod["display"], callback_data="none"),
                    InlineKeyboardButton(status, callback_data=f"mt_{key}")
                ])
            try:
                await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
            except Exception:
                pass
        return

    # Xử lý ADMIN DUYỆT LỆNH
    if data.startswith("admin_approve_"):
        if user_id not in ADMIN_IDS:
            await query.answer("⚠️ Chỉ Admin mới có quyền này!", show_alert=True)
            return
        
        order_id = data.replace("admin_approve_", "")
        
        if order_id not in db["pending_orders"]:
            await query.edit_message_text("❌ Không tìm thấy đơn hàng!")
            return
        
        order = db["pending_orders"][order_id]
        if order["status"] != "pending":
            await query.edit_message_text(f"❌ Đơn hàng này đã được {order['status']} rồi!")
            return
        
        admin_waiting_for_points[user_id] = order_id
        
        await query.edit_message_text(
            f"✅ *ĐANG DUYỆT LỆNH* `{order_id}`\n"
            f"───────────────────\n"
            f"🎮 *Game:* {order['display']}\n"
            f"👤 *Người dùng:* {order['user_name']}\n"
            f"🔑 *Tên tài khoản:* `{order['account_name']}`\n"
            f"💰 *Giá trị:* {PRICE_STR}\n"
            f"───────────────────\n\n"
            f"📝 *Vui lòng nhập SỐ ĐIỂM cần nạp cho người dùng:*\n"
            f"(Ví dụ: 588)\n\n"
            f"⏳ *Gõ số điểm ngay tại ô chat này để hoàn tất duyệt lệnh!*",
            parse_mode="Markdown"
        )
        return

    # Xử lý ADMIN TỪ CHỐI LỆNH
    if data.startswith("admin_reject_"):
        if user_id not in ADMIN_IDS:
            await query.answer("⚠️ Chỉ Admin mới có quyền này!", show_alert=True)
            return
        
        order_id = data.replace("admin_reject_", "")
        
        if order_id not in db["pending_orders"]:
            await query.edit_message_text("❌ Không tìm thấy đơn hàng!")
            return
        
        order = db["pending_orders"][order_id]
        if order["status"] != "pending":
            await query.edit_message_text(f"❌ Đơn hàng này đã được {order['status']} rồi!")
            return
        
        admin_waiting_for_reason[user_id] = order_id
        
        await query.edit_message_text(
            f"❌ *ĐANG TỪ CHỐI LỆNH* `{order_id}`\n"
            f"───────────────────\n"
            f"🎮 *Game:* {order['display']}\n"
            f"👤 *Người dùng:* {order['user_name']}\n"
            f"🔑 *Tên tài khoản:* `{order['account_name']}`\n"
            f"💰 *Giá trị:* {PRICE_STR}\n"
            f"───────────────────\n\n"
            f"📝 *Mời Admin viết lý do từ chối lệnh `{order_id}` tại ô chat này:*\n\n"
            f"⏳ *Gõ lý do ngay tại ô chat này để hoàn tất từ chối lệnh!*",
            parse_mode="Markdown"
        )
        return

    # Xử lý chọn game (user)
    if data.startswith("select_"):
        game_key = data.replace("select_", "")
        prod = PRODUCTS.get(game_key)
        
        if not prod:
            await query.edit_message_text("❌ Sản phẩm không tồn tại!")
            return
        
        if db.get("maintenance", {}).get(game_key, False):
            await query.edit_message_text(
                text=f"⚠️ Game *{prod['display']}* đang bảo trì. Vui lòng chọn game khác!",
                parse_mode="Markdown"
            )
            return
        
        u_info = db["users"].get(uid)
        if not u_info:
            await query.edit_message_text("❌ Lỗi dữ liệu người dùng.")
            return
        
        if u_info["balance"] < prod["price"]:
            await query.edit_message_text(
                text=f"❌ *Số dư không đủ:* Ví của bạn có `{u_info['balance']:,} VNĐ`, gói này cần `{prod['price']:,} VNĐ`. Hãy nạp thêm tiền!",
                parse_mode="Markdown"
            )
            return
        
        user_pending_confirmation[uid] = game_key
        
        confirm_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ XÁC NHẬN MUA", callback_data=f"confirm_{game_key}")],
            [InlineKeyboardButton("❌ HỦY BỎ", callback_data="cancel_buy")]
        ])
        
        await query.edit_message_text(
            text=f"🛒 *XÁC NHẬN ĐƠN HÀNG*\n"
                 f"───────────────────\n"
                 f"🎮 *Game:* {prod['display']}\n"
                 f"💰 *Giá tiền:* `{prod['price_str']}` ({prod['price']:,} VNĐ)\n"
                 f"💳 *Số dư hiện tại:* `{u_info['balance']:,} VNĐ`\n"
                 f"───────────────────\n"
                 f"⚠️ *Sau khi xác nhận, tiền sẽ được trừ khỏi tài khoản ngay lập tức!*",
            parse_mode="Markdown",
            reply_markup=confirm_keyboard
        )
        return

    # Xử lý xác nhận mua
    if data.startswith("confirm_"):
        game_key = data.replace("confirm_", "")
        prod = PRODUCTS.get(game_key)
        
        if not prod:
            await query.edit_message_text("❌ Sản phẩm không tồn tại!")
            return
        
        if uid in user_pending_confirmation:
            del user_pending_confirmation[uid]
        
        u_info = db["users"].get(uid)
        if not u_info:
            await query.edit_message_text("❌ Lỗi dữ liệu người dùng.")
            return
        
        if u_info["balance"] < prod["price"]:
            await query.edit_message_text(
                text=f"❌ *Số dư không đủ:* Ví của bạn có `{u_info['balance']:,} VNĐ`, gói này cần `{prod['price']:,} VNĐ`. Hãy nạp thêm tiền!",
                parse_mode="Markdown"
            )
            return
        
        if db.get("maintenance", {}).get(game_key, False):
            await query.edit_message_text(
                text=f"⚠️ Game *{prod['display']}* đang bảo trì. Vui lòng chọn game khác!",
                parse_mode="Markdown"
            )
            return
        
        u_info["balance"] -= prod["price"]
        save_data(db)
        
        user_waiting_for_account[uid] = {
            "game": prod["game"],
            "value": prod["value"]
        }
        
        task = asyncio.create_task(refund_user(uid, prod["price"], prod["display"], context))
        timeout_tasks[uid] = task
        
        await query.edit_message_text(
            text=f"✅ *ĐÃ TRỪ TIỀN THÀNH CÔNG!*\n"
                 f"───────────────────\n"
                 f"🎮 *Game:* {prod['display']}\n"
                 f"💰 *Đã trừ:* `{prod['price_str']}`\n"
                 f"💳 *Số dư còn lại:* `{u_info['balance']:,} VNĐ`\n"
                 f"───────────────────\n\n"
                 f"📝 *Vui lòng nhập TÊN TÀI KHOẢN game của bạn:*\n\n"
                 f"⏰ *Bạn có 5 phút để nhập, nếu quá thời gian tiền sẽ được hoàn lại!*\n"
                 f"❌ Nhập /cancel để hủy giao dịch.",
            parse_mode="Markdown"
        )
        return

    # Xử lý hủy mua
    if data == "cancel_buy":
        if uid in user_pending_confirmation:
            del user_pending_confirmation[uid]
        await query.edit_message_text("❌ *Đã hủy giao dịch mua hàng.*", parse_mode="Markdown")
        return

# Xử lý cancel từ user
async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    uid = str(user_id)
    
    if uid in user_waiting_for_account:
        if uid in timeout_tasks:
            timeout_tasks[uid].cancel()
            del timeout_tasks[uid]
        
        game_info = user_waiting_for_account[uid]
        game_display = f"{game_info['game']}({game_info['value']})"
        del user_waiting_for_account[uid]
        
        if uid in db["users"]:
            db["users"][uid]["balance"] += PRICE
            save_data(db)
            
            await update.message.reply_text(
                f"❌ *ĐÃ HỦY GIAO DỊCH VÀ HOÀN TIỀN!*\n"
                f"───────────────────\n"
                f"🎮 *Game:* {game_display}\n"
                f"💰 *Số tiền hoàn lại:* {PRICE_STR}\n"
                f"💳 *Số dư hiện tại:* `{db['users'][uid]['balance']:,} VNĐ`\n"
                f"───────────────────\n"
                f"✅ Bạn có thể thực hiện lại giao dịch nếu muốn!",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ *Đã hủy giao dịch!*", parse_mode="Markdown")
            
    elif uid in user_pending_confirmation:
        del user_pending_confirmation[uid]
        await update.message.reply_text("❌ *Đã hủy giao dịch mua hàng.*", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Không có giao dịch nào đang thực hiện để hủy.", parse_mode="Markdown")

# --- CÁC LỆNH ADMIN ---
async def cmd_baotri(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: 
        await update.message.reply_text("❌ Bạn không có quyền!")
        return
    
    keyboard = []
    for key, prod in PRODUCTS.items():
        status = "🔴 OFF" if db["maintenance"].get(key, False) else "🟢 ON"
        keyboard.append([
            InlineKeyboardButton(prod["display"], callback_data="none"),
            InlineKeyboardButton(status, callback_data=f"mt_{key}")
        ])
    await update.message.reply_text("🛠️ *BẢNG ĐIỀU KHIỂN BẢO TRÌ SẢN PHẨM*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def cmd_donhang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bạn không có quyền!")
        return
    
    pending = {k: v for k, v in db["pending_orders"].items() if v["status"] == "pending"}
    
    if not pending:
        await update.message.reply_text("📭 Không có đơn hàng nào đang chờ duyệt!")
        return
    
    msg = "📋 *DANH SÁCH ĐƠN HÀNG CHỜ DUYỆT*\n───────────────────\n"
    for order_id, order in pending.items():
        msg += f"🆔 `{order_id}`\n"
        msg += f"👤 {order['user_name']} (@{order['username'] or 'no username'})\n"
        msg += f"🎮 {order['display']} - TK: `{order['account_name']}`\n"
        msg += f"💰 {PRICE_STR}\n───────────────────\n"
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def cmd_tong(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bạn không có quyền!")
        return
    
    pending_count = len([v for v in db["pending_orders"].values() if v["status"] == "pending"])
    total_users = len(db["users"])
    
    await update.message.reply_text(
        f"📊 *THỐNG KÊ HỆ THỐNG*\n───────────────────\n"
        f"👥 *Tổng người dùng:* `{total_users}`\n"
        f"⏳ *Đơn chờ duyệt:* `{pending_count}`\n"
        f"🎮 *Số game:* `{len(PRODUCTS)}`",
        parse_mode="Markdown"
    )

async def cmd_nap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: 
        await update.message.reply_text("❌ Bạn không có quyền!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("❌ Cú pháp: /nap <user_id> <số_tiền>")
        return
    
    target_uid = context.args[0]
    try: 
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Số tiền không hợp lệ!")
        return
    
    if target_uid not in db["users"]:
        await update.message.reply_text("❌ Không tìm thấy người dùng!")
        return
    
    db["users"][target_uid]["balance"] += amount
    save_data(db)
    await update.message.reply_text(f"✅ Đã cộng `+{amount:,} VNĐ` cho `{target_uid}`", parse_mode="Markdown")
    
    try:
        await context.bot.send_message(
            chat_id=int(target_uid), 
            text=f"🔔 *NẠP TIỀN THÀNH CÔNG!*\n💰 Số dư được cộng `+{amount:,} VNĐ` từ Admin.\n📊 Số dư hiện tại: `{db['users'][target_uid]['balance']:,} VNĐ`", 
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Không thể gửi thông báo: {e}")

async def cmd_thongbao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bạn không có quyền!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Cú pháp: /thongbao <nội dung>")
        return
    
    announcement = "📢 *THÔNG BÁO TỪ ADMIN*\n───────────────────\n" + " ".join(context.args)
    count = 0
    
    for uid in db["users"].keys():
        try:
            await context.bot.send_message(chat_id=int(uid), text=announcement, parse_mode="Markdown")
            count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    
    await update.message.reply_text(f"📢 Đã gửi thông báo đến {count}/{len(db['users'])} người dùng!", parse_mode="Markdown")

# --- HÀM CHẠY BOT ---
def main():
    TOKEN = "8627628503:AAFm4RPVqu43EwHuu2Rmx8yvCFaUDPIdujo"
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("baotri", cmd_baotri))
    application.add_handler(CommandHandler("tong", cmd_tong))
    application.add_handler(CommandHandler("nap", cmd_nap))
    application.add_handler(CommandHandler("thongbao", cmd_thongbao))
    application.add_handler(CommandHandler("donhang", cmd_donhang))
    application.add_handler(CommandHandler("cancel", handle_cancel))
    
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logging.info("Bot đang chạy...")
    application.run_polling()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Bot đã dừng.")
    except Exception as e:
        logging.error(f"Lỗi: {e}")
        sys.exit(1)
