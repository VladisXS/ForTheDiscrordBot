"""
Модуль баночки молочка для Discord бота
Функціонал: Юзер може клікати на баночку, кожен клік = 25% наповнення
"""

import json
import os
from datetime import datetime

# ============ JSON БД ДЛЯ БАНОЧОК ============
BANKA_DATA_FILE = "banka_data.json"

def load_banka_data():
    """Завантажити дані баночок."""
    if os.path.exists(BANKA_DATA_FILE):
        try:
            with open(BANKA_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_banka_data(data):
    """Зберегти дані баночок."""
    with open(BANKA_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_banka_key(user_id: int, server_id: int) -> str:
    """Отримати ключ для користувача."""
    return f"{user_id}_{server_id}"

def get_user_banka(user_id: int, server_id: int) -> dict:
    """Отримати дані баночки юзера."""
    data = load_banka_data()
    key = get_banka_key(user_id, server_id)
    
    if key not in data:
        data[key] = {
            "user_id": user_id,
            "server_id": server_id,
            "progress": 0,  # 0, 25, 50, 75, 100
            "completed": False,
            "created_at": datetime.now().isoformat()
        }
        save_banka_data(data)
    
    return data[key]

def add_progress(user_id: int, server_id: int) -> int:
    """Додати 25% до баночки. Повертає новий прогрес."""
    data = load_banka_data()
    key = get_banka_key(user_id, server_id)
    
    if key not in data:
        data[key] = {
            "user_id": user_id,
            "server_id": server_id,
            "progress": 0,
            "completed": False,
            "created_at": datetime.now().isoformat()
        }
    
    # Додати 25%
    if data[key]["progress"] < 100:
        data[key]["progress"] += 25
    
    # Якщо досяг 100%, позначити як завершено
    if data[key]["progress"] >= 100:
        data[key]["progress"] = 100
        data[key]["completed"] = True
        data[key]["completed_at"] = datetime.now().isoformat()
    
    save_banka_data(data)
    return data[key]["progress"]

def reset_user_banka(user_id: int, server_id: int):
    """Скинути баночку юзера (зберігаючи загальний лічильник)."""
    data = load_banka_data()
    key = get_banka_key(user_id, server_id)
    
    if key in data:
        # Зберігаємо загальний лічильник
        total_completed = data[key].get("total_completed", 0)
        
        data[key] = {
            "user_id": user_id,
            "server_id": server_id,
            "progress": 0,
            "completed": False,
            "created_at": datetime.now().isoformat(),
            "total_completed": total_completed
        }
        save_banka_data(data)

def get_progress_bar(progress: int) -> str:
    """Отримати бар прогресу."""
    filled = progress // 25
    empty = 4 - filled
    return "🟩" * filled + "⬜" * empty

def get_completed_count(user_id: int, server_id: int) -> int:
    """Отримати кількість завершених баночок юзера на сервері."""
    data = load_banka_data()
    key = get_banka_key(user_id, server_id)
    
    if key in data and data[key].get("completed"):
        # Лічимо скільки разів юзер завершив баночку
        return data[key].get("completed_count", 1)
    
    return 0

def increment_completed_count(user_id: int, server_id: int):
    """Збільшити лічильник завершених баночок."""
    data = load_banka_data()
    key = get_banka_key(user_id, server_id)
    
    if key in data:
        if "completed_count" not in data[key]:
            data[key]["completed_count"] = 1
        else:
            data[key]["completed_count"] += 1
        save_banka_data(data)

def get_total_completed_count(user_id: int, server_id: int) -> int:
    """Отримати загальну кількість всіх завершених баночок юзера."""
    # Зберігаємо в окремому полі "total_completed"
    data = load_banka_data()
    key = get_banka_key(user_id, server_id)
    
    if key in data:
        return data[key].get("total_completed", 0)
    
    return 0

def add_to_total_completed(user_id: int, server_id: int):
    """Додати 1 до загальної кількості завершених баночок."""
    data = load_banka_data()
    key = get_banka_key(user_id, server_id)
    
    if key not in data:
        data[key] = {
            "user_id": user_id,
            "server_id": server_id,
            "progress": 0,
            "completed": False,
            "created_at": datetime.now().isoformat(),
            "total_completed": 0
        }
    
    if "total_completed" not in data[key]:
        data[key]["total_completed"] = 0
    
    data[key]["total_completed"] += 1
    save_banka_data(data)

# ============ КОНСТАНТИ ============
COLOR_SUCCESS = 0x2ECC71
COLOR_WARNING = 0xF39C12
COLOR_ERROR = 0xE74C3C
COLOR_INFO = 0x3498DB

# URLs фоток
BANKA_IMAGE_URL = "https://i.imgur.com/ANX1l54.jpeg"  # Порожня баночка
BANKA_COMPLETE_IMAGE_URL = "https://i.imgur.com/vCqUZYn.jpeg"  # Заповнена баночка
