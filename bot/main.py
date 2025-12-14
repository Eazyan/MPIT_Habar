import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.types import WebAppInfo
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
# In production, this should be the HTTPS URL of your deployed frontend
# For local dev with ngrok, use the ngrok URL. For docker-compose, it's tricky without https.
# We will use a placeholder or localhost for now, but Telegram Web Apps require HTTPS.
# For local testing on Desktop, http://localhost:3000 works.
# For mobile, you need https (e.g., via ngrok).
WEB_APP_URL = os.getenv("WEB_APP_URL", "http://localhost:3000") 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

import redis.asyncio as redis
import json

import httpx

# Redis connection
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Extract args (e.g., /start 123456)
    args = message.text.split()
    token = args[1] if len(args) > 1 else None
    
    if token:
        # Call Backend to verify and link
        await message.answer(f"🔗 Проверяю код {token}...")
        
        try:
            # Use internal docker dns "backend"
            # Note: Ensure "backend" is reachable. In docker-compose it is.
            # If running bot locally output of docker, this will fail unless mapped to localhost.
            # But the bot is in docker.
            backend_url = "http://backend:8000" 
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{backend_url}/auth/telegram/link",
                    json={"token": token, "telegram_chat_id": str(message.chat.id)},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    email = data.get("user_email", "User")
                    await message.answer(f"✅ **Успешно!**\nАккаунт **{email}** привязан.\nТеперь я буду присылать уведомления о генерациях сюда.")
                else:
                    error_detail = response.json().get("detail", "Unknown error")
                    await message.answer(f"❌ Ошибка связки: {error_detail}")
                    
        except Exception as e:
            await message.answer(f"❌ Ошибка соединения с сервером: {str(e)}")
            
    else:
        await message.answer(
            "Привет! Я AI-Newsmaker Bot. 🤖\n\n"
            "Я буду присылать уведомления о готовых постах.\n"
            "Чтобы связать меня с аккаунтом, нажми кнопку 'Подключить Telegram' в личном кабинете на сайте."
        )

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

@dp.message(Command("config"))
async def cmd_config(message: types.Message):
    chat_id = message.chat.id
    # Load current config
    model = await redis_client.get(f"user_config:{chat_id}:model") or "claude"
    mode = await redis_client.get(f"user_config:{chat_id}:mode") or "pr"
    
    if isinstance(model, bytes): model = model.decode()
    if isinstance(mode, bytes): mode = mode.decode()
    
    # Text
    text = (
        f"⚙️ **Настройки Генерации**\n\n"
        f"🧠 **Модель:** {model.upper()}\n"
        f"🎭 **Режим:** {mode.upper()}"
    )
    
    # Keyboard
    btn_model = InlineKeyboardButton(text="🔄 Сменить Модель", callback_data=f"set_model:{'qwen' if model=='claude' else 'claude'}")
    btn_mode = InlineKeyboardButton(text="🔄 Сменить Режим", callback_data=f"set_mode:{'blogger' if mode=='pr' else 'pr'}")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[btn_model], [btn_mode]])
    
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("set_"))
async def process_callback(callback: CallbackQuery):
    action, value = callback.data.split(":")
    chat_id = callback.message.chat.id
    
    if action == "set_model":
        await redis_client.set(f"user_config:{chat_id}:model", value)
    elif action == "set_mode":
        await redis_client.set(f"user_config:{chat_id}:mode", value)
        
    # Refresh Message
    await callback.answer("Настройки обновлены")
    
    # Get new state to render
    model = await redis_client.get(f"user_config:{chat_id}:model") or "claude"
    mode = await redis_client.get(f"user_config:{chat_id}:mode") or "pr"
    
    if isinstance(model, bytes): model = model.decode()
    if isinstance(mode, bytes): mode = mode.decode()

    text = (
        f"⚙️ **Настройки Генерации**\n\n"
        f"🧠 **Модель:** {model.upper()}\n"
        f"🎭 **Режим:** {mode.upper()}"
    )
    
    # Update buttons for next toggle
    next_model = 'qwen' if model == 'claude' else 'claude'
    next_mode = 'blogger' if mode == 'pr' else 'pr'
    
    btn_model = InlineKeyboardButton(text="🔄 Сменить Модель", callback_data=f"set_model:{next_model}")
    btn_mode = InlineKeyboardButton(text="🔄 Сменить Режим", callback_data=f"set_mode:{next_mode}")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[btn_model], [btn_mode]])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@dp.message(F.text)
async def handle_text(message: types.Message):
    # Lite Generation Mode: If text is URL
    if message.text and (message.text.startswith("http://") or message.text.startswith("https://")):
        url = message.text.strip()
        
        # Get Config
        chat_id = message.chat.id
        model = await redis_client.get(f"user_config:{chat_id}:model") or "claude"
        mode = await redis_client.get(f"user_config:{chat_id}:mode") or "pr"
        
        if isinstance(model, bytes): model = model.decode()
        if isinstance(mode, bytes): mode = mode.decode()

        await message.answer(f"🔎 Принял ссылку! \n⚙️ {model.upper()} | {mode.upper()}\nЗапускаю анализ...")
        
        try:
            backend_url = "http://backend:8000"
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{backend_url}/bot/generate",
                    json={
                        "url": url, 
                        "telegram_chat_id": str(chat_id),
                        "model_provider": model,
                        "mode": mode
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    await message.answer(f"🚀 Задача создана! (ID: {data['task_id'][:8]})\nЯ пришлю уведомление, когда все будет готово.")
                elif response.status_code == 404:
                    await message.answer("⚠️ Ваш Telegram не привязан к аккаунту.\nИспользуйте кнопку 'Link TG' на сайте.")
                else:
                    error = response.json().get("detail", "Unknown error")
                    await message.answer(f"❌ Ошибка: {error}")
                    
        except Exception as e:
            await message.answer(f"❌ Ошибка соединения: {str(e)}")
            
    else:
        # Just chat / instructions
        await message.answer(
            "Отправь мне ссылку на новость, и я сгенерирую PR-стратегию! ⚡\n\n"
            "Настройки: /config\n"
            "(Убедись, что аккаунт привязан)"
        )

async def notification_worker(bot: Bot):
    """Listens for Redis events and sends notifications."""
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("task_updates")
    
    print("🔔 Notification worker started...")
    
    async for message in pubsub.listen():
        if message["type"] == "message":
            try:
                data = json.loads(message["data"])
                # Use linked chat_id if available
                chat_id = data.get("telegram_chat_id")
                
                if chat_id:
                    chat_id = int(chat_id) # Ensure chat_id is an integer
                    msg_type = data.get("type")
                    status = data.get("status")
                    
                    # Handle PUBLISH messages
                    if msg_type == "publish":
                        content = data.get("content", "")
                        platform = data.get("platform", "telegram")
                        
                        text = (
                            f"📤 <b>Публикация ({platform.upper()})</b>\n\n"
                            f"{content}\n\n"
                            f"---\n"
                            f"💡 <i>Добавьте бота админом в ваш канал для автопостинга!</i>"
                        )
                        await bot.send_message(chat_id, text, parse_mode="HTML")
                    
                    elif status == "ready":
                        # Format Rich Notification
                        score = data.get("score", 0)
                        verdict = data.get("verdict", "N/A")
                        summary = data.get("summary", "")
                        post = data.get("post_content", "")
                        
                        # Basic HTML escaping
                        summary = summary.replace("<", "&lt;").replace(">", "&gt;")
                        post = post.replace("<", "&lt;").replace(">", "&gt;")
                        
                        text = (
                            f"🔔 <b>Готово!</b>\n\n"
                            f"📊 <b>Score:</b> {score}/100\n"
                            f"⚖️ <b>Вердикт:</b> {verdict}\n\n"
                            f"📝 <b>Саммари:</b>\n{summary[:200]}...\n\n"
                            f"📤 <b>Пост:</b>\nStart---\n{post[:500]}...\n---End\n\n"
                            f"🔗 <a href='{os.getenv('WEB_APP_URL')}/'>Открыть полную версию</a>"
                        )
                        await bot.send_message(chat_id, text, parse_mode="HTML")
                        
                    elif status == "error":
                        error = data.get("error", "Unknown")
                        await bot.send_message(chat_id, f"❌ Ошибка генерации: {error}")
            except Exception as e:
                print(f"Notification Error: {e}")

async def main():
    asyncio.create_task(notification_worker(bot))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
