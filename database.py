import json
import os
from datetime import datetime
from typing import Dict, Optional, List

DATA_FILE = "characters.json"

def load_data() -> Dict:
    if not os.path.exists(DATA_FILE):
        return {
            "characters": {},
            "active": None,
            "message_counter": {},
            "hidden_mode": False  # Скрытый режим
        }
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Автоматическая миграция
    if "hidden_mode" not in data:
        data["hidden_mode"] = False
        save_data(data)
    
    return data

def save_data(data: Dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_character(name: str) -> Optional[Dict]:
    data = load_data()
    return data["characters"].get(name)

def get_character_by_tag(tag: str) -> Optional[Dict]:
    """Ищет персонажа по тегу (регистронезависимо)"""
    data = load_data()
    tag_lower = tag.lower()
    for char in data["characters"].values():
        if char.get("tag", "").lower() == tag_lower:
            return char
    return None

def find_character(query: str) -> Optional[Dict]:
    """Ищет персонажа по имени ИЛИ тегу"""
    # Сначала пробуем по тегу
    char = get_character_by_tag(query)
    if char:
        return char
    # Потом по имени
    return get_character(query)

def get_all_characters() -> List[str]:
    data = load_data()
    return list(data["characters"].keys())

def add_character(name: str, photo_url: str, bio: str = "", tag: str = "") -> bool:
    data = load_data()
    if name in data["characters"]:
        return False
    # Если тег не указан — генерируем из первых 4 букв имени
    if not tag:
        tag = name[:4].upper()
    # Проверяем, что тег уникален
    existing = get_character_by_tag(tag)
    if existing:
        # Если тег занят — добавляем номер
        tag = f"{tag[:3]}{len(data['characters']) + 1}"
    
    data["characters"][name] = {
        "name": name,
        "tag": tag,
        "photo_url": photo_url,
        "bio": bio,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    data["message_counter"][name] = 0
    save_data(data)
    return True

def delete_character(name: str) -> bool:
    data = load_data()
    if name not in data["characters"]:
        return False
    del data["characters"][name]
    if name in data["message_counter"]:
        del data["message_counter"][name]
    if data.get("active") == name:
        data["active"] = None
    save_data(data)
    return True

def edit_character(name: str, photo_url: Optional[str] = None, bio: Optional[str] = None, tag: Optional[str] = None) -> bool:
    data = load_data()
    if name not in data["characters"]:
        return False
    if photo_url:
        data["characters"][name]["photo_url"] = photo_url
    if bio is not None:
        data["characters"][name]["bio"] = bio
    if tag:
        data["characters"][name]["tag"] = tag.upper()
    save_data(data)
    return True

def set_active(name: Optional[str]) -> bool:
    data = load_data()
    if name and name not in data["characters"]:
        return False
    data["active"] = name
    if name:
        data["message_counter"][name] = 0
    save_data(data)
    return True

def get_active() -> Optional[str]:
    data = load_data()
    return data.get("active")

def toggle_hidden_mode() -> bool:
    data = load_data()
    data["hidden_mode"] = not data.get("hidden_mode", False)
    save_data(data)
    return data["hidden_mode"]

def get_hidden_mode() -> bool:
    data = load_data()
    return data.get("hidden_mode", False)

def get_message_counter(name: str) -> int:
    data = load_data()
    return data["message_counter"].get(name, 0)

def increment_message_counter(name: str) -> int:
    data = load_data()
    if name not in data["message_counter"]:
        data["message_counter"][name] = 0
    data["message_counter"][name] += 1
    count = data["message_counter"][name]
    save_data(data)
    return count

def reset_message_counter(name: str):
    data = load_data()
    if name in data["message_counter"]:
        data["message_counter"][name] = 0
        save_data(data)

def get_last_change() -> Optional[str]:
    return None