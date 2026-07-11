import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from aiogram.enums import ParseMode
from aiohttp import web  # ← НОВОЕ

import config
import database as db

AVATARS_DIR = "avatars"
os.makedirs(AVATARS_DIR, exist_ok=True)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

def is_admin(user_id: int) -> bool:
    return user_id == config.ADMIN_ID

def should_send_photo(character_name: str) -> bool:
    counter = db.get_message_counter(character_name)
    return counter == 0 or counter % 10 == 0

async def delete_message(message: Message):
    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    except:
        pass

# --- КОРОТКИЕ АЛИАСЫ ---
@dp.message(Command("c"))
async def cmd_change_short(message: Message):
    await cmd_change(message)

@dp.message(Command("h"))
async def cmd_hide_short(message: Message):
    await cmd_hide(message)

@dp.message(Command("o"))
async def cmd_off_short(message: Message):
    await cmd_off(message)

# --- ВСЕ ТВОИ КОМАНДЫ (ОНИ ТУТ, КАК БЫЛИ) ---

@dp.message(Command("start"))
async def cmd_start(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён.")
        return
    
    await delete_message(message)
    
    hidden_status = "🔇 Включён" if db.get_hidden_mode() else "🔊 Выключен"
    active = db.get_active()
    active_str = f"Активный: {active}" if active else "Нет активного персонажа"
    
    text = (
        "👋 Привет! Я бот для ролевых игр.\n\n"
        f"📌 {active_str}\n"
        f"🔇 Скрытый режим: {hidden_status}\n\n"
        "📋 Команды:\n"
        "/add <имя> - создать персонажа (потом отправь фото)\n"
        "/c <имя_или_тег> - переключиться\n"
        "/tag <имя> <тег> - установить тег (1-4 символа)\n"
        "/bio <имя> <текст> - добавить биографию\n"
        "/o - отключить активного персонажа\n"
        "/h - скрытый режим (вкл/выкл)\n"
        "/list - список персонажей\n"
        "/info <имя> - информация\n"
        "/del <имя> - удалить\n"
        "/active - текущий активный\n\n"
        "💡 Все твои сообщения удаляются и отправляются от лица персонажа!"
    )
    await message.answer(text)

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await cmd_start(message)

@dp.message(Command("hide"))
async def cmd_hide(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён.")
        return
    
    await delete_message(message)
    
    mode = db.toggle_hidden_mode()
    status = "🔇 ВКЛЮЧЁН" if mode else "🔊 ВЫКЛЮЧЕН"
    await message.answer(f"🔄 Скрытый режим: {status}")

@dp.message(Command("off"))
async def cmd_off(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён.")
        return
    
    await delete_message(message)
    
    active = db.get_active()
    if not active:
        await message.answer("ℹ️ И так нет активного персонажа.")
        return
    
    db.set_active(None)
    
    if not db.get_hidden_mode():
        await message.answer(f"⏹️ Активный персонаж отключён.")

@dp.message(Command("add"))
async def cmd_add(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён.")
        return
    
    await delete_message(message)
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "❌ Формат: `/add <имя>`\n"
            "После этого отправь фото для аватарки.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    name = args[1].strip()
    
    if not name:
        await message.answer("❌ Имя не может быть пустым.")
        return
    
    if db.get_character(name):
        await message.answer(f"❌ Персонаж *{name}* уже существует!", parse_mode=ParseMode.MARKDOWN)
        return
    
    if db.add_character(name, "", "", ""):
        await message.answer(
            f"✅ Персонаж *{name}* создан!\n\n"
            f"📸 Теперь отправь фото для аватарки\n"
            f"(просто прикрепи картинку к сообщению).\n\n"
            f"📌 Установить тег: `/tag {name} <тег>`\n"
            f"📝 Добавить биографию: `/bio {name} <текст>`",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await message.answer(f"❌ Ошибка при создании *{name}*", parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("bio"))
async def cmd_bio(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён.")
        return
    
    await delete_message(message)
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Формат: `/bio <имя> <биография>`", parse_mode=ParseMode.MARKDOWN)
        return
    
    parts = args[1].split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ Укажите имя и биографию: `/bio Джордж Дантон Тёмный маг`", parse_mode=ParseMode.MARKDOWN)
        return
    
    name = parts[0].strip()
    new_bio = parts[1].strip()
    
    if not db.get_character(name):
        await message.answer(f"❌ Персонаж *{name}* не найден!", parse_mode=ParseMode.MARKDOWN)
        return
    
    if db.edit_character(name, bio=new_bio):
        await message.answer(f"✅ Биография для *{name}* обновлена!", parse_mode=ParseMode.MARKDOWN)
    else:
        await message.answer(f"❌ Ошибка при обновлении *{name}*", parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("tag"))
async def cmd_tag(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён.")
        return
    
    await delete_message(message)
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Формат: `/tag <имя> <тег>`\nТег должен быть 1-4 символа.", parse_mode=ParseMode.MARKDOWN)
        return
    
    parts = args[1].rsplit(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ Формат: `/tag <имя> <тег>`\nТег должен быть 1-4 символа.", parse_mode=ParseMode.MARKDOWN)
        return
    
    name = parts[0].strip()
    new_tag = parts[1].strip().upper()
    
    if len(new_tag) > 4 or len(new_tag) < 1:
        await message.answer("❌ Тег должен быть от 1 до 4 символов.")
        return
    
    if not db.get_character(name):
        await message.answer(f"❌ Персонаж *{name}* не найден!", parse_mode=ParseMode.MARKDOWN)
        return
    
    existing = db.get_character_by_tag(new_tag)
    if existing and existing["name"] != name:
        await message.answer(f"❌ Тег `{new_tag}` уже используется персонажем *{existing['name']}*", parse_mode=ParseMode.MARKDOWN)
        return
    
    if db.edit_character(name, tag=new_tag):
        await message.answer(f"✅ Тег для *{name}* установлен: `{new_tag}`", parse_mode=ParseMode.MARKDOWN)
    else:
        await message.answer(f"❌ Ошибка при установке тега", parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("change"))
async def cmd_change(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён.")
        return
    
    await delete_message(message)
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Укажите имя или тег: `/c Vasya` или `/c JD`", parse_mode=ParseMode.MARKDOWN)
        return
    
    query = args[1].strip()
    character = db.find_character(query)
    
    if not character:
        await message.answer(f"❌ Персонаж по запросу *{query}* не найден!", parse_mode=ParseMode.MARKDOWN)
        return
    
    name = character["name"]
    db.set_active(name)
    
    if db.get_hidden_mode():
        return
    
    await message.answer(
        f"🔄 Переключился на *{name}*!\n"
        f"📌 Тег: `{character.get('tag', 'нет')}`\n"
        f"📝 Биография: {character.get('bio', '(не указана)')}\n\n"
        f"💬 Первое сообщение будет с фото!",
        parse_mode=ParseMode.MARKDOWN
    )

@dp.message(Command("list"))
async def cmd_list(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён.")
        return
    
    await delete_message(message)
    
    characters = db.get_all_characters()
    if not characters:
        await message.answer("📭 Нет персонажей.")
        return
    
    active = db.get_active()
    text = "📋 *Список персонажей:*\n\n"
    for i, name in enumerate(characters, 1):
        char_data = db.get_character(name)
        active_mark = " ✅" if name == active else ""
        tag_info = f" `{char_data.get('tag', 'нет')}`"
        text += f"{i}. *{name}*{active_mark}{tag_info}\n"
    
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("info"))
async def cmd_info(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён.")
        return
    
    await delete_message(message)
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Укажите имя или тег: `/info Vasya`", parse_mode=ParseMode.MARKDOWN)
        return
    
    query = args[1].strip()
    character = db.find_character(query)
    
    if not character:
        await message.answer(f"❌ Персонаж по запросу *{query}* не найден!", parse_mode=ParseMode.MARKDOWN)
        return
    
    text = (
        f"📖 *{character['name']}*\n\n"
        f"📌 Тег: `{character.get('tag', 'нет')}`\n"
        f"📝 Биография: {character.get('bio', '(не указана)')}\n"
        f"📅 Создан: {character.get('created_at', 'неизвестно')}"
    )
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("del"))
async def cmd_delete(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён.")
        return
    
    await delete_message(message)
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Укажите имя: `/del Vasya`", parse_mode=ParseMode.MARKDOWN)
        return
    
    name = args[1].strip()
    
    avatar_path = os.path.join(AVATARS_DIR, f"{name}.jpg")
    if os.path.exists(avatar_path):
        os.remove(avatar_path)
    
    if db.delete_character(name):
        await message.answer(f"🗑️ Персонаж *{name}* удалён!", parse_mode=ParseMode.MARKDOWN)
    else:
        await message.answer(f"❌ Персонаж *{name}* не найден!", parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("active"))
async def cmd_active(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён.")
        return
    
    await delete_message(message)
    
    active = db.get_active()
    if active:
        char = db.get_character(active)
        await message.answer(
            f"🟢 Активный: *{active}*\n"
            f"📌 Тег: `{char.get('tag', 'нет')}`",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await message.answer("🟡 Нет активного персонажа.")

# --- ОБРАБОТКА ФОТО ---

@dp.message(F.photo)
async def handle_photo(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    await delete_message(message)
    
    characters = db.get_all_characters()
    if not characters:
        await message.answer("❌ Сначала создай персонажа: `/add <имя>`", parse_mode=ParseMode.MARKDOWN)
        return
    
    target_name = db.get_active()
    if not target_name:
        target_name = characters[-1]
        await message.answer(f"ℹ️ Активного персонажа нет. Фото сохраняю для *{target_name}*", parse_mode=ParseMode.MARKDOWN)
    
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    avatar_path = os.path.join(AVATARS_DIR, f"{target_name}.jpg")
    await bot.download_file(file.file_path, avatar_path)
    
    character = db.get_character(target_name)
    if character:
        data = db.load_data()
        data["characters"][target_name]["photo_url"] = avatar_path
        db.save_data(data)
        
        if not db.get_hidden_mode():
            await message.answer(f"✅ Аватарка для *{target_name}* сохранена!", parse_mode=ParseMode.MARKDOWN)
    else:
        await message.answer("❌ Персонаж не найден.", parse_mode=ParseMode.MARKDOWN)

# --- ОБРАБОТКА ТЕКСТА ---

@dp.message(F.text, ~F.text.startswith("/"))
async def handle_text(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    active_name = db.get_active()
    if not active_name:
        return
    
    text = message.text.strip()
    if not text:
        return
    
    await delete_message(message)
    
    send_photo = should_send_photo(active_name)
    db.increment_message_counter(active_name)
    
    avatar_path = os.path.join(AVATARS_DIR, f"{active_name}.jpg")
    formatted_text = f"*{active_name}:*\n{text}"
    
    if send_photo and os.path.exists(avatar_path):
        await message.answer_photo(
            photo=FSInputFile(avatar_path),
            caption=formatted_text,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await message.answer(formatted_text, parse_mode=ParseMode.MARKDOWN)

# --- НОВЫЙ ЗАПУСК (С ВЕБ-СЕРВЕРОМ ДЛЯ RENDER) ---

async def handle_web(request):
    """Обработчик для проверки Render-ом"""
    return web.Response(text="Бот запущен и работает!")

async def main():
    # 1. Запускаем веб-сервер для Render
    app = web.Application()
    app.router.add_get('/', handle_web)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"🌐 Веб-сервер запущен на порту {port}")
    
    # 2. Запускаем бота
    print("🤖 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
