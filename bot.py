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

# Cấu hình danh mục sản phẩm (Đã tối ưu hóa hiển thị ngắn gọn)
PRODUCTS = {
    "fly88_188": {"game": "Fly88", "points": "188đ", "price": 79000, "price_str": "79K"},
    "fly88_588": {"game": "Fly88", "points": "588đ", "price": 220000, "price_str": "220K"},
    
    "f168_188": {"game": "F168", "points": "188đ", "price": 79000, "price_str": "79K"},
    "f168_588": {"game": "F168", "points": "588đ", "price": 220000, "price_str": "220K"},
    
    "new88_188": {"game": "New88", "points": "188đ", "price": 79000, "price_str": "79K"},
    "new88_588": {"game": "New88", "points": "588đ", "price": 220000, "price_str": "220K"},
    
    "qq88_188": {"game": "QQ88", "points": "188đ", "price": 79000, "price_str": "79K"},
    "qq88_588": {"game": "QQ88", "points": "588đ", "price": 220000, "price_str": "220K"},
    
    "shbet_188": {"game": "Shbet", "points": "188đ", "price": 79000, "price_str": "79K"},
    "shbet_588": {"game": "Shbet", "points": "588đ", "price": 220000, "price_str": "220K"}
}

# Khởi tạo hoặc đọc dữ liệu từ file JSON
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "maintenance" not in data:
                    data["maintenance"] = {key: False for key in PRODUCTS.keys()}
                for key in PRODUCTS.keys():
                    if key not in data["codes"]:
                        data["codes"][key] = []
                    if key not in data["maintenance"]:
                        data["maintenance"][key] = False
                return data
        except json.JSONDecodeError:
            logging.error("File dữ liệu bị lỗi định dạng, đang khởi tạo lại!")
            
    return {
        "users": {},
        "codes": {key: [] for key in PRODUCTS.keys()},
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
        ["📈 SỐ LƯỢNG CODE", "☎️ HỖ TRỢ"]
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

# --- XỬ LÝ DI CHUYỂN MENU CHÍNH ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    uid = str(user_id)
    init_user(user_id, update.effective_user.username, update.effective_user.first_name)

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
            "👉 Chọn gói sản phẩm cần mua:"
        )
        
        # Tạo nút bấm dạng cột đôi ngắn gọn: Trái (188đ) - Phải (588đ) của cùng 1 game xếp chung 1 hàng
        # Giúp menu ngắn đi một nửa chiều dài, hiển thị rõ số lượng, không bao giờ bị tràn màn hình
        game_keys = list(db["codes"].keys())
        for i in range(0, len(game_keys), 2):
            row_buttons = []
            for j in range(2):
                if i + j < len(game_keys):
                    key = game_keys[i + j]
                    prod = PRODUCTS[key]
                    is_mainten = db.get("maintenance", {}).get(key, False)
                    
                    if is_mainten:
                        status = "Bảo trì"
                    else:
                        stock = len(db['codes'].get(key, []))
                        status = f"Còn {stock}" if stock > 0 else "Hết"
                    
                    # Chuỗi text siêu ngắn gọn: Fly88(188đ)-79K [Còn 20]
                    button_text = f"🎁 {prod['game']}({prod['points']})-{prod['price_str']} [{status}]"
                    row_buttons.append(InlineKeyboardButton(button_text, callback_data=f"prod_{key}"))
            keyboard.append(row_buttons)
        
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

    elif text == "📈 SỐ LƯỢNG CODE":
        msg = "📊 *THỐNG KÊ KHO CODE HIỆN TẠI*\n"
        msg += "───────────────────\n"
        for key, prod in PRODUCTS.items():
            count = len(db["codes"].get(key, []))
            is_mainten = db.get("maintenance", {}).get(key, False)
            status_str = " (⚠️ Bảo trì)" if is_mainten else ""
            msg += f"🎁 *{prod['game']} ({prod['points']}):* Còn `{count}` code{status_str}\n"
        msg += "───────────────────"
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

# --- XỬ LÝ MUA HÀNG & CHECK KHO & BẢO TRÌ CALLBACK ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    uid = str(user_id)
    data = query.data

    if data.startswith("mt_"):
        if user_id not in ADMIN_IDS:
            return
        prod_key = data.replace("mt_", "")
        if prod_key in db["maintenance"]:
            db["maintenance"][prod_key] = not db["maintenance"][prod_key]
            save_data(db)
            
            keyboard = []
            for key, prod in PRODUCTS.items():
                status = "🔴 OFF" if db["maintenance"].get(key, False) else "🟢 ON"
                keyboard.append([
                    InlineKeyboardButton(f"{prod['game']}({prod['points']})", callback_data="none"),
                    InlineKeyboardButton(status, callback_data=f"mt_{key}")
                ])
            try:
                await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
            except Exception:
                pass
        return

    if data.startswith("prod_"):
        prod_key = data.split("_")[1] + "_" + data.split("_")[2]
        prod = PRODUCTS[prod_key]
        
        if db.get("maintenance", {}).get(prod_key, False):
            await query.edit_message_text(
                text=f"⚠️ Gói *{prod['game']} ({prod['points']})* đang bảo trì. Vui lòng chọn gói khác!",
                parse_mode="Markdown"
            )
            return
            
        keyboard = [
            [
                InlineKeyboardButton("✅ Xác Nhận Mua", callback_data=f"confirm_{prod_key}"),
                InlineKeyboardButton("❌ Hủy Bỏ", callback_data="cancel_buy")
            ]
        ]
        await query.edit_message_text(
            text=f"❓ *Xác nhận mua:* {prod['game']} ({prod['points']})\n💰 *Giá tiền:* `{prod['price_str']}` ({prod['price']:,} VNĐ)?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    elif data.startswith("confirm_"):
        prod_key = data.split("_")[1] + "_" + data.split("_")[2]
        prod = PRODUCTS[prod_key]
        u_info = db["users"].get(uid)
        
        if not u_info:
            await query.edit_message_text("❌ Lỗi dữ liệu người dùng.")
            return

        if db.get("maintenance", {}).get(prod_key, False):
            await query.edit_message_text(text=f"⚠️ Sản phẩm *{prod['game']}* vừa bảo trì!", parse_mode="Markdown")
            return

        if not db["codes"].get(prod_key):
            suggest_keyboard = []
            for key, p_item in PRODUCTS.items():
                p_count = len(db["codes"].get(key, []))
                is_m = db.get("maintenance", {}).get(key, False)
                if p_count > 0 and not is_m:  
                    suggest_keyboard.append([InlineKeyboardButton(f"🎁 {p_item['game']}({p_item['points']}) (Còn: {p_count})", callback_data=f"prod_{key}")])
            
            error_msg = f"😭 *Loại code {prod['game']} ({prod['points']}) hiện tại vừa cháy hàng.*\n👇 Bạn có thể tham khảo các dòng code sẵn hàng dưới đây:"
            if suggest_keyboard:
                await query.edit_message_text(text=error_msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(suggest_keyboard))
            else:
                await query.edit_message_text(text=f"❌ *Hệ thống hết code, vui lòng liên hệ Admin.*", parse_mode="Markdown")
            return

        if u_info["balance"] < prod["price"]:
            await query.edit_message_text(
                text=f"❌ *Số dư không đủ:* Ví của bạn có `{u_info['balance']:,} VNĐ`, gói này cần `{prod['price']:,} VNĐ`. Hãy nạp thêm tiền!",
                parse_mode="Markdown"
            )
            return
            
        u_info["balance"] -= prod["price"]
        code_bought = db["codes"][prod_key].pop(0)  
        
        time_now = datetime.now().strftime("%d/%m %H:%M")
        u_info["history"].append(f"[{time_now}] Mua {prod['game']}({prod['points']}) (-{prod['price_str']})")
        save_data(db)
        
        success_msg = (
            "🎉 *MUA HÀNG THÀNH CÔNG!* 🎉\n"
            "───────────────────\n"
            f"📦 *Sản phẩm:* {prod['game']} ({prod['points']})\n"
            f"🔑 *Mã Code:* `{code_bought}`\n"
            f"💰 *Số dư ví:* `{u_info['balance']:,} VNĐ`\n"
            "───────────────────\n"
            "✨ Ấn và đè vào mã code ở trên để copy nhanh nhé."
        )
        await query.edit_message_text(text=success_msg, parse_mode="Markdown")
        
    elif data == "cancel_buy":
        await query.edit_message_text("❌ *Đã hủy giao dịch mua hàng.*")

# --- CÁC HÀM QUẢN TRỊ ADMIN ---
async def cmd_baotri(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    keyboard = []
    for key, prod in PRODUCTS.items():
        status = "🔴 OFF" if db["maintenance"].get(key, False) else "🟢 ON"
        keyboard.append([
            InlineKeyboardButton(f"{prod['game']}({prod['points']})", callback_data="none"),
            InlineKeyboardButton(status, callback_data=f"mt_{key}")
        ])
    await update.message.reply_text("🛠️ *BẢNG ĐIỀU KHIỂN BẢO TRÌ SẢN PHẨM*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

def process_bulk_codes(lines, suffix_type, default_game):
    current_game = default_game
    report_dict = {}
    for line in lines:
        if ":" in line:
            parts = line.split(":", 1)
            possible_game = parts[0].strip().lower()
            full_key = f"{possible_game}_{suffix_type}"
            if full_key in PRODUCTS:
                current_game = full_key
                if current_game not in report_dict: report_dict[current_game] = 0
                inline_content = parts[1].strip()
                if inline_content:
                    for sp in inline_content.split(","):
                        clean_code = sp.strip()
                        if clean_code:
                            db["codes"][current_game].append(clean_code)
                            report_dict[current_game] += 1
                continue
        if current_game:
            if current_game not in report_dict: report_dict[current_game] = 0
            for sp in line.split(","):
                clean_code = sp.strip()
                if clean_code:
                    db["codes"][current_game].append(clean_code)
                    report_dict[current_game] += 1
    return report_dict

async def cmd_themcodesll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    message_text = update.message.text
    lines = [line.strip() for line in message_text.split('\n') if line.strip()]
    first_line_parts = lines[0].split()
    default_game = f"{first_line_parts[1].lower()}_188" if len(first_line_parts) >= 2 and f"{first_line_parts[1].lower()}_188" in PRODUCTS else None
    lines.pop(0)
    if not lines: return
    report_dict = process_bulk_codes(lines, "188", default_game)
    save_data(db)
    msg = "📊 *KẾT QUẢ THÊM CODE 188 ĐIỂM (79K):*\n"
    for g_key, count in report_dict.items():
        if count > 0: msg += f"✅ *{PRODUCTS[g_key]['game']}:* +{count} code (Tổng: `{len(db['codes'][g_key])}`)\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def cmd_themcodesll1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    message_text = update.message.text
    lines = [line.strip() for line in message_text.split('\n') if line.strip()]
    first_line_parts = lines[0].split()
    default_game = f"{first_line_parts[1].lower()}_588" if len(first_line_parts) >= 2 and f"{first_line_parts[1].lower()}_588" in PRODUCTS else None
    lines.pop(0)
    if not lines: return
    report_dict = process_bulk_codes(lines, "588", default_game)
    save_data(db)
    msg = "📊 *KẾT QUẢ THÊM CODE 588 ĐIỂM (220K):*\n"
    for g_key, count in report_dict.items():
        if count > 0: msg += f"✅ *{PRODUCTS[g_key]['game']}:* +{count} code (Tổng: `{len(db['codes'][g_key])}`)\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def cmd_xoacode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    if not context.args: return
    target_code = " ".join(context.args).strip()
    for key in db["codes"].keys():
        if target_code in db["codes"][key]:
            db["codes"][key].remove(target_code)
            save_data(db)
            await update.message.reply_text(f"✅ Đã xoá mã code khỏi kho *{PRODUCTS[key]['game']}*.", parse_mode="Markdown")
            return
    await update.message.reply_text("❌ Không tìm thấy mã code.")

async def cmd_slcode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    msg = "📋 *DANH SÁCH CHI TIẾT CODE TỒN KHO*\n───────────────────\n"
    for key, prod in PRODUCTS.items():
        code_list = db["codes"].get(key, [])
        msg += f"🎮 *{prod['game']} ({prod['points']})* (Còn: `{len(code_list)}`):\n"
        if code_list:
            for idx, c in enumerate(code_list, start=1): msg += f"  `{idx}.` `{c}`\n"
        else: msg += "  _(Kho trống)_\n"
    if len(msg) > 4000:
        for chunk in [msg[i:i+4000] for i in range(0, len(msg), 4000)]: await update.message.reply_text(chunk, parse_mode="Markdown")
    else: await update.message.reply_text(msg, parse_mode="Markdown")

async def cmd_themcode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    if len(context.args) < 2: return
    prod_key = context.args[0].lower()
    code_val = " ".join(context.args[1:])
    if prod_key not in PRODUCTS: return
    db["codes"][prod_key].append(code_val)
    save_data(db)
    await update.message.reply_text(f"✅ Đã thêm vào kho. Hiện tại còn: `{len(db['codes'][prod_key])}`.", parse_mode="Markdown")

async def cmd_tong(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    await update.message.reply_text(f"📊 *Tổng người dùng:* `{len(db['users'])}` thành viên.", parse_mode="Markdown")

async def cmd_nap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    if len(context.args) < 2: return
    target_uid = context.args[0]
    try: amount = int(context.args[1])
    except ValueError: return
    if target_uid not in db["users"]: return
    db["users"][target_uid]["balance"] += amount
    save_data(db)
    await update.message.reply_text(f"✅ Đã cộng `+{amount:,} VNĐ` cho `{target_uid}`", parse_mode="Markdown")
    try: await context.bot.send_message(chat_id=int(target_uid), text=f"🔔 Tài khoản được cộng `+{amount:,} VNĐ` từ Admin.", parse_mode="Markdown")
    except Exception: pass

async def cmd_thongbao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    if not context.args: return
    announcement = "📢 *THÔNG BÁO TỪ ADMIN*\n" + " ".join(context.args)
    count = 0
    for uid in db["users"].keys():
        try:
            await context.bot.send_message(chat_id=int(uid), text=announcement, parse_mode="Markdown")
            count += 1
            await asyncio.sleep(0.05)
        except Exception: pass
    await update.message.reply_text(f"📢 Đã gửi thông báo đến {count}/{len(db['users'])} người dùng!", parse_mode="Markdown")

# --- HÀM CHẠY BOT CHÍNH ---
def main():
    # Cập nhật token bot chính xác theo yêu cầu
    TOKEN = "8960587351:AAEe0E5gUXYoZ_G864q4ek7Duu4S3foD07g"
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("themcode", cmd_themcode))
    application.add_handler(CommandHandler("themcodesll", cmd_themcodesll))
    application.add_handler(CommandHandler("themcodesll1", cmd_themcodesll1))
    application.add_handler(CommandHandler("baotri", cmd_baotri))
    application.add_handler(CommandHandler("xoacode", cmd_xoacode))
    application.add_handler(CommandHandler("slcode", cmd_slcode))
    application.add_handler(CommandHandler("tong", cmd_tong))
    application.add_handler(CommandHandler("nap", cmd_nap))
    application.add_handler(CommandHandler("thongbao", cmd_thongbao))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    logging.info("Bot đang chạy...")
    application.run_polling()

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: logging.info("Bot đã dừng.")
    except Exception as e:
        logging.error(f"Lỗi: {e}")
        sys.exit(1)
