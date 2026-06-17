import asyncio
import re
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from aiogram.enums import ParseMode

import config
import database as db

# Инициализация
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# Валидация ссылки на изображение
def is_valid_image_url(url: str) -> bool:
    """Проверяет, что ссылка ведёт на изображение"""
    pattern = r'^https?://.+\.(jpg|jpeg|png|gif|webp)(\?.*)?$'
    return bool(re.match(pattern, url, re.IGNORECASE))

# Проверка прав администратора
def is_admin(user_id: int) -> bool:
    return user_id == config.ADMIN_ID

# Проверка лимитов Telegram
def can_change_profile() -> bool:
    """Проверяет, можно ли менять имя/аватарку (2 раза в сутки)"""
    last_change = db.get_last_change()
    if not last_change:
        return True
    
    last_time = datetime.fromisoformat(last_change)
    # Считаем количество смен за последние 24 часа
    # Упрощённо: если последняя смена была меньше 12 часов назад
    # и мы уже меняли 2 раза - запрещаем
    # Для простоты проверяем, что прошло больше 12 часов
    time_diff = datetime.now() - last_time
    return time_diff.total_seconds() > 43200  # 12 часов

# --- ХЭНДЛЕРЫ КОМАНД ---

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Приветствие"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этому боту.")
        return
    
    text = (
        "👋 Привет! Я бот для ролевых игр.\n\n"
        "📋 Список команд:\n"
        "/add ch <имя> <фото> [\"биография\"] - добавить персонажа\n"
        "/change <имя> - переключиться на персонажа\n"
        "/say <текст> - написать от лица активного\n"
        "/list - список персонажей\n"
        "/info <имя> - информация о персонаже\n"
        "/edit <имя> <новое_фото> \"новая_био\" - редактировать\n"
        "/del <имя> - удалить персонажа\n"
        "/active - текущий активный персонаж\n"
        "/help - эта справка"
    )
    await message.answer(text)

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Помощь"""
    await cmd_start(message)

@dp.message(Command("add"))
async def cmd_add(message: Message):
    """Добавление персонажа: /add ch Vasya https://photo.jpg "Биография" """
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён.")
        return
    
    args = message.text.split(maxsplit=3)
    if len(args) < 3 or args[1] != "ch":
        await message.answer(
            "❌ Неверный формат!\n"
            "Используйте: `/add ch <имя> <ссылка_на_фото> [\"биография\"]`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    name = args[2].strip()
    # Проверяем, есть ли биография
    bio = ""
    photo_url = None
    
    if len(args) == 4:
        # Пытаемся распарсить: может быть фото или био
        third_arg = args[3].strip()
        # Проверяем, похоже на ссылку
        if is_valid_image_url(third_arg):
            photo_url = third_arg
        else:
            # Если не ссылка - считаем биографией
            bio = third_arg.strip('"')
    else:
        # Если только 3 аргумента - ждём, что второй - фото
        await message.answer(
            "❌ Укажите ссылку на фото!\n"
            "Используйте: `/add ch <имя> <ссылка_на_фото> [\"биография\"]`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Если не нашли фото в третьем аргументе - ищем во втором
    if not photo_url:
        # В этом случае у нас только имя и фото (био нет)
        # На самом деле args[3] может быть фото
        if len(args) >= 3:
            possible_photo = args[3].strip()
            if is_valid_image_url(possible_photo):
                photo_url = possible_photo
    
    if not photo_url:
        await message.answer("❌ Некорректная ссылка на фото!")
        return
    
    # Добавляем персонажа
    if db.add_character(name, photo_url, bio):
        await message.answer(f"✅ Персонаж *{name}* добавлен!", parse_mode=ParseMode.MARKDOWN)
    else:
        await message.answer(f"❌ Персонаж *{name}* уже существует!", parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("change"))
async def cmd_change(message: Message):
    """Переключение на персонажа: /change Vasya"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён.")
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Укажите имя персонажа: `/change Vasya`", parse_mode=ParseMode.MARKDOWN)
        return
    
    name = args[1].strip()
    character = db.get_character(name)
    
    if not character:
        await message.answer(f"❌ Персонаж *{name}* не найден!", parse_mode=ParseMode.MARKDOWN)
        return
    
    # Проверяем, не активен ли уже
    if db.get_active() == name:
        await message.answer(f"ℹ️ Уже активен персонаж *{name}*", parse_mode=ParseMode.MARKDOWN)
        return
    
    # Проверяем лимиты
    if not can_change_profile():
        await message.answer(
            "⚠️ Достигнут лимит смены имени/аватарки (2 раза в сутки).\n"
            "Попробуйте позже."
        )
        return
    
    # Меняем имя и аватарку бота
    try:
        await bot.set_my_name(name)
        await bot.set_my_photo(photo=character["photo_url"])
        
        # Сохраняем активного персонажа
        db.set_active(name)
        
        await message.answer(
            f"🔄 Переключился на персонажа *{name}*!\n"
            f"📝 Биография: {character['bio'] or '(не указана)'}",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка при смене: {str(e)}")

@dp.message(Command("say"))
async def cmd_say(message: Message):
    """Написать от лица активного: /say Текст"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён.")
        return
    
    active = db.get_active()
    if not active:
        await message.answer(
            "❌ Нет активного персонажа!\n"
            "Используйте `/change <имя>` чтобы выбрать персонажа.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Введите текст: `/say Привет!`", parse_mode=ParseMode.MARKDOWN)
        return
    
    text = args[1].strip()
    await message.answer(f"*{active}:* {text}", parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("list"))
async def cmd_list(message: Message):
    """Список всех персонажей"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён.")
        return
    
    characters = db.get_all_characters()
    if not characters:
        await message.answer("📭 Нет добавленных персонажей.")
        return
    
    active = db.get_active()
    text = "📋 *Список персонажей:*\n\n"
    for i, name in enumerate(characters, 1):
        char_data = db.get_character(name)
        active_mark = " ✅" if name == active else ""
        text += f"{i}. *{name}*{active_mark}\n"
        if char_data.get("bio"):
            text += f"   📝 {char_data['bio'][:50]}...\n"
    
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("info"))
async def cmd_info(message: Message):
    """Информация о персонаже: /info Vasya"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён.")
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Укажите имя: `/info Vasya`", parse_mode=ParseMode.MARKDOWN)
        return
    
    name = args[1].strip()
    character = db.get_character(name)
    
    if not character:
        await message.answer(f"❌ Персонаж *{name}* не найден!", parse_mode=ParseMode.MARKDOWN)
        return
    
    text = (
        f"📖 *Информация о персонаже*\n\n"
        f"👤 Имя: *{character['name']}*\n"
        f"🖼️ Фото: {character['photo_url']}\n"
        f"📝 Биография: {character['bio'] or '(не указана)'}\n"
        f"📅 Создан: {character['created_at']}"
    )
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("edit"))
async def cmd_edit(message: Message):
    """Редактирование персонажа: /edit Vasya https://new.jpg "Новая био" """
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён.")
        return
    
    args = message.text.split(maxsplit=3)
    if len(args) < 4:
        await message.answer(
            "❌ Неверный формат!\n"
            "Используйте: `/edit <имя> <новое_фото> \"новая_био\"`\n"
            "Где `~` означает 'не менять'",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    name = args[1].strip()
    new_photo = args[2].strip()
    new_bio = args[3].strip()
    
    # Проверяем, существует ли персонаж
    if not db.get_character(name):
        await message.answer(f"❌ Персонаж *{name}* не найден!", parse_mode=ParseMode.MARKDOWN)
        return
    
    # Обрабатываем изменения
    photo_to_update = None
    bio_to_update = None
    
    if new_photo != "~":
        if is_valid_image_url(new_photo):
            photo_to_update = new_photo
        else:
            await message.answer("❌ Некорректная ссылка на фото!")
            return
    
    if new_bio != "~":
        bio_to_update = new_bio.strip('"')
    
    if not photo_to_update and bio_to_update is None:
        await message.answer("❌ Ничего не изменено. Используйте `~` для пропуска.")
        return
    
    # Обновляем
    if db.edit_character(name, photo_to_update, bio_to_update):
        changes = []
        if photo_to_update:
            changes.append("🖼️ фото обновлено")
        if bio_to_update is not None:
            changes.append("📝 биография обновлена")
        
        await message.answer(
            f"✅ Персонаж *{name}* обновлён!\n"
            f"Изменения: {', '.join(changes)}",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await message.answer(f"❌ Ошибка при обновлении *{name}*", parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("del"))
async def cmd_delete(message: Message):
    """Удаление персонажа: /del Vasya"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён.")
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Укажите имя: `/del Vasya`", parse_mode=ParseMode.MARKDOWN)
        return
    
    name = args[1].strip()
    if db.delete_character(name):
        await message.answer(f"🗑️ Персонаж *{name}* удалён!", parse_mode=ParseMode.MARKDOWN)
    else:
        await message.answer(f"❌ Персонаж *{name}* не найден!", parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("active"))
async def cmd_active(message: Message):
    """Показать активного персонажа"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён.")
        return
    
    active = db.get_active()
    if active:
        char_data = db.get_character(active)
        await message.answer(
            f"🟢 Активный персонаж: *{active}*\n"
            f"📝 Биография: {char_data['bio'] or '(не указана)'}",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await message.answer("🟡 Нет активного персонажа.")

# --- ЗАПУСК ---
async def main():
    print("🤖 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())