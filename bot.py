import logging
import json
import os
import asyncio
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

# Đồng giá 118K cho tất cả game
PRICE = 118000
PRICE_STR = "118K"

# Danh sách game (chỉ còn tên game, không còn phân biệt 188/588)
GAMES = ["Fly88", "F168", "New88", "QQ88", "Shbet", "Ww88"]

# Map game key cho dễ xử lý
PRODUCTS = {}
for game in GAMES:
    PRODUCTS[game.lower()] = {"game": game, "price": PRICE, "price_str": PRICE_STR}

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
        ["💳 NẠP TIỀN", "👤 TÀI KHOẢN"],
        ["🛒 MUA HÀNG", "📜 LỊCH SỬ"],
        ["☎️ HỖ TRỢ"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    init_user(user.id, user.username, user.first_name)
    
    welcome_text = (
        f"👑 *Chào mừng {user.first_name} đã đến với Hệ Thống Code Uy Tín!*\n\n"
        "✨ Vui lòng chọn các tính năng bên dưới menu để bắt đầu giao dịch."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=main_menu_keyboard())

# Biến lưu trữ trạng thái chờ nhập tên tài khoản của user
user_waiting_for_account = {}

# --- XỬ LÝ DI CHUYỂN MENU CHÍNH ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    uid = str(user_id)
    init_user(user_id, update.effective_user.username, update.effective_user.first_name)

    # Kiểm tra xem user có đang chờ nhập tên tài khoản không
    if uid in user_waiting_for_account:
        game_name = user_waiting_for_account[uid]
        account_name = text.strip()
        del user_waiting_for_account[uid]
        
        # Tạo đơn hàng chờ duyệt
        order_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{user_id}"
        db["pending_orders"][order_id] = {
            "user_id": uid,
            "user_name": update.effective_user.first_name,
            "username": update.effective_user.username,
            "game": game_name,
            "account_name": account_name,
            "status": "pending",
            "created_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        }
        save_data(db)
        
        # Gửi thông báo cho Admin
        admin_msg = (
            f"🆕 *YÊU CẦU MUA CODE MỚI*\n"
            f"───────────────────\n"
            f"🆔 *Order ID:* `{order_id}`\n"
            f"👤 *Người dùng:* {update.effective_user.first_name}\n"
            f"📝 *Username:* @{update.effective_user.username or 'Không có'}\n"
            f"🎮 *Game:* {game_name}\n"
            f"🔑 *Tên tài khoản:* `{account_name}`\n"
            f"💰 *Giá:* {PRICE_STR}\n"
            f"⏰ *Thời gian:* {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
            f"───────────────────\n"
            f"✅ /duyet_{order_id} - Duyệt đơn\n"
            f"❌ /huy_{order_id} - Từ chối"
        )
        
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(chat_id=admin_id, text=admin_msg, parse_mode="Markdown")
            except Exception as e:
                logging.error(f"Không thể gửi tin nhắn đến admin {admin_id}: {e}")
        
        await update.message.reply_text(
            f"✅ *Đã gửi yêu cầu mua code {game_name} đến Admin!*\n\n"
            f"🔑 *Tên tài khoản:* `{account_name}`\n"
            f"💰 *Giá:* {PRICE_STR}\n\n"
            f"⏳ Vui lòng chờ Admin duyệt đơn hàng. Bạn sẽ nhận được code sau khi được duyệt!",
            parse_mode="Markdown"
        )
        return

    if text == "💳 NẠP TIỀN":
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

    elif text == "👤 TÀI KHOẢN":
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

    elif text == "🛒 MUA HÀNG":
        keyboard = []
        msg_header = (
            "🛒 *DANH SÁCH CODE SẴN HÀNG*\n"
            "───────────────────────────\n"
            "⚡️ *Hệ thống phân phối tự động 24/7*\n"
            "👉 Chọn game cần mua code:"
        )
        
        # Tạo nút cho từng game với giá 118K
        row_buttons = []
        for i, game in enumerate(GAMES):
            is_mainten = db.get("maintenance", {}).get(game.lower(), False)
            status = "🔴 Bảo trì" if is_mainten else "🟢 Còn code"
            button_text = f"🎁 {game} - {PRICE_STR} [{status}]"
            row_buttons.append(InlineKeyboardButton(button_text, callback_data=f"buy_{game.lower()}"))
            
            # Mỗi hàng 2 nút
            if len(row_buttons) == 2 or i == len(GAMES) - 1:
                keyboard.append(row_buttons.copy())
                row_buttons.clear()
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(msg_header, parse_mode="Markdown", reply_markup=reply_markup)

    elif text == "📜 LỊCH SỬ":
        history = db["users"][uid].get("history", [])
        if not history:
            await update.message.reply_text("❌ Bạn chưa có lịch sử giao dịch nào.")
            return
        
        msg = "📜 *LỊCH SỬ GIAO DỊCH GẦN ĐÂY*\n"
        msg += "───────────────────\n"
        for item in history[-10:]:
            msg += f"▪️ {item}\n"
        await update.message.reply_text(msg, parse_mode="Markdown")

    elif text == "☎️ HỖ TRỢ":
        support_msg = (
            "☎️ *TRUNG TÂM CHĂM SÓC KHÁCH HÀNG*\n"
            "───────────────────────────\n"
            "👋 Chào bạn! Nếu gặp bất kỳ vấn đề gì liên quan tới lỗi nạp tiền hoặc lỗi code...\n\n"
            "👉 Vui lòng nhấn vào nút dưới đây để kết nối với bộ phận CSKH."
        )
        keyboard = [[InlineKeyboardButton("💬 Tham Gia Hỗ Trợ", url="https://t.me/cskhcodeminilive")]]
        await update.message.reply_text(support_msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# --- XỬ LÝ MUA HÀNG ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    uid = str(user_id)
    data = query.data

    # Xử lý bảo trì (admin)
    if data.startswith("mt_"):
        if user_id not in ADMIN_IDS:
            return
        game_key = data.replace("mt_", "")
        if game_key in db["maintenance"]:
            db["maintenance"][game_key] = not db["maintenance"][game_key]
            save_data(db)
            
            keyboard = []
            for key, prod in PRODUCTS.items():
                status = "🔴 OFF" if db["maintenance"].get(key, False) else "🟢 ON"
                keyboard.append([
                    InlineKeyboardButton(prod["game"], callback_data="none"),
                    InlineKeyboardButton(status, callback_data=f"mt_{key}")
                ])
            try:
                await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
            except Exception:
                pass
        return

    # Xử lý chọn game để mua
    if data.startswith("buy_"):
        game_key = data.replace("buy_", "")
        prod = PRODUCTS.get(game_key)
        
        if not prod:
            await query.edit_message_text("❌ Sản phẩm không tồn tại!")
            return
        
        if db.get("maintenance", {}).get(game_key, False):
            await query.edit_message_text(
                text=f"⚠️ Game *{prod['game']}* đang bảo trì. Vui lòng chọn game khác!",
                parse_mode="Markdown"
            )
            return
        
        # Kiểm tra số dư
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
        
        # Yêu cầu nhập tên tài khoản
        user_waiting_for_account[uid] = prod["game"]
        await query.edit_message_text(
            text=f"🎮 *Game:* {prod['game']}\n"
                 f"💰 *Giá tiền:* `{prod['price_str']}` ({prod['price']:,} VNĐ)\n\n"
                 f"📝 *Vui lòng nhập TÊN TÀI KHOẢN game của bạn:*\n"
                 f"(Admin sẽ gửi code vào tài khoản này sau khi duyệt)\n\n"
                 f"⏳ *Lưu ý:* Bạn có 5 phút để nhập, nếu quá thời gian vui lòng chọn lại.",
            parse_mode="Markdown"
        )

# --- CÁC HÀNH ĐỘNG CỦA ADMIN (DUYỆT/TỪ CHỐI ĐƠN HÀNG) ---
async def handle_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    text = update.message.text.strip()
    
    # Xử lý lệnh từ chối có lý do
    if text.startswith("/reject_"):
        parts = text.split(" ", 1)
        if len(parts) < 2:
            await update.message.reply_text("❌ Sai cú pháp! Vui lòng nhập: /reject_<order_id> <lý do từ chối>")
            return
        
        order_id = parts[0].replace("/reject_", "")
        reason = parts[1]
        
        if order_id not in db["pending_orders"]:
            await update.message.reply_text("❌ Không tìm thấy đơn hàng!")
            return
        
        order = db["pending_orders"][order_id]
        if order["status"] != "pending":
            await update.message.reply_text(f"❌ Đơn hàng này đã được {order['status']} rồi!")
            return
        
        # Cập nhật trạng thái
        order["status"] = "rejected"
        order["reason"] = reason
        order["rejected_at"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        order["rejected_by"] = user_id
        save_data(db)
        
        # Gửi thông báo từ chối cho user
        user_msg = (
            f"❌ *YÊU CẦU MUA CODE BỊ TỪ CHỐI*\n"
            f"───────────────────\n"
            f"🎮 *Game:* {order['game']}\n"
            f"🔑 *Tên tài khoản:* `{order['account_name']}`\n"
            f"💰 *Giá:* {PRICE_STR}\n"
            f"───────────────────\n"
            f"📝 *Lý do từ chối:* {reason}\n"
            f"───────────────────\n"
            f"💡 Vui lòng liên hệ Admin để được hỗ trợ thêm!"
        )
        
        try:
            await context.bot.send_message(chat_id=int(order["user_id"]), text=user_msg, parse_mode="Markdown")
            await update.message.reply_text(f"✅ Đã từ chối đơn hàng `{order_id}` và thông báo lý do đến người dùng!", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Đã từ chối đơn hàng nhưng không thể gửi thông báo: {e}")
        
        return
    
    # Xử lý lệnh duyệt
    if text.startswith("/approve_"):
        order_id = text.replace("/approve_", "").strip()
        
        if order_id not in db["pending_orders"]:
            await update.message.reply_text("❌ Không tìm thấy đơn hàng!")
            return
        
        order = db["pending_orders"][order_id]
        if order["status"] != "pending":
            await update.message.reply_text(f"❌ Đơn hàng này đã được {order['status']} rồi!")
            return
        
        game_key = order["game"].lower()
        prod = PRODUCTS[game_key]
        
        # Lấy thông tin user
        u_info = db["users"].get(order["user_id"])
        if not u_info:
            await update.message.reply_text("❌ Không tìm thấy thông tin người dùng!")
            return
        
        # Kiểm tra số dư lần nữa (phòng trường hợp user đã tiêu tiền lúc chờ)
        if u_info["balance"] < prod["price"]:
            await update.message.reply_text(
                f"❌ Số dư của user không đủ! Ví có {u_info['balance']:,} VNĐ, cần {prod['price']:,} VNĐ.\n"
                f"Vui lòng yêu cầu user nạp thêm tiền trước khi duyệt."
            )
            return
        
        # Yêu cầu admin nhập code để gửi
        context.user_data["pending_approve"] = order_id
        await update.message.reply_text(
            f"✅ *Đang duyệt đơn hàng:* `{order_id}`\n"
            f"🎮 *Game:* {order['game']}\n"
            f"🔑 *Tên tài khoản:* `{order['account_name']}`\n"
            f"💰 *Giá:* {PRICE_STR}\n\n"
            f"📝 *Vui lòng nhập MÃ CODE để gửi cho người dùng:*\n"
            f"(Nhập /cancel để hủy)",
            parse_mode="Markdown"
        )
        return

# Xử lý nhập code từ admin
async def handle_admin_code_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return
    
    if "pending_approve" not in context.user_data:
        return
    
    text = update.message.text.strip()
    
    if text == "/cancel":
        del context.user_data["pending_approve"]
        await update.message.reply_text("❌ Đã hủy duyệt đơn hàng!")
        return
    
    order_id = context.user_data["pending_approve"]
    del context.user_data["pending_approve"]
    
    if order_id not in db["pending_orders"]:
        await update.message.reply_text("❌ Đơn hàng không tồn tại!")
        return
    
    order = db["pending_orders"][order_id]
    if order["status"] != "pending":
        await update.message.reply_text(f"❌ Đơn hàng đã được {order['status']} trước đó!")
        return
    
    code = text
    game_key = order["game"].lower()
    prod = PRODUCTS[game_key]
    
    # Trừ tiền user
    u_info = db["users"].get(order["user_id"])
    if not u_info:
        await update.message.reply_text("❌ Không tìm thấy người dùng!")
        return
    
    u_info["balance"] -= prod["price"]
    time_now = datetime.now().strftime("%d/%m %H:%M")
    u_info["history"].append(f"[{time_now}] Mua {order['game']} (-{PRICE_STR}) - TK: {order['account_name']}")
    
    # Cập nhật đơn hàng
    order["status"] = "approved"
    order["approved_at"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    order["approved_by"] = user_id
    order["code"] = code
    save_data(db)
    
    # Gửi code cho user
    user_msg = (
        f"🎉 *MUA HÀNG THÀNH CÔNG!* 🎉\n"
        f"───────────────────\n"
        f"🎮 *Game:* {order['game']}\n"
        f"🔑 *Tên tài khoản:* `{order['account_name']}`\n"
        f"🔐 *Mã Code:* `{code}`\n"
        f"💰 *Số dư ví còn lại:* `{u_info['balance']:,} VNĐ`\n"
        f"───────────────────\n"
        f"✨ Ấn và đè vào mã code ở trên để copy nhanh nhé.\n"
        f"💡 *Lưu ý:* Code có thể nhập 1 lần duy nhất, vui lòng nhập đúng tài khoản!"
    )
    
    try:
        await context.bot.send_message(chat_id=int(order["user_id"]), text=user_msg, parse_mode="Markdown")
        await update.message.reply_text(f"✅ Đã duyệt đơn hàng và gửi code thành công cho {order['user_name']}!")
    except Exception as e:
        await update.message.reply_text(f"❌ Đã duyệt đơn hàng nhưng không thể gửi code: {e}")

# --- CÁC HÀM QUẢN TRỊ ADMIN KHÁC ---
async def cmd_baotri(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: 
        await update.message.reply_text("❌ Bạn không có quyền!")
        return
    
    keyboard = []
    for key, prod in PRODUCTS.items():
        status = "🔴 OFF" if db["maintenance"].get(key, False) else "🟢 ON"
        keyboard.append([
            InlineKeyboardButton(prod["game"], callback_data="none"),
            InlineKeyboardButton(status, callback_data=f"mt_{key}")
        ])
    await update.message.reply_text("🛠️ *BẢNG ĐIỀU KHIỂN BẢO TRÌ SẢN PHẨM*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def cmd_donhang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xem danh sách đơn hàng đang chờ duyệt"""
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
        msg += f"🎮 {order['game']} - TK: `{order['account_name']}`\n"
        msg += f"💰 {PRICE_STR}\n"
        msg += f"✅ /approve_{order_id}\n"
        msg += f"❌ /reject_{order_id} <lý do>\n───────────────────\n"
    
    if len(msg) > 4000:
        for chunk in [msg[i:i+4000] for i in range(0, len(msg), 4000)]:
            await update.message.reply_text(chunk, parse_mode="Markdown")
    else:
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

# --- HÀM CHẠY BOT CHÍNH ---
def main():
    TOKEN = "8960587351:AAEe0E5gUXYoZ_G864q4ek7Duu4S3foD07g"
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("baotri", cmd_baotri))
    application.add_handler(CommandHandler("tong", cmd_tong))
    application.add_handler(CommandHandler("nap", cmd_nap))
    application.add_handler(CommandHandler("thongbao", cmd_thongbao))
    application.add_handler(CommandHandler("donhang", cmd_donhang))
    
    # Xử lý lệnh duyệt/từ chối đơn hàng
    application.add_handler(MessageHandler(filters.Regex(r'^/(approve_|reject_)'), handle_admin_action))
    # Xử lý nhập code từ admin
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_code_input))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
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
