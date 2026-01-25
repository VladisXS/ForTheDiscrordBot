"""
Клікер механіка для Discord Бота
Всі функції роботи з гравцями та база даних
"""

import os
import json
from datetime import datetime

# ============ JSON БД ============
DATA_FILE = "game_data.json"

# ============ КОНФІГ АПГРЕЙДІВ ============
BASE_CLICK_UPGRADE_COST = 50
BASE_IDLE_UPGRADE_COST = 100
UPGRADE_MULTIPLIER = 1.2  # 20% збільшення вартості на кожен рівень

def calculate_upgrade_cost(base_cost: int, level: int) -> int:
    """Розраховує вартість апгрейду на основі рівня гравця.
    Формула: base_cost * (1.2 ^ (level - 1))
    """
    return int(base_cost * (UPGRADE_MULTIPLIER ** (level - 1)))

def load_data():
    """Завантажує дані з JSON. Створює порожнистий файл якщо його немає."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"users": {}}
    return {"users": {}}

def save_data(data):
    """Зберігає дані у JSON."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_player_key(user_id: int, server_id: int) -> str:
    """Генерує ключ гравця у форматі 'user_id-server_id'."""
    return f"{user_id}-{server_id}"

def create_player(user_id: int, server_id: int) -> bool:
    """Створює профіль гравця. Повертає True якщо успішно."""
    data = load_data()
    key = get_player_key(user_id, server_id)

    if key in data["users"]:
        return False  # Вже існує

    data["users"][key] = {
        "user_id": user_id,
        "server_id": server_id,
        "money": 0,
        "income_per_click": 1,
        "income_per_sec": 0,
        "level": 1,
        "last_click_time": 0,
        "created_at": datetime.now().isoformat(),
        "has_certificate": False,
        "certificate_date": None
    }

    save_data(data)
    return True

def get_player(user_id: int, server_id: int) -> dict | None:
    """Отримує дані гравця."""
    data = load_data()
    key = get_player_key(user_id, server_id)
    return data["users"].get(key)

def add_money(user_id: int, server_id: int, amount: int):
    """Додає гроші гравцю."""
    data = load_data()
    key = get_player_key(user_id, server_id)

    if key in data["users"]:
        data["users"][key]["money"] += amount
        save_data(data)

def update_click_time(user_id: int, server_id: int, timestamp: float):
    """Оновлює час останнього кліка."""
    data = load_data()
    key = get_player_key(user_id, server_id)

    if key in data["users"]:
        data["users"][key]["last_click_time"] = timestamp
        save_data(data)

def upgrade_income_per_click(user_id: int, server_id: int) -> bool:
    """Апгрейдить дохід за клік. Повертає True якщо успішно."""
    data = load_data()
    key = get_player_key(user_id, server_id)

    if key not in data["users"]:
        return False

    player = data["users"][key]

    # Розраховуємо вартість на основі поточного рівня
    cost = calculate_upgrade_cost(BASE_CLICK_UPGRADE_COST, player["level"])

    if player["money"] < cost:
        return False

    player["money"] -= cost
    player["income_per_click"] += 1
    player["level"] += 1

    save_data(data)
    return True

def upgrade_income_per_sec(user_id: int, server_id: int) -> bool:
    """Апгрейдить пасивний дохід. Повертає True якщо успішно."""
    data = load_data()
    key = get_player_key(user_id, server_id)

    if key not in data["users"]:
        return False

    player = data["users"][key]

    # Розраховуємо вартість на основі поточного рівня
    cost = calculate_upgrade_cost(BASE_IDLE_UPGRADE_COST, player["level"])

    if player["money"] < cost:
        return False

    player["money"] -= cost
    player["income_per_sec"] += 1

    save_data(data)
    return True

def set_player_money(user_id: int, server_id: int, amount: int) -> bool:
    """Встановлює гроші гравцю. Повертає True якщо успішно."""
    data = load_data()
    key = get_player_key(user_id, server_id)

    if key not in data["users"]:
        return False

    data["users"][key]["money"] = max(0, amount)
    save_data(data)
    return True

def set_player_level(user_id: int, server_id: int, level: int) -> bool:
    """Встановлює рівень гравцю. Повертає True якщо успішно."""
    data = load_data()
    key = get_player_key(user_id, server_id)

    if key not in data["users"]:
        return False

    data["users"][key]["level"] = max(1, level)
    save_data(data)
    return True

def set_income_per_click(user_id: int, server_id: int, amount: int) -> bool:
    """Встановлює дохід за клік. Повертає True якщо успішно."""
    data = load_data()
    key = get_player_key(user_id, server_id)

    if key not in data["users"]:
        return False

    data["users"][key]["income_per_click"] = max(1, amount)
    save_data(data)
    return True

def set_income_per_sec(user_id: int, server_id: int, amount: int) -> bool:
    """Встановлює дохід за секунду. Повертає True якщо успішно."""
    data = load_data()
    key = get_player_key(user_id, server_id)

    if key not in data["users"]:
        return False

    data["users"][key]["income_per_sec"] = max(0, amount)
    save_data(data)
    return True

def issue_certificate(user_id: int, server_id: int) -> bool:
    """Видає сертифікат гравцю. Повертає True якщо успішно."""
    data = load_data()
    key = get_player_key(user_id, server_id)

    if key not in data["users"]:
        return False

    data["users"][key]["has_certificate"] = True
    data["users"][key]["certificate_date"] = datetime.now().isoformat()
    save_data(data)
    return True

def get_server_top(server_id: int, limit: int = 10) -> list:
    """Отримує ТОП-10 гравців на сервері."""
    data = load_data()

    # Фільтруємо гравців цього сервера
    server_players = [
        player for player in data["users"].values()
        if player["server_id"] == server_id
    ]

    # Сортуємо за грошима
    server_players.sort(key=lambda x: x["money"], reverse=True)

    # Беремо топ
    top_players = []
    for idx, player in enumerate(server_players[:limit], 1):
        top_players.append({
            "position": idx,
            "user_id": player["user_id"],
            "money": player["money"],
            "level": player["level"],
            "income_per_click": player["income_per_click"]
        })

    return top_players
def clear_active_game(user_id: int, server_id: int, active_games: dict) -> bool:
    """Очищує активну гру гравця для оновлення даних. Повертає True якщо успішно."""
    key = (user_id, server_id)
    if key in active_games:
        del active_games[key]
        return True
    return False

def reset_player_progress(user_id: int, server_id: int) -> bool:
    """Скидує прогрес гравця на початковий рівень. Повертає True якщо успішно."""
    data = load_data()
    key = get_player_key(user_id, server_id)

    if key not in data["users"]:
        return False

    # Скидуємо всі параметри на початкові значення
    data["users"][key]["money"] = 0
    data["users"][key]["income_per_click"] = 1
    data["users"][key]["income_per_sec"] = 0
    data["users"][key]["level"] = 1
    data["users"][key]["last_click_time"] = 0
    data["users"][key]["has_certificate"] = False
    data["users"][key]["certificate_date"] = None

    save_data(data)
    return True
