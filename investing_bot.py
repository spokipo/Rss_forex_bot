import os
import asyncio
import feedparser
from telegram import Bot
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# === Конфигурация ===
RSS_URL = "https://ru.investing.com/rss/news_25.rss"
CHECK_INTERVAL = 60  # Проверка каждые 60 сек
LAST_LINK_FILE = "last_link.txt"

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
THREAD_ID = os.getenv("MESSAGE_THREAD_ID")

bot = Bot(token=BOT_TOKEN)
first_run = True

# === Работа с файлом ссылки ===
def load_last_link():
    if os.path.exists(LAST_LINK_FILE):
        with open(LAST_LINK_FILE, "r") as f:
            return f.read().strip()
    return None

def save_last_link(link):
    with open(LAST_LINK_FILE, "w") as f:
        f.write(link)

last_sent_link = load_last_link()

# === Отправка новостей ===
async def send_news(entries):
    global last_sent_link, first_run

    entries = list(reversed(entries))

    for entry in entries:
        title = entry.get("title")
        link = entry.get("link")

        if not link or link == last_sent_link:
            continue

        msg = f"📰 <b>{title}</b>\n{link}"
        try:
            await bot.send_message(
                chat_id=CHAT_ID,
                text=msg,
                parse_mode="HTML",
                message_thread_id=int(THREAD_ID) if THREAD_ID else None
            )
            last_sent_link = link
            save_last_link(link)
            await asyncio.sleep(1)
        except Exception as e:
            print("❌ Ошибка отправки:", e)

        if first_run:
            break

    first_run = False

# === Основной цикл ===
async def main():
    try:
        await bot.send_message(
            chat_id=CHAT_ID,
            text="✅ Бот запущен и следит за Investing.com (Forex)",
            parse_mode="HTML",
            message_thread_id=int(THREAD_ID) if THREAD_ID else None
        )
    except Exception as e:
        print("❌ Ошибка запуска бота:", e)

    while True:
        try:
            print("📡 Проверка ленты...")
            feed = feedparser.parse(RSS_URL)
            await send_news(feed.entries)
        except Exception as e:
            print("❌ Ошибка чтения RSS:", e)
        await asyncio.sleep(CHECK_INTERVAL)

# === HTTP для Render ===
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
