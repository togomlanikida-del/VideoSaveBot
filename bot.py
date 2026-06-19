import asyncio
import json
import os
import subprocess
from pathlib import Path

import yt_dlp
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, FSInputFile, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv


ADMIN_ID = 6225032098
STATS_FILE = "stats.json"
DOWNLOAD_DIR = Path("downloads")
SUPPORTED_DOMAINS = ("youtube.com", "youtu.be", "tiktok.com", "instagram.com")

waiting_broadcast: set[int] = set()

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi")

bot = Bot(token=TOKEN)
dp = Dispatcher()


def load_stats() -> dict:
    if not os.path.exists(STATS_FILE):
        return {"users": [], "videos": 0}

    try:
        with open(STATS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            data.setdefault("users", [])
            data.setdefault("videos", 0)
            return data
    except (json.JSONDecodeError, OSError):
        return {"users": [], "videos": 0}


def save_stats(stats: dict) -> None:
    with open(STATS_FILE, "w", encoding="utf-8") as file:
        json.dump(stats, file, ensure_ascii=False, indent=2)


def register_user(user_id: int) -> None:
    stats = load_stats()
    if user_id not in stats["users"]:
        stats["users"].append(user_id)
        save_stats(stats)


def add_video_stat(user_id: int) -> None:
    stats = load_stats()
    if user_id not in stats["users"]:
        stats["users"].append(user_id)
    stats["videos"] += 1
    save_stats(stats)


def clean_downloads_folder() -> int:
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    deleted = 0

    for file_path in DOWNLOAD_DIR.iterdir():
        if file_path.is_file():
            try:
                file_path.unlink()
                deleted += 1
            except OSError:
                pass

    return deleted


def download_video(url: str) -> str:
    DOWNLOAD_DIR.mkdir(exist_ok=True)

    ydl_opts = {
        "outtmpl": str(DOWNLOAD_DIR / "%(id)s.%(ext)s"),
        "format": "best[ext=mp4][height<=720]/best[ext=mp4]/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "retries": 2,
        "fragment_retries": 2,
        "extractor_retries": 2,
        "socket_timeout": 15,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/120 Safari/537.36"
            )
        },
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)


def extract_audio(video_path: str) -> str:
    audio_path = os.path.splitext(video_path)[0] + ".mp3"

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-vn",
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "2",
            audio_path,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return audio_path


@dp.message(CommandStart())
async def start(message: Message) -> None:
    register_user(message.from_user.id)
    await message.answer(
        "📥 Assalomu alaykum!\n\n"
        "Instagram, TikTok yoki YouTube link yuboring."
    )


@dp.message(Command("id"))
async def get_my_id(message: Message) -> None:
    await message.answer(f"🆔 Sizning Telegram ID: {message.from_user.id}")


@dp.message(Command("stats"))
async def stats_command(message: Message) -> None:
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Ruxsat yo‘q")
        return

    stats = load_stats()
    await message.answer(
        "📊 Statistika\n\n"
        f"👥 Foydalanuvchilar: {len(stats['users'])}\n"
        f"🎬 Yuklangan videolar: {stats['videos']}"
    )


@dp.message(Command("clean"))
async def clean_command(message: Message) -> None:
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Ruxsat yo‘q")
        return

    deleted = clean_downloads_folder()
    await message.answer(f"🧹 Tozalandi: {deleted} ta fayl")


@dp.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Ruxsat yo‘q")
        return

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="📊 Statistika", callback_data="admin_stats")
    keyboard.button(text="📢 Broadcast", callback_data="admin_broadcast")
    keyboard.button(text="🧹 Tozalash", callback_data="admin_clean")
    keyboard.adjust(1)

    await message.answer("⚙️ Admin panel", reply_markup=keyboard.as_markup())


@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery) -> None:
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Ruxsat yo‘q")
        return

    stats = load_stats()
    await callback.message.answer(
        "📊 Statistika\n\n"
        f"👥 Foydalanuvchilar: {len(stats['users'])}\n"
        f"🎬 Yuklangan videolar: {stats['videos']}"
    )
    await callback.answer()


@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery) -> None:
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Ruxsat yo‘q")
        return

    waiting_broadcast.add(callback.from_user.id)
    await callback.message.answer(
        "📢 Xabarni yozing. Bekor qilish uchun /cancel yuboring."
    )
    await callback.answer()


@dp.callback_query(F.data == "admin_clean")
async def admin_clean(callback: CallbackQuery) -> None:
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Ruxsat yo‘q")
        return

    deleted = clean_downloads_folder()
    await callback.message.answer(f"🧹 Tozalandi: {deleted} ta fayl")
    await callback.answer()


async def send_broadcast(message: Message, text: str) -> None:
    users = load_stats().get("users", [])
    sent = 0
    failed = 0

    status = await message.answer(
        f"⏳ Xabar {len(users)} ta foydalanuvchiga yuborilmoqda..."
    )

    for user_id in users:
        try:
            await bot.send_message(user_id, text)
            sent += 1
        except Exception:
            failed += 1

        await asyncio.sleep(0.05)

    await status.edit_text(
        "✅ Broadcast tugadi!\n\n"
        f"📨 Yuborildi: {sent}\n"
        f"❌ Yuborilmadi: {failed}"
    )


@dp.message(Command("broadcast"))
async def broadcast_command(message: Message) -> None:
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Ruxsat yo‘q")
        return

    text = message.text.partition(" ")[2].strip()
    if not text:
        await message.answer("/broadcast dan keyin xabar yozing.")
        return

    await send_broadcast(message, text)


@dp.message()
async def get_link(message: Message) -> None:
    if not message.text:
        return

    if message.from_user.id in waiting_broadcast:
        if message.text == "/cancel":
            waiting_broadcast.discard(message.from_user.id)
            await message.answer("❌ Broadcast bekor qilindi.")
            return

        waiting_broadcast.discard(message.from_user.id)
        await send_broadcast(message, message.text)
        return

    url = message.text.strip()

    if not any(domain in url for domain in SUPPORTED_DOMAINS):
        await message.answer(
            "❌ Instagram, TikTok yoki YouTube link yuboring."
        )
        return

    register_user(message.from_user.id)
    status = await message.answer("⏳ Video yuklanmoqda...")
    file_path: str | None = None
    audio_path: str | None = None

    try:
        file_path = await asyncio.to_thread(download_video, url)

        await message.answer_video(
            video=FSInputFile(file_path),
            caption="✅ Video tayyor",
        )

        audio_path = await asyncio.to_thread(extract_audio, file_path)

        await message.answer_audio(
            audio=FSInputFile(audio_path),
            caption="🎵 Video musiqasi",
        )

        add_video_stat(message.from_user.id)
        await status.delete()

    except Exception as error:
        error_text = str(error)
        print(f"DOWNLOAD ERROR: {error_text}", flush=True)

        if "Sign in to confirm" in error_text:
            await status.edit_text(
                "❌ YouTube bu videoni tekshiruvga qo‘ygan. Boshqa video yuboring."
            )
        elif (
            "10054" in error_text
            or "Unable to download webpage" in error_text
            or "handshake operation timed out" in error_text
        ):
            await status.edit_text(
                "❌ Bu video hozir yuklanmadi. Boshqa link yuboring."
            )
        else:
            await status.edit_text(
                "❌ Video yoki audio tayyorlab bo‘lmadi. Boshqa link yuboring."
            )

    finally:
        for path in (audio_path, file_path):
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass


async def main() -> None:
    await bot.delete_webhook(drop_pending_updates=True)

    bot_info = await bot.get_me()
    print(f"Bot ishga tushdi: @{bot_info.username}", flush=True)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
