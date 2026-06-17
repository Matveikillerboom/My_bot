import json
import os
from datetime import datetime
from typing import Dict, Optional, List

DATA_FILE = "characters.json"

def load_data() -> Dict:
    """Загружает данные из JSON-файла"""
    if not os.path.exists(DATA_FILE):
        return {
            "characters": {},
            "active": None,
            "last_change": None
        }
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data: Dict):
    """Сохраняет данные в JSON-файл"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_character(name: str) -> Optional[Dict]:
    """Получить персонажа по имени"""
    data = load_data()
    return data["characters"].get(name)

def get_all_characters() -> List[str]:
    """Получить список всех имён персонажей"""
    data = load_data()
    return list(data["characters"].keys())

def add_character(name: str, photo_url: str, bio: str = "") -> bool:
    """Добавить нового персонажа"""
    data = load_data()
    if name in data["characters"]:
        return False
    data["characters"][name] = {
        "name": name,
        "photo_url": photo_url,
        "bio": bio,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_data(data)
    return True

def delete_character(name: str) -> bool:
    """Удалить персонажа"""
    data = load_data()
    if name not in data["characters"]:
        return False
    del data["characters"][name]
    if data["active"] == name:
        data["active"] = None
    save_data(data)
    return True

def edit_character(name: str, photo_url: Optional[str] = None, bio: Optional[str] = None) -> bool:
    """Редактировать персонажа"""
    data = load_data()
    if name not in data["characters"]:
        return False
    if photo_url:
        data["characters"][name]["photo_url"] = photo_url
    if bio is not None:
        data["characters"][name]["bio"] = bio
    save_data(data)
    return True

def set_active(name: Optional[str]) -> bool:
    """Установить активного персонажа"""
    data = load_data()
    if name and name not in data["characters"]:
        return False
    data["active"] = name
    data["last_change"] = datetime.now().isoformat()
    save_data(data)
    return True

def get_active() -> Optional[str]:
    """Получить активного персонажа"""
    data = load_data()
    return data.get("active")

def get_last_change() -> Optional[str]:
    """Получить время последней смены"""
    data = load_data()
    return data.get("last_change")