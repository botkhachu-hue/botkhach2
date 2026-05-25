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
ADMIN_IDS = [8789260361, 8619503816]

# Cấu hình danh mục sản phẩm
PRODUCTS = {
    "fly88": {"name": "Fly88 (79 điểm)", "price": 25000, "price_str": "25K"},
    "f168": {"name": "F168 (188 điểm)", "price": 79000, "price_str": "79K"},
    "new88": {"name": "New88 (188 điểm)", "price": 79000, "price_str": "79K"},
    "qq88": {"name": "QQ88 (108 điểm)", "price": 40000, "price_str": "40K"},
    "shbet": {"name": "Shbet (139 điểm)", "price": 50000, "price_str": "50K"}
}

# Khởi tạo hoặc đọc dữ liệu từ file JSON
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logging.error("File dữ liệu bị lỗi định dạng, đang khởi tạo lại!")
    return {
        "users": {},
        "codes": {key: [] for key in PRODUCTS.keys()}
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
        ["📈 SỐ LƯỢNG CODE"]
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
        msg = (
            "🏦 *HỆ THỐNG NẠP TIỀN TỰ ĐỘNG*\n"
            "───────────────────\n"
            "📌 *Ngân hàng:* VPBANK\n"
            "📌 *Số tài khoản:* `95533356868`\n"
            "📌 *Chủ tài khoản:* LE TUAN BAO\n"
            f"📌 *Nội dung chuyển khoản:* `{user_id}`\n"
            "───────────────────\n"
            "⚠️ *Lưu ý:* Vui lòng nhập đúng ID tài khoản trong nội dung chuyển khoản để hệ thống cộng tiền chính xác."
        )
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
        for key, prod in PRODUCTS.items():
            count = len(db["codes"].get(key, []))
            keyboard.append([InlineKeyboardButton(f"🎁 {prod['name']} - {prod['price_str']} (Còn: {count})", callback_data=f"prod_{key}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🛒 *DANH SÁCH CODE ĐANG CÓ SẴN:*", parse_mode="Markdown", reply_markup=reply_markup)

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
            msg += f"🎁 *{prod['name']}:* Còn `{count}` code\n"
        msg += "───────────────────"
        await update.message.reply_text(msg, parse_mode="Markdown")

# --- XỬ LÝ MUA HÀNG & CHECK KHO ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    uid = str(user_id)
    data = query.data

    if data.startswith("prod_"):
        prod_key = data.split("_")[1]
        prod = PRODUCTS[prod_key]
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Xác Nhận Mua", callback_data=f"confirm_{prod_key}"),
                InlineKeyboardButton("❌ Hủy Bỏ", callback_data="cancel_buy")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=f"❓ *Xác nhận mua:* {prod['name']}\n💰 *Giá tiền:* `{prod['price_str']}` ({prod['price']:,} VNĐ)?",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
    elif data.startswith("confirm_"):
        prod_key = data.split("_")[1]
        prod = PRODUCTS[prod_key]
        u_info = db["users"].get(uid)
        
        if not u_info:
            await query.edit_message_text("❌ Lỗi dữ liệu người dùng.")
            return

        # Kiểm tra kho code
        if not db["codes"].get(prod_key):
            suggest_keyboard = []
            for key, p_item in PRODUCTS.items():
                p_count = len(db["codes"].get(key, []))
                if p_count > 0:  
                    suggest_keyboard.append([InlineKeyboardButton(f"🎁 {p_item['name']} (Còn: {p_count})", callback_data=f"prod_{key}")])
            
            error_msg = (
                f"😭 *Rất tiếc! Loại code {prod['name']} hiện tại vừa cháy hàng.*\n"
                f"📩 Hệ thống đang tự động cập nhật và bổ sung code mới sớm nhất.\n\n"
                f"👇 Trong lúc chờ đợi, bạn có thể tham khảo mua các loại code đang *SẴN HÀNG* dưới đây nhé:"
            )
            
            if suggest_keyboard:
                await query.edit_message_text(text=error_msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(suggest_keyboard))
            else:
                await query.edit_message_text(text=f"❌ *Hệ thống không còn code, vui lòng liên hệ Admin để nạp thêm.*", parse_mode="Markdown")
            return

        # Kiểm tra số dư tài khoản
        if u_info["balance"] < prod["price"]:
            await query.edit_message_text(
                text=f"❌ *Giao dịch thất bại:*\nSố dư tài khoản của bạn (`{u_info['balance']:,} VNĐ`) không đủ để thanh toán mặt hàng *{prod['name']}* (`{prod['price']:,} VNĐ`). Vui lòng thực hiện nạp thêm!",
                parse_mode="Markdown"
            )
            return
            
        # Trừ tiền và xuất code
        u_info["balance"] -= prod["price"]
        code_bought = db["codes"][prod_key].pop(0)  
        
        time_now = datetime.now().strftime("%d/%m %H:%M")
        u_info["history"].append(f"[{time_now}] Mua {prod['name']} (-{prod['price_str']})")
        save_data(db)
        
        success_msg = (
            "🎉 *MUA HÀNG THÀNH CÔNG!* 🎉\n"
            "───────────────────\n"
            f"📦 *Sản phẩm:* {prod['name']}\n"
            f"🔑 *Mã Code của bạn:* `{code_bought}`\n"
            f"💰 *Số dư ví hiện tại:* `{u_info['balance']:,} VNĐ`\n"
            "───────────────────\n"
            "✨ Cảm ơn bạn rất nhiều! Nhấp và đè vào mã code ở trên để copy nhanh nhé."
        )
        await query.edit_message_text(text=success_msg, parse_mode="Markdown")
        
    elif data == "cancel_buy":
        await query.edit_message_text("❌ *Đã hủy giao dịch mua hàng.*")

# --- QUYỀN HẠN ADMIN ---
async def cmd_themcode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Cú pháp: `/themcode [tên_loại] [mã_code]`", parse_mode="Markdown")
        return
    prod_key = context.args[0].lower()
    code_val = " ".join(context.args[1:])
    if prod_key not in PRODUCTS:
        await update.message.reply_text("❌ Loại sản phẩm sai! Các loại: fly88, f168, new88, qq88, shbet", parse_mode="Markdown")
        return
    db["codes"][prod_key].append(code_val)
    save_data(db)
    await update.message.reply_text(f"✅ Thêm thành công vào kho `{prod_key}`. Hiện có: `{len(db['codes'][prod_key])}` code.", parse_mode="Markdown")

async def cmd_tong(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    await update.message.reply_text(f"📊 *Tổng người dùng:* `{len(db['users'])}` thành viên.", parse_mode="Markdown")

async def cmd_nap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Cú pháp: `/nap [id] [số_tiền]`", parse_mode="Markdown")
        return
    target_uid = context.args[0]
    try:
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Số tiền không hợp lệ!")
        return
    if target_uid not in db["users"]:
        await update.message.reply_text("❌ Không tìm thấy người dùng này.")
        return
    db["users"][target_uid]["balance"] += amount
    save_data(db)
    await update.message.reply_text(f"✅ Nạp thành công cho `{target_uid}` số tiền `+{amount:,} VNĐ`", parse_mode="Markdown")
    try:
        await context.bot.send_message(chat_id=int(target_uid), text=f"🔔 Tài khoản được cộng `+{amount:,} VNĐ` từ Admin.", parse_mode="Markdown")
    except Exception:
        pass

async def cmd_thongbao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("⚠️ Cú pháp: `/thongbao [nội dung]`", parse_mode="Markdown")
        return
    announcement = "📢 *THÔNG BÁO TỪ ADMIN*\n" + " ".join(context.args)
    count = 0
    for uid in db["users"].keys():
        try:
            await context.bot.send_message(chat_id=int(uid), text=announcement, parse_mode="Markdown")
            count += 1
            await asyncio.sleep(0.05)  # Tránh rate limit
        except Exception:
            pass
    await update.message.reply_text(f"📢 Đã gửi thông báo đến {count}/{len(db['users'])} người dùng!", parse_mode="Markdown")

# --- HÀM CHẠY BOT CHÍNH ---
def main():
    TOKEN = "8610843811:AAHIaWRgc1A1CSyTivsDXXy6z0Usy_B6NR4"
    
    # Khởi tạo application đúng cách
    application = Application.builder().token(TOKEN).build()
    
    # Thêm các handlers xử lý
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(CommandHandler("themcode", cmd_themcode))
    application.add_handler(CommandHandler("tong", cmd_tong))
    application.add_handler(CommandHandler("nap", cmd_nap))
    application.add_handler(CommandHandler("thongbao", cmd_thongbao))
    
    logging.info("Bot đang khởi động bằng run_polling()...")
    
    # Sử dụng hàm chuẩn run_polling để tự động quản lý vòng lặp sự kiện, tránh lỗi dọn dẹp cache trên server
    application.run_polling()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Bot đã dừng.")
    except Exception as e:
        logging.error(f"Lỗi nghiêm trọng hệ thống: {e}")
        sys.exit(1)
