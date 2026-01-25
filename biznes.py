"""
Система бізнесу для Discord Бота
Вкладання в бізнеси з пасивним доходом
"""

import os
import json
import discord
from discord.ext import commands, tasks
from datetime import datetime
import asyncio

# ============ JSON БД ============
BUSINESS_DATA_FILE = "business_data.json"

# ============ КОНФІГ БІЗНЕСІВ ============
BUSINESSES = [
    {"key": "park", "name": "🎪 Парк", "price": 40000, "emoji": "🎪"},
    {"key": "offices", "name": "🏢 Офіси", "price": 15000, "emoji": "🏢"},
    {"key": "tattoo", "name": "🎨 Тату салон", "price": 8000, "emoji": "🎨"},
    {"key": "supermarket", "name": "🛒 Продуктовий магазин", "price": 14500, "emoji": "🛒"},
    {"key": "school", "name": "🎓 Приватна школа", "price": 60000, "emoji": "🎓"},
    {"key": "hospital", "name": "🏥 Приватна лікарня", "price": 105000, "emoji": "🏥"},
    {"key": "electronics", "name": "💻 Магазин електро техніки", "price": 9000, "emoji": "💻"},
    {"key": "barber", "name": "💈 Перукарня", "price": 5000, "emoji": "💈"},
    {"key": "stationery", "name": "📚 Магазин канцелярії", "price": 5000, "emoji": "📚"},
    {"key": "playground", "name": "🎠 Приватний дитячий майданчик", "price": 43000, "emoji": "🎠"},
]

PROFIT_PERCENTAGE = 0.0025  # 0.25% в 15 секунд
PROFIT_INTERVAL = 15  # Секунди

# ============ КАНАЛ ДЛЯ БІЗНЕСУ ============
BUSINESS_CHANNEL_ID = 1462580804998926336

# ============ ФУНКЦІЇ РОБОТИ З ДАНИМИ ============

def load_business_data():
    """Завантажує дані про бізнеси з JSON."""
    if os.path.exists(BUSINESS_DATA_FILE):
        try:
            with open(BUSINESS_DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"businesses": {}}
    return {"businesses": {}}

def save_business_data(data):
    """Зберігає дані про бізнеси у JSON."""
    with open(BUSINESS_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_player_business_key(user_id: int, server_id: int) -> str:
    """Генерує ключ для бізнесу гравця."""
    return f"{user_id}-{server_id}"

def get_player_businesses(user_id: int, server_id: int) -> dict:
    """Отримує всі бізнеси гравця."""
    data = load_business_data()
    key = get_player_business_key(user_id, server_id)
    return data["businesses"].get(key, {})

def buy_business(user_id: int, server_id: int, business_index: int, player_money: int) -> tuple:
    """
    Купує бізнес. Повертає (успіх, нове_дохід, нова_сума_грошей)
    """
    if business_index < 0 or business_index >= len(BUSINESSES):
        return False, None, None

    data = load_business_data()
    player_key = get_player_business_key(user_id, server_id)

    business = BUSINESSES[business_index]
    business_key = business["key"]
    price = business["price"]

    if player_money < price:
        return False, None, None

    # Ініціалізуємо бізнеси гравця якщо потрібно
    if player_key not in data["businesses"]:
        data["businesses"][player_key] = {}

    # Додаємо або збільшуємо кількість бізнесу
    if business_key in data["businesses"][player_key]:
        data["businesses"][player_key][business_key]["count"] += 1
    else:
        data["businesses"][player_key][business_key] = {
            "name": business["name"],
            "price": price,
            "emoji": business["emoji"],
            "count": 1,
            "bought_at": datetime.now().isoformat()
        }

    new_money = player_money - price
    save_business_data(data)

    return True, price, new_money

def reset_player_businesses(user_id: int, server_id: int) -> bool:
    """Скидує всі бізнеси гравця. Повертає True якщо успішно."""
    data = load_business_data()
    player_key = get_player_business_key(user_id, server_id)

    if player_key in data["businesses"]:
        del data["businesses"][player_key]
        save_business_data(data)
        return True
    return True  # Повертаємо True навіть якщо немає бізнесів

def calculate_profit(price: float) -> float:
    """Розраховує прибиль (0.25% від ціни)."""
    return price * PROFIT_PERCENTAGE

def get_total_profit(user_id: int, server_id: int) -> float:
    """Розраховує загальну прибиль за всі бізнеси гравця."""
    businesses = get_player_businesses(user_id, server_id)
    total_profit = 0

    for business_key, business_data in businesses.items():
        # Знаходимо бізнес по ключу
        for business in BUSINESSES:
            if business["key"] == business_key:
                price = business["price"]
                count = business_data.get("count", 1)
                profit = calculate_profit(price) * count
                total_profit += profit
                break

    return total_profit

# ============ КОМАНДИ ============

def get_business_cog(bot):
    """Отримує Cog з командами бізнесу."""

    class BusinessCog(commands.Cog):
        def __init__(self, bot_instance):
            self.bot = bot_instance
            self.profit_loop.start()

        def cog_unload(self):
            self.profit_loop.cancel()

        @commands.command(name="buybusiness")
        async def buy_business_command(self, ctx, business_num: int = None):
            """Показує каталог бізнесів або купує бізнес по номеру."""
            # Імпортуємо функції з clicker для перевірки грошей
            from clicker import get_player, set_player_money

            user_id = ctx.author.id
            server_id = ctx.guild.id

            player = get_player(user_id, server_id)
            if not player:
                await ctx.send("❌ У тебе немає профілю! Використай `!start`")
                return

            # Якщо не передав аргумент - показуємо каталог
            if business_num is None:
                player_money = player["money"]

                # Створюємо embed з каталогом
                embed = discord.Embed(
                    title="💼 Каталог Бізнесів",
                    description="Вибери бізнес для покупки",
                    color=discord.Color.gold()
                )
                embed.add_field(name="💵 Твій баланс", value=f"**{player_money:,}** 💵", inline=False)

                # Додаємо всі бізнеси з номерами
                for idx, business in enumerate(BUSINESSES, 1):
                    emoji = business["emoji"]
                    name = business["name"]
                    price = business["price"]

                    can_buy = player_money >= price
                    buy_status = "✅ Можеш купити" if can_buy else "❌ Не вистачає грошей"

                    embed.add_field(
                        name=f"#{idx} {emoji} {name}",
                        value=f"💰 Ціна: **{price:,}** 💵\n{buy_status}",
                        inline=True
                    )

                embed.add_field(
                    name="📝 Як купити?",
                    value="Використай: `!buybusiness [номер бізнесу]`\n"
                          "Приклад: `!buybusiness 5`",
                    inline=False
                )

                embed.set_footer(text=f"Прибиль: 0.25% в 15 секунд від ціни бізнесу")

                await ctx.send(embed=embed)
                return

            # Якщо передав номер - купуємо бізнес
            # Індекс починається з 0, але користувач вводить з 1
            business_index = business_num - 1

            # Перевіряємо чи такий бізнес існує
            if business_index < 0 or business_index >= len(BUSINESSES):
                await ctx.send(f"❌ Бізнес #{business_num} не знайдено. Використай `!buybusiness` для списку.")
                return

            # Купуємо бізнес
            success, price, new_money = buy_business(user_id, server_id, business_index, player["money"])

            if not success:
                business = BUSINESSES[business_index]
                required = business["price"]
                missing = required - player["money"]
                await ctx.send(
                    f"❌ Не вистачає грошей!\n"
                    f"💰 Потрібно: **{required:,}** 💵\n"
                    f"❌ Не вистачає: **{missing:,}** 💵"
                )
                return

            # Оновлюємо баланс у clicker.py
            set_player_money(user_id, server_id, int(new_money))

            business = BUSINESSES[business_index]
            profit_per_15_sec = calculate_profit(business["price"])

            embed = discord.Embed(
                title="✅ Бізнес придбаний!",
                color=discord.Color.green()
            )
            embed.add_field(
                name=f"{business['emoji']} {business['name']}",
                value=f"💰 Ціна: **{price:,}** 💵",
                inline=False
            )
            embed.add_field(
                name="💸 Прибиль",
                value=f"**{profit_per_15_sec:.2f}** 💵 в 15 секунд",
                inline=False
            )
            embed.add_field(
                name="💵 Новий баланс",
                value=f"**{int(new_money):,}** 💵",
                inline=False
            )

            await ctx.send(embed=embed)


        @commands.command(name="mybusinesses")
        async def my_businesses_command(self, ctx):
            """Показує твої бізнеси."""
            # Імпортуємо функції з clicker
            from clicker import get_player

            user_id = ctx.author.id
            server_id = ctx.guild.id

            player = get_player(user_id, server_id)
            if not player:
                await ctx.send("❌ У тебе немає профілю! Використай `!start`")
                return

            businesses = get_player_businesses(user_id, server_id)

            if not businesses:
                await ctx.send("❌ У тебе немає жодного бізнесу. Використай `!buybusiness` щоб купити.")
                return

            total_profit = get_total_profit(user_id, server_id)

            embed = discord.Embed(
                title="💼 Мої Бізнеси",
                description=f"👤 {ctx.author.mention}",
                color=discord.Color.gold()
            )

            for business_key, business_data in businesses.items():
                count = business_data.get("count", 1)
                emoji = business_data.get("emoji", "📦")
                name = business_data.get("name", "Невідомий")
                price = business_data.get("price", 0)

                profit_per_15_sec = calculate_profit(price) * count

                embed.add_field(
                    name=f"{emoji} {name}",
                    value=f"📊 Кількість: **{count}**\n"
                          f"💰 Ціна за одиницю: **{price:,}** 💵\n"
                          f"💸 Прибиль: **{profit_per_15_sec:.2f}** 💵/15сек",
                    inline=False
                )

            embed.add_field(
                name="📈 Загальна прибиль",
                value=f"**{total_profit:.2f}** 💵 в 15 секунд",
                inline=False
            )

            await ctx.send(embed=embed)

        @tasks.loop(seconds=PROFIT_INTERVAL)
        async def profit_loop(self):
            """Додає прибиль від бізнесів кожні 15 секунд."""
            try:
                # Імпортуємо функції з clicker
                from clicker import load_data, save_data, get_player_key

                data = load_business_data()
                player_data = load_data()

                # Розраховуємо прибиль за кожен бізнес
                for player_key_business, businesses in data["businesses"].items():
                    # Формат ключа: user_id-server_id
                    parts = player_key_business.split("-")
                    if len(parts) != 2:
                        continue
                    
                    try:
                        user_id, server_id = int(parts[0]), int(parts[1])
                    except ValueError:
                        continue

                    player_key = get_player_key(user_id, server_id)

                    if player_key not in player_data["users"]:
                        continue

                    total_profit = 0
                    for business_key, business_data in businesses.items():
                        # Знайдемо бізнес у нашому конфігу
                        business_config = next((b for b in BUSINESSES if b["key"] == business_key), None)
                        if business_config:
                            # Використовуємо ціну з конфігу, а не з бізнесу
                            price = business_config["price"]
                            count = business_data.get("count", 1)
                            profit = calculate_profit(price) * count
                            total_profit += profit

                    # Додаємо прибиль
                    if total_profit > 0:
                        player_data["users"][player_key]["money"] += total_profit

                save_data(player_data)

            except Exception as e:
                print(f"❌ Помилка в циклі прибилі бізнесів: {e}")

        @profit_loop.before_loop
        async def before_profit_loop(self):
            """Чекає коли бот буде готовий перед стартом циклу."""
            await self.bot.wait_until_ready()

    return BusinessCog(bot)

# ============ ІНТЕГРАЦІЯ З БОТОМ ============

async def setup_business(bot):
    """Налаштовує систему бізнесу в боті."""
    cog = get_business_cog(bot)
    await bot.add_cog(cog)
