import os
import asyncio
import feedparser
import httpx
from telegram import Bot
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# === Настройки ===
RSS_URL = "https://www.fxstreet.com/rss/news"
TRANSLATE_API = "https://libretranslate.de/translate"  # Бесплатный, публичный
CHECK_INTERVAL = 60

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
THREAD_ID = os.getenv("MESSAGE_THREAD_ID")  # Может быть None

bot = Bot(token=BOT_TOKEN)
sent_links = set()
first_run = True

# === Переводчик ===
async def translate(text, to_lang="ru"):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(TRANSLATE_API, data={
                "q": text,
                "source": "en",
                "target": to_lang,
                "format": "text"
            }, timeout=10)
            resp.raise_for_status()
            return resp.json()["translatedText"]
    except Exception as e:
        print("Ошибка перевода:", e)
        return text

# === Отправка сообщений ===
async def send_news(entries):
    global first_run
    entries = list(reversed(entries))  # Старые сначала

    for entry in entries:
        title = entry.get("title", "")
        link = entry.get("link", "")

        if not link or link in sent_links:
            continue

        translated_title = await translate(title)
        message = f"📰 <b>{translated_title}</b>\n🌍 {link}"

        try:
            await bot.send_message(
                chat_id=CHAT_ID,
                text=message,
                parse_mode="HTML",
                message_thread_id=int(THREAD_ID) if THREAD_ID else None
            )
            sent_links.add(link)
            await asyncio.sleep(1)
        except Exception as e:
            print("Ошибка отправки в Telegram:", e)

        if first_run:
            break  # Только одну новость при старте

    first_run = False

# === Основной цикл ===
async def main():
    try:
        await bot.send_message(
            chat_id=CHAT_ID,
            text="✅ Бот запущен и отслеживает новости FXStreet",
            parse_mode="HTML",
            message_thread_id=int(THREAD_ID) if THREAD_ID else None
        )
    except Exception as e:
        print("Ошибка при запуске бота:", e)

    while True:
        try:
            print("📡 Проверка RSS-ленты...")
            feed = feedparser.parse(RSS_URL)
            await send_news(feed.entries)
        except Exception as e:
            print("❌ Ошибка загрузки RSS:", e)
        await asyncio.sleep(CHECK_INTERVAL)

# === HTTP-сервер для Render ===
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running.")

def run_http_server():
    server = HTTPServer(('0.0.0.0', 10000), DummyHandler)
    print("🌐 HTTP-сервер запущен на порту 10000")
    server.serve_forever()

# === Запуск ===
if __name__ == "__main__":
    threading.Thread(target=run_http_server, daemon=True).start()
    asyncio.run(main())
