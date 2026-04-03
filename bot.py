import os
import asyncio
import logging
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Переменные окружения
TOKEN = os.environ["BOT_TOKEN"]
URL = os.environ.get("RENDER_EXTERNAL_URL")  # Render подставляет сам!
PORT = int(os.getenv("PORT", 8000))

# --- Обработчики команд (ваши старые обработчики вставьте сюда) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Бот работает на Render.com 🎉")

# --- Главная функция ---
async def main():
    # Создаем приложение бота
    app = Application.builder().token(TOKEN).updater(None).build()
    app.add_handler(CommandHandler("start", start))
    # СЮДА ДОБАВЬТЕ ВСЕ ВАШИ ОСТАЛЬНЫЕ ОБРАБОТЧИКИ
    
    # Устанавливаем webhook (это важно для бесплатного тарифа!)
    await app.bot.set_webhook(url=f"{URL}/telegram", allowed_updates=Update.ALL_TYPES)
    logger.info(f"Webhook установлен на {URL}/telegram")
    
    # Создаем веб-сервер для health check
    async def telegram(request: Request) -> Response:
        await app.update_queue.put(Update.de_json(await request.json(), app.bot))
        return Response()
    
    async def health(_: Request) -> PlainTextResponse:
        return PlainTextResponse("OK")
    
    starlette_app = Starlette(routes=[
        Route("/telegram", telegram, methods=["POST"]),
        Route("/healthcheck", health, methods=["GET"]),
    ])
    
    # Запускаем сервер
    import uvicorn
    server = uvicorn.Server(uvicorn.Config(starlette_app, host="0.0.0.0", port=PORT))
    async with app:
        await app.start()
        await server.serve()
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main())