from aiogram import Bot, Dispatcher
from aiogram import F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
import asyncio
import yt_dlp
import os
from dotenv import load_dotenv
import json
from aiogram.types import Message, FSInputFile, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
STATS_FILE = "stats.json"
waiting_broadcast = set()

def load_stats():
    if not os.path.exists(STATS_FILE):
        return {"users": [], "videos": 0}

    with open(STATS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_stats(stats):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=4)

def add_video_stat(user_id):
    stats = load_stats()

    if user_id not in stats["users"]:
        stats["users"].append(user_id)

    stats["videos"] += 1
    save_stats(stats)
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "📥 Assalomu alaykum!\n\nInstagram, TikTok yoki YouTube link yuboring."
    )
@dp.message(Command("clean"))
async def clean_downloads(message: Message):
    if message.from_user.id != 6225032098:
        await message.answer("⛔ Ruxsat yo'q")
        return
    deleted = 0

    if os.path.exists("downloads"):
        for file in os.listdir("downloads"):
            file_path = os.path.join("downloads", file)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    deleted += 1
                except:
                    pass

    await message.answer(f"🧹 Tozalandi: {deleted} ta fayl")

@dp.message(Command("stats"))
async def stats(message: Message):
    if message.from_user.id != 6225032098:
        await message.answer("⛔ Ruxsat yo'q")
        return

    stats_data = load_stats()

    await message.answer(
        "📊 Statistika\n\n"
        f"👥 Foydalanuvchilar: {len(stats_data['users'])}\n"
        f"🎬 Yuklangan videolar: {stats_data['videos']}"
    )

@dp.message(Command("id"))
async def get_my_id(message: Message):
    await message.answer(f"🆔 Sizning Telegram ID: {message.from_user.id}")

@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != 6225032098:
        await message.answer("⛔ Ruxsat yo'q")
        return

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="📊 Statistika", callback_data="admin_stats")
    keyboard.button(text="📢 Broadcast", callback_data="admin_broadcast")
    keyboard.button(text="🧹 Tozalash", callback_data="admin_clean")
    keyboard.adjust(1)

    await message.answer(
        "🎛 Admin panel",
        reply_markup=keyboard.as_markup()
)

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_button(callback: CallbackQuery):
    if callback.from_user.id != 6225032098:
        await callback.answer("⛔ Ruxsat yo‘q")
        return

    waiting_broadcast.add(callback.from_user.id)

    await callback.message.answer(
        "📢 Barcha foydalanuvchilarga yuboriladigan xabarni yozing.\n\n"
        "Bekor qilish uchun /cancel yuboring."
    )

    await callback.answer()
@dp.message(Command("broadcast"))
async def broadcast_message(message: Message):
    if message.from_user.id != 6225032098:
        await message.answer("⛔ Ruxsat yo‘q")
        return

    broadcast_text = message.text.partition(" ")[2].strip()

    if not broadcast_text:
        await message.answer(
            "📢 Xabarni mana bunday yuboring:\n\n"
            "/broadcast Assalomu alaykum! Bot yangilandi."
        )
        return

    stats_data = load_stats()
    users = stats_data.get("users", [])

    sent = 0
    failed = 0

    status = await message.answer(
        f"⏳ Xabar {len(users)} ta foydalanuvchiga yuborilmoqda..."
    )

    for user_id in users:
        try:
            await bot.send_message(user_id, broadcast_text)
            sent += 1
        except Exception:
            failed += 1

        await asyncio.sleep(0.05)

    await status.edit_text(
        "✅ Broadcast tugadi!\n\n"
        f"📨 Yuborildi: {sent}\n"
        f"❌ Yuborilmadi: {failed}"
    )
@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_button(callback: CallbackQuery):
    if callback.from_user.id != 6225032098:
        await callback.answer("⛔ Ruxsat yo‘q")
        return

    await callback.message.answer(
        "📢 Broadcast xabarini mana bunday yuboring:\n\n"
        "/broadcast Assalomu alaykum! Bot yangilandi 🚀"
    )

    await callback.answer()


@dp.callback_query(F.data == "admin_clean")
async def admin_clean(callback: CallbackQuery):
    if callback.from_user.id != 6225032098:
        await callback.answer("⛔ Ruxsat yo‘q")
        return

    deleted = 0

    if os.path.exists("downloads"):
        for file in os.listdir("downloads"):
            file_path = os.path.join("downloads", file)

            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    deleted += 1
                except Exception:
                    pass

    await callback.message.answer(
        f"🧹 Tozalandi: {deleted} ta fayl"
    )
    await callback.answer()

    @dp.message()
    async def get_link(message: Message):
        if message.from_user.id in waiting_broadcast:
            if message.text == "/cancel":
                waiting_broadcast.discard(message.from_user.id)
            await message.answer("❌ Broadcast bekor qilindi.")
            return

        stats_data = load_stats()
        users = stats_data.get("users", [])

        sent = 0
        failed = 0

        status = await message.answer(
            f"⏳ Xabar {len(users)} ta foydalanuvchiga yuborilmoqda..."
        )

        for user_id in users:
            try:
                await bot.send_message(user_id, message.text)
                sent += 1
            except Exception:
                failed += 1

            await asyncio.sleep(0.05)

        waiting_broadcast.discard(message.from_user.id)

        await status.edit_text(
            "✅ Broadcast tugadi!\n\n"
            f"📨 Yuborildi: {sent}\n"
            f"❌ Yuborilmadi: {failed}"
        )
        return
    url = message.text.strip()
    file_path = None

    if not any(x in url for x in ["youtube.com", "youtu.be", "tiktok.com", "instagram.com"]):
        await message.answer("❌ Instagram, TikTok yoki YouTube link yuboring")
        return

    status = await message.answer("⏳ Video yuklanmoqda...")

    try:
        os.makedirs("downloads", exist_ok=True)

        ydl_opts = {
            "outtmpl": "downloads/%(id)s.%(ext)s",
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "merge_output_format": "mp4",
            "noplaylist": True,
            "quiet": True,
            "retries": 2,
            "fragment_retries": 2,
            "extractor_retries": 2,
            "socket_timeout": 8,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
            },
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        await message.answer_video(
            FSInputFile(file_path),
            caption="✅ Video tayyor"
        )

        add_video_stat(message.from_user.id)
        await status.delete()
        await asyncio.sleep(3)

    except Exception as e:
        error = str(e)

        if "10054" in error or "Unable to download webpage" in error or "handshake operation timed out" in error:
            await status.edit_text("❌ Bu video hozir yuklanmadi. Boshqa link yuboring.")
        elif "Sign in to confirm" in error:
            await status.edit_text("❌ YouTube bu videoni tekshiruvga qo‘ygan. Boshqa video yuboring.")
        else:
            await status.edit_text("❌ Video yuklab bo‘lmadi. Boshqa link yuboring.")

    finally:
        if file_path and os.path.exists(file_path):
            await asyncio.sleep(10)
            for _ in range(30):
                try:
                    os.remove(file_path)
                    break
                except PermissionError:
                    await asyncio.sleep(1)


async def main():
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
        
        