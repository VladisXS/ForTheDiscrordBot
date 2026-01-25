"""
Discord Clicker Bot - Все в одному файлі
Idle гра з server-specific економікою (JSON)
"""

import os
import json
import discord
from discord.ext import commands, tasks
from discord import app_commands
import time
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# ============ ЗАВАНТАЖИТИ .ENV ============
load_dotenv()

# Імпортуємо клікер механіку
from clicker import (
    load_data, save_data, get_player_key, create_player, get_player,
    add_money, update_click_time, upgrade_income_per_click,
    set_player_money, set_player_level, set_income_per_click,
    set_income_per_sec, issue_certificate, get_server_top, DATA_FILE, clear_active_game,
    calculate_upgrade_cost, BASE_CLICK_UPGRADE_COST,
    reset_player_progress
)

# Імпортуємо систему бізнесу
from biznes import setup_business, get_total_profit, reset_player_businesses

# Імпортуємо казино модуль
from kazino import setup_casino, reset_casino_stats

# Імпортуємо модуль баночки молочка
from banka import (
    load_banka_data, save_banka_data, get_banka_key, get_user_banka,
    add_progress, reset_user_banka, get_progress_bar,
    BANKA_IMAGE_URL, BANKA_COMPLETE_IMAGE_URL,
    get_total_completed_count, add_to_total_completed
)

# ============ КОНФІГ ============
# Токен бота
TOKEN = os.getenv("DISCORD_TOKEN")

# ID власника бота
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

# ID додатку
APP_ID = int(os.getenv("APP_ID", "0"))

# URL фотки сертифіката
CERTIFICATE_IMAGE_URL = os.getenv("CERTIFICATE_IMAGE_URL")
CLICK_COOLDOWN = 0.5

COLOR_SUCCESS = 0x2ECC71
COLOR_WARNING = 0xF39C12
COLOR_ERROR = 0xE74C3C
COLOR_INFO = 0x3498DB

EMOJI_CLICK = "💰"
EMOJI_UPGRADE = "⬆️"
EMOJI_TOP = "🏆"
EMOJI_PROFILE = "👤"
EMOJI_MONEY = "💵"
EMOJI_LEVEL = "📊"
EMOJI_CLOCK = "⏱️"
EMOJI_SUCCESS = "✅"
EMOJI_ERROR = "❌"

# ============ FLASK KEEP-ALIVE ============
app = Flask('')

@app.route('/')
def home():
    return "Я живий! 🟢"

def run():
    app.run(host='0.0.0.0', port=5000)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()
    print("✅ Keep-alive server started on port 5000")

# ============ ІНТЕНТИ ДИСКОРДУ ============

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True
intents.presences = True
bot = commands.Bot(intents=intents, application_id=APP_ID, command_prefix=["!", "/"], help_command=None)

# Для cooldown
click_cooldowns = {}

# Активні ігри для оновлення в реальному часі
# Формат: {(user_id, server_id): (message, channel)}
active_games = {}

# Дані адміністраторів
admin_ids = []

# ============ JSON БД - ДІЇ ТА АДМІНИ ============
ACTIONS_FILE = "actions.json"
ADMINS_FILE = "admins.json"

def load_actions():
    """Завантажує дії з JSON."""
    if not os.path.exists(ACTIONS_FILE):
        return {}
    try:
        with open(ACTIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_actions(actions):
    """Зберігає дії у JSON."""
    with open(ACTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(actions, f, ensure_ascii=False, indent=2)

# ============ ФАЙЛИ ДАНІ ============

def init_files():
    """Ініціалізує необхідні JSON файли."""
    if not os.path.exists(DATA_FILE):
        save_data({"users": {}})
    if not os.path.exists(ACTIONS_FILE):
        save_actions({})
    if not os.path.exists(ADMINS_FILE):
        save_admins()

@bot.event
async def on_message(message):
    """Обробляє звичайні повідомлення."""
    if message.author.bot:
        return

    # Обробка дій (напр. обійняв, цілував)
    if message.mentions:
        mentioned_user = message.mentions[0]
        msg_text = message.content.lower()
        for action in actions:
            if action in msg_text:
                template = actions[action]
                response = template.format(
                    author=message.author.mention,
                    target=mentioned_user.mention
                )
                await message.channel.send(response)
                break

    # Привіт
    if message.content.lower() == "привіт":
        await message.channel.send("Привіт!")

    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    """Обробляє помилки команд."""
    if isinstance(error, commands.MissingRequiredArgument):
        if ctx.command.name == "setadm":
            await ctx.send("❌ Використання: `!setadm @користувач`")
        elif ctx.command.name == "deladmin":
            await ctx.send("❌ Використання: `/deladmin @користувач`")
        elif ctx.command.name == "addc":
            await ctx.send("❌ Використання: `!addc \"дія\": \"{author} робить щось {target}\"`")
        else:
            await ctx.send(f"❌ Не вистачає аргументу для команди `{ctx.command.name}`")
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        print(f"Помилка: {error}")

# ============ КОМАНДИ АДМІНІСТРАТОРІВ ============

@bot.command(name="setadm")
async def set_admin(ctx, member: discord.Member = None):
    """Додати адміністратора (тільки власник)."""
    if member is None:
        await ctx.send("❌ Використання: `!setadm @користувач`")
        return

    if OWNER_ID is None or ctx.author.id != OWNER_ID:
        await ctx.send("⛔ Тільки власник може додавати адміністраторів.")
        return

    if member.id not in admin_ids:
        admin_ids.append(member.id)
        save_admins()
        await ctx.send(f"✅ {member.mention} тепер адміністратор!")
    else:
        await ctx.send(f"⚠️ {member.mention} вже є адміністратором.")

@bot.command(name="deladmin")
async def delete_admin(ctx, member: discord.Member = None):
    """Видалити адміністратора (тільки власник)."""
    if member is None:
        await ctx.send("❌ Використання: `/deladmin @користувач`")
        return

    if OWNER_ID is None or ctx.author.id != OWNER_ID:
        await ctx.send("⛔ Тільки власник може видаляти адміністраторів.")
        return

    if member.id in admin_ids:
        admin_ids.remove(member.id)
        save_admins()
        await ctx.send(f"❌ {member.mention} більше не адміністратор.")
    else:
        await ctx.send(f"⚠️ {member.mention} не є адміністратором.")

@bot.command(name="addc")
async def add_custom_action(ctx, *, msg: str = None):
    """Додати нову дію (тільки власник та адміни)."""
    if msg is None:
        await ctx.send("❌ Використання: `!addc \"дія\": \"{author} робить щось {target}\"`")
        return

    if OWNER_ID and ctx.author.id != OWNER_ID and ctx.author.id not in admin_ids:
        await ctx.send("⛔ Ти не маєш доступу до адмін-команд.")
        return

    try:
        if '": "' in msg:
            key, template = msg.split('": "', 1)
        elif '":"' in msg:
            key, template = msg.split('":"', 1)
        else:
            await ctx.send("❌ Формат неправильний. Використовуй: `!addc \"дія\": \"{author} щось там {target}\"`")
            return

        key = key.strip().strip('"')
        template = template.strip().strip('"')

        if "{author}" not in template or "{target}" not in template:
            await ctx.send("❌ Шаблон має містити {author} і {target}.")
            return

        actions[key.lower()] = template
        save_actions(actions)
        await ctx.send(f"✅ Дія \"{key}\" додана.")
    except Exception as e:
        await ctx.send(f"❌ Помилка додавання: {e}")

@bot.command(name="delc")
async def delete_custom_action(ctx, action: str = None):
    """Видалити дію (тільки власник та адміни)."""
    if action is None:
        await ctx.send("❌ Використання: `!delc назва_дії`")
        return

    if OWNER_ID and ctx.author.id != OWNER_ID and ctx.author.id not in admin_ids:
        await ctx.send("⛔ Ти не маєш доступу до адмін-команд.")
        return

    action = action.lower()
    if action in actions:
        del actions[action]
        save_actions(actions)
        await ctx.send(f"✅ Дія \"{action}\" видалена.")
    else:
        await ctx.send(f"❌ Дія \"{action}\" не знайдена.")

@bot.command(name="admins")
async def list_admins(ctx):
    """Показати список адміністраторів."""
    if not admin_ids:
        await ctx.send("❌ Немає доданих адміністраторів.")
        return
    mentions = [f"<@{aid}>" for aid in admin_ids]
    embed = discord.Embed(
        title="🛡️ Список адміністраторів",
        description="\n".join(mentions),
        color=discord.Color.orange()
    )
    await ctx.send(embed=embed)

@bot.command(name="userscertification")
async def users_certification_command(ctx):
    """Показати список користувачів з сертифікатом (тільки адмін)."""
    if OWNER_ID and ctx.author.id != OWNER_ID and ctx.author.id not in admin_ids:
        await ctx.send("⛔ Ти не маєш доступу до адмін-команд.")
        return

    data = load_data()
    server_id = ctx.guild.id

    # Фільтруємо користувачів з сертифікатом на цьому сервері
    certified_users = [
        player for player in data["users"].values()
        if player["server_id"] == server_id and player.get("has_certificate", False)
    ]

    if not certified_users:
        embed = discord.Embed(
            title="🎖️ Сертифікована користувачі",
            description="На цьому сервері немає користувачів з сертифікатом.",
            color=COLOR_WARNING
        )
        await ctx.send(embed=embed)
        return

    # Створити списко сертифікованих користувачів
    certification_list = []
    for player in certified_users:
        user_mention = f"<@{player['user_id']}>"
        cert_date = player.get("certificate_date", "Невідомо")
        if cert_date and cert_date != "Невідомо":
            # Форматувати дату
            try:
                cert_datetime = datetime.fromisoformat(cert_date)
                formatted_date = cert_datetime.strftime("%d.%m.%Y %H:%M")
            except:
                formatted_date = cert_date
        else:
            formatted_date = "Невідомо"

        certification_list.append(f"{user_mention} - {formatted_date}")

    embed = discord.Embed(
        title="🎖️ Користувачі з сертифікатом",
        description="\n".join(certification_list) if certification_list else "Немає.",
        color=COLOR_SUCCESS
    )
    embed.set_footer(text=f"Всього: {len(certified_users)}")
    await ctx.send(embed=embed)

@bot.command(name="addmoney")
async def add_money_command(ctx, member: discord.Member = None, amount: int = None):
    """Видати гроші гравцю (тільки адмін)."""
    if OWNER_ID and ctx.author.id != OWNER_ID and ctx.author.id not in admin_ids:
        await ctx.send("⛔ Ти не маєш доступу до адмін-команд.")
        return

    if member is None or amount is None:
        await ctx.send("❌ Використання: `!addmoney @користувач кількість_грошей`")
        return

    if amount < 0:
        await ctx.send("❌ Кількість грошей не може бути негативною!")
        return

    server_id = ctx.guild.id
    if set_player_money(member.id, server_id, (get_player(member.id, server_id)["money"] if get_player(member.id, server_id) else 0) + amount):
        player = get_player(member.id, server_id)
        embed = discord.Embed(
            title=f"💵 Гроші видані",
            description=f"Виданої {amount} 💵 користувачу {member.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="Новий баланс", value=f"**{player['money']:,}** 💵", inline=False)
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ У користувача {member.mention} немає профілю!")

@bot.command(name="removemoney")
async def remove_money_command(ctx, member: discord.Member = None, amount: int = None):
    """Забрати гроші у гравця (тільки адмін)."""
    if OWNER_ID and ctx.author.id != OWNER_ID and ctx.author.id not in admin_ids:
        await ctx.send("⛔ Ти не маєш доступу до адмін-команд.")
        return

    if member is None or amount is None:
        await ctx.send("❌ Використання: `!removemoney @користувач кількість_грошей`")
        return

    if amount < 0:
        await ctx.send("❌ Кількість грошей не може бути негативною!")
        return

    server_id = ctx.guild.id
    player = get_player(member.id, server_id)
    if player:
        new_amount = max(0, player["money"] - amount)
        if set_player_money(member.id, server_id, new_amount):
            embed = discord.Embed(
                title=f"💵 Гроші забрані",
                description=f"Забрано {amount} 💵 у користувача {member.mention}",
                color=discord.Color.red()
            )
            embed.add_field(name="Новий баланс", value=f"**{new_amount:,}** 💵", inline=False)
            await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ У користувача {member.mention} немає профілю!")

@bot.command(name="setlevel")
async def set_level_command(ctx, member: discord.Member = None, level: int = None):
    """Встановити рівень гравцю (тільки адмін)."""
    if OWNER_ID and ctx.author.id != OWNER_ID and ctx.author.id not in admin_ids:
        await ctx.send("⛔ Ти не маєш доступу до адмін-команд.")
        return

    if member is None or level is None:
        await ctx.send("❌ Використання: `!setlevel @користувач рівень`")
        return

    if level < 1:
        await ctx.send("❌ Рівень не може бути менше 1!")
        return

    server_id = ctx.guild.id
    if set_player_level(member.id, server_id, level):
        player = get_player(member.id, server_id)
        embed = discord.Embed(
            title=f"📊 Рівень змінено",
            description=f"Рівень встановлено на {level} для користувача {member.mention}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Новий рівень", value=f"**Lv. {player['level']}**", inline=False)
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ У користувача {member.mention} немає профілю!")

@bot.command(name="setclickdps")
async def set_click_dps_command(ctx, member: discord.Member = None, amount: int = None):
    """Встановити дохід за клік (тільки адмін)."""
    if OWNER_ID and ctx.author.id != OWNER_ID and ctx.author.id not in admin_ids:
        await ctx.send("⛔ Ти не маєш доступу до адмін-команд.")
        return

    if member is None or amount is None:
        await ctx.send("❌ Використання: `!setclickdps @користувач кількість`")
        return

    if amount < 1:
        await ctx.send("❌ Дохід не може бути менше 1!")
        return

    server_id = ctx.guild.id
    if set_income_per_click(member.id, server_id, amount):
        player = get_player(member.id, server_id)
        embed = discord.Embed(
            title=f"💸 Дохід за клік змінено",
            description=f"Дохід за клік встановлено на {amount} для користувача {member.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="Новий дохід за клік", value=f"**+{player['income_per_click']}** 💵/клік", inline=False)
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ У користувача {member.mention} немає профілю!")


@bot.command(name="reset")
async def reset_command(ctx, member: discord.Member = None):
    """Скинути прогрес гравця на початковий рівень (тільки адмін)."""
    if OWNER_ID and ctx.author.id != OWNER_ID and ctx.author.id not in admin_ids:
        await ctx.send("⛔ Ти не маєш доступу до адмін-команд.")
        return

    if member is None:
        await ctx.send("❌ Використання: `!reset @користувач`")
        return

    server_id = ctx.guild.id
    if reset_player_progress(member.id, server_id):
        # Скидуємо всі бізнеси гравця
        reset_player_businesses(member.id, server_id)
        
        # Скидуємо казино статистику
        reset_casino_stats(member.id, server_id)
        
        # Скидуємо пасивний дохід на 0
        set_income_per_sec(member.id, server_id, 0)
        
        # Очищуємо активну гру гравця
        clear_active_game(member.id, server_id, active_games)
        
        embed = discord.Embed(
            title=f"🔄 Прогрес скинено",
            description=f"Прогрес користувача {member.mention} скинено на початковий рівень",
            color=discord.Color.orange()
        )
        embed.add_field(name="💰 Монети", value="**0**", inline=True)
        embed.add_field(name="📊 Рівень Кліку", value="**1**", inline=True)
        embed.add_field(name="⚡ Рівень Пасиву", value="**0**", inline=True)
        embed.add_field(name="🏢 Бізнеси", value="**Видалено**", inline=True)
        embed.add_field(name="🎰 Казино Статистика", value="**Видалено**", inline=True)
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ У користувача {member.mention} немає профілю!")

@bot.command(name="тест")
async def test_command(ctx):
    """Перевірити роботу бота."""
    await ctx.send("✅ Бот працює правильно!")

@bot.command(name="активність")
async def check_activity(ctx, member: discord.Member = None):
    """Подивитись активність користувача."""
    member = member or ctx.author
    if member.activities:
        activities = [f"- {a.name}" for a in member.activities if hasattr(a, 'name') and a.name]
        await ctx.send(f"**{member.display_name}** зараз:\n" + "\n".join(
            activities) if activities else f"**{member.display_name}** нічого не робить")
    else:
        await ctx.send(f"**{member.display_name}** нічого не робить")

@bot.command(name="help")
async def help_command(ctx):
    """Показати довідку по боту."""
    embed = discord.Embed(
        title="📜 Довідка по боту",
        description="Список команд та функцій бота",
        color=discord.Color.blue()
    )

    owner_cmds = (
        "`!setadm @user` - додати адміна\n"
        "`!deladmin @user` - видалити адміна"
    )
    embed.add_field(name="👑 Команди власника", value=owner_cmds, inline=False)

    admin_cmds = (
        "`!addc \"дія\": \"{author} текст {target}\"` - додати дію\n"
        "`!delc назва` - видалити дію\n"
        "`!admins` - список адмінів\n"
        "`!userscertification` - переглянути користувачів з сертифікатом\n"
        "`!addmoney @user кількість` - видати гроші\n"
        "`!removemoney @user кількість` - забрати гроші\n"
        "`!setlevel @user рівень` - встановити рівень\n"
        "`!setclickdps @user кількість` - встановити дохід за клік\n"
        "`!reset @user` - скинути прогрес гравця"
    )
    embed.add_field(name="🛡️ Команди адмінів", value=admin_cmds, inline=False)

    clicker_cmds = (
        "`!start` - створити профіль\n"
        "`!profile` - переглянути профіль\n"
        "`!top` - ТОП-10 гравців\n"
        "`!clicker` - відкрити гру\n"
        "`!certification` - пройти тест на Негев"
    )
    embed.add_field(name="🎮 Клікер команди", value=clicker_cmds, inline=False)

    business_cmds = (
        "`!buybusiness` - каталог бізнесів\n"
        "`!buybusiness [номер]` - купити бізнес\n"
        "`!mybusinesses` - мої бізнеси і прибиль"
    )
    embed.add_field(name="💼 Команди бізнесу", value=business_cmds, inline=False)

    casino_cmds = (
        "`!kazino` - грати в казино (вибір множника x2, x3, x5, x10)\n"
        "`!kazino_stats` - твоя казино статистика"
    )
    embed.add_field(name="🎰 Команди казино", value=casino_cmds, inline=False)

    banka_cmds = (
        "`!banochka` - відкрити баночку молочка (натискай 4 рази!)\n"
        "`!stats_banochka` - статистика твоїх баночок"
    )
    embed.add_field(name="🥛 Команди баночки молочка", value=banka_cmds, inline=False)

    user_cmds = (
        "`!тест` - перевірити роботу бота\n"
        "`!активність [@user]` - подивитись активність\n"
        "`!help` - ця довідка"
    )
    embed.add_field(name="👤 Команди користувачів", value=user_cmds, inline=False)

    embed.set_footer(text=f"Бот: {bot.user.name}")
    await ctx.send(embed=embed)

# ============ КОМАНДИ КЛІКЕРА ============

def load_admins():
    """Завантажує список адмінів з JSON."""
    if not os.path.exists(ADMINS_FILE):
        return []
    try:
        with open(ADMINS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_admins():
    """Зберігає список адмінів."""
    with open(ADMINS_FILE, "w", encoding="utf-8") as f:
        json.dump(admin_ids, f, ensure_ascii=False, indent=2)

actions = load_actions()
admin_ids = load_admins()

# ============ БОТА НАЛАШТУВАННЯ ============

# Для cooldown
click_cooldowns = {}

@bot.event
async def on_ready():
    """Бот готовий."""
    print(f"✅ Бот онлайн як {bot.user}")
    # Переконуємось що файл існує
    if not os.path.exists(DATA_FILE):
        save_data({"users": {}})
    # Синхронізуємо команди
    try:
        synced = await bot.tree.sync()
        print(f"✅ Синхронізовано {len(synced)} команди")
    except Exception as e:
        print(f"❌ Помилка синхронізації: {e}")
    # Завантажуємо систему бізнесу
    try:
        await setup_business(bot)
        print(f"✅ Система бізнесу завантажена")
    except Exception as e:
        print(f"❌ Помилка завантаження бізнесу: {e}")
    
    # Завантажуємо казино модуль
    try:
        await setup_casino(bot)
        print(f"✅ Казино модуль завантажений")
    except Exception as e:
        print(f"❌ Помилка завантаження казино: {e}")
    # Запускаємо цикл оновлення меню
    update_game_display.start()


# ============ ТЕСТ СЕРТИФІКАЦІЇ ============

class TestView(discord.ui.View):
    """Вьюха для тесту сертифікації."""

    def __init__(self, user_id: int, question_num: int, answers: dict):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.question_num = question_num
        self.answers = answers
        self.score = answers.get("score", 0)
        self.user_answers = answers.get("user_answers", {})

    async def on_timeout(self):
        """Час тесту вичерпався."""
        pass

# Дані тесту
NEGEV_TEST = [
    {
        "number": 1,
        "question": "Коли вийшов Негев у Counter-Strike?",
        "type": "choice",
        "choices": ["2002", "2005", "1999"],
        "answer": "2002"
    },
    {
        "number": 2,
        "question": "Коли зробили перший скін на Негева?",
        "type": "choice",
        "choices": ["2010", "2013", "2015"],
        "answer": "2013"
    },
    {
        "number": 3,
        "question": "Твоя команда програє, що ти будеш робити?",
        "type": "choice",
        "choices": ["Купляти Негев", "Скажу що нам здаватись", "Візьму собі еко раунд"],
        "answer": "Купляти Негев"
    },
    {
        "number": 4,
        "question": "Скільки коштує Негев?",
        "type": "choice",
        "choices": ["1500", "1700", "2000"],
        "answer": "1700"
    },
    {
        "number": 5,
        "question": "Скільки грошей дають за вбивства когось з Негева?",
        "type": "choice",
        "choices": ["250", "300", "350"],
        "answer": "300"
    },
    {
        "number": 6,
        "question": "Ти лишився 1 в 5, і в тебе є вибір вибрати калаш чи Негев. Що ти вибереш?",
        "type": "choice",
        "choices": ["Калаш", "Негев"],
        "answer": "Негев"
    },
    {
        "number": 7,
        "question": "Твоя команда каже що Негев гімно, що ти будеш робити?",
        "type": "choice",
        "choices": ["Скажу їм що вони кончені", "Куплю Негев", "Куплю Негев та розстреляю свою команду"],
        "answer": "Куплю Негев та розстреляю свою команду"
    }
]

user_test_progress = {}  # Зберігає прогрес тесту {user_id: {"question": N, "score": X, "answers": {}}}

@bot.command(name="certification")
async def certification_command(ctx):
    """Почати тест сертифікації на Негев."""
    user_id = ctx.author.id

    # Перевірити чи користувач вже проходить тест
    if user_id in user_test_progress:
        embed = discord.Embed(
            title="⚠️ Тест вже розпочатий",
            description="Ти вже проходиш тест! Закінчи його перед тим як почати новий.",
            color=COLOR_WARNING
        )
        await ctx.send(embed=embed)
        return

    # Запустити перший вопрос
    user_test_progress[user_id] = {
        "question": 0,
        "score": 0,
        "user_answers": {},
        "channel": ctx.channel,
        "guild_id": ctx.guild.id,
        "message": None,
        "results_message": None
    }

    await show_test_question(user_id)

async def show_test_question(user_id):
    """Показати поточне питання тесту."""
    if user_id not in user_test_progress:
        return

    progress = user_test_progress[user_id]
    q_idx = progress["question"]

    if q_idx >= len(NEGEV_TEST):
        # Тест завершено
        score = progress["score"]
        total = len(NEGEV_TEST)
        percentage = (score / total) * 100

        embed = discord.Embed(
            title="✅ Тест завершено!",
            description=f"Вітаємо з завершенням тесту на сертифікацію Негев!",
            color=COLOR_SUCCESS
        )
        embed.add_field(
            name="📊 Твій результат",
            value=f"**{score}/{total}** правильних відповідей ({percentage:.1f}%)",
            inline=False
        )

        # Видати сертифікат якщо 7/7
        if score == 7:
            embed.add_field(
                name="🏆 СЕРТИФІКАТ ВИДАНО!",
                value="🎖️ Ти отримав офіційний сертифікат експерта на Негев!\nТвоя вмілість з Негева визнана!",
                inline=False
            )
            embed.set_image(url=CERTIFICATE_IMAGE_URL)
            # Видати сертифікат у базі даних
            guild_id = progress.get("guild_id", 1)
            issue_certificate(user_id, guild_id)
        elif percentage >= 80:
            embed.add_field(
                name="🏆 Результат",
                value="**Видатно!** Ти справжній фахівець з Негева!",
                inline=False
            )
        elif percentage >= 60:
            embed.add_field(
                name="👍 Результат",
                value="**Добре!** Ти добре знаєш Негев.",
                inline=False
            )
        else:
            embed.add_field(
                name="📚 Результат",
                value="**Потрібна практика.** Вивчай більше про Негев!",
                inline=False
            )

        # Оновити повідомлення тесту
        if progress["message"]:
            try:
                await progress["message"].edit(embed=embed, view=None)
            except:
                channel = progress["channel"]
                await channel.send(embed=embed)

        # Видалити з прогресу
        del user_test_progress[user_id]
        return

    question = NEGEV_TEST[q_idx]
    embed = discord.Embed(
        title=f"❓ Питання {question['number']}/7",
        description=question["question"],
        color=COLOR_INFO
    )

    channel = progress["channel"]

    if question["type"] == "choice":
        view = ChoiceTestView(user_id, question)

        # Якщо це перше питання - створити нове повідомлення
        if progress["message"] is None:
            message = await channel.send(embed=embed, view=view)
            progress["message"] = message

            # Створити повідомлення з результатами
            results_embed = discord.Embed(
                title="📝 Результати відповідей",
                description="",
                color=COLOR_INFO
            )
            results_message = await channel.send(embed=results_embed)
            progress["results_message"] = results_message
        else:
            # Інакше редагувати існуюче
            try:
                await progress["message"].edit(embed=embed, view=view)
            except:
                message = await channel.send(embed=embed, view=view)
                progress["message"] = message

class ChoiceTestView(discord.ui.View):
    """Вьюха для питань з варіантами."""

    def __init__(self, user_id: int, question: dict):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.question = question
        self.answered = False

        # Додати кнопки для варіантів
        for idx, choice in enumerate(question["choices"]):
            btn = discord.ui.Button(
                label=choice,
                style=discord.ButtonStyle.primary,
                custom_id=f"test_choice_{user_id}_{idx}"
            )
            btn.callback = self.make_choice_callback(idx)
            self.add_item(btn)

    def make_choice_callback(self, choice_idx: int):
        """Створити callback для вибору."""
        async def callback(interaction: discord.Interaction):
            # Перевіряємо чи це той самий користувач
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ Це не твій тест!", ephemeral=True)
                return

            # Перевіряємо чи користувач вже в тесті
            if self.user_id not in user_test_progress:
                await interaction.response.send_message("❌ Тест завершено або скасовано!", ephemeral=True)
                return

            if self.answered:
                await interaction.response.send_message("❌ Ти вже відповів на це питання!", ephemeral=True)
                return

            self.answered = True

            selected_answer = self.question["choices"][choice_idx]

            # Перевірити відповідь
            progress = user_test_progress[self.user_id]
            progress["user_answers"][self.question["number"]] = selected_answer

            is_correct = selected_answer == self.question["answer"]
            if is_correct:
                progress["score"] += 1
                result_text = f"{self.question['number']}) ✅ Правильно"
            else:
                result_text = f"{self.question['number']}) ❌ Неправильно"

            # Оновити повідомлення з результатами
            if progress["results_message"]:
                try:
                    current_description = progress["results_message"].embeds[0].description if progress["results_message"].embeds else ""
                    if current_description:
                        new_description = current_description + "\n" + result_text
                    else:
                        new_description = result_text

                    results_embed = discord.Embed(
                        title="📝 Результати відповідей",
                        description=new_description,
                        color=COLOR_INFO
                    )
                    await progress["results_message"].edit(embed=results_embed)
                except:
                    pass

            await interaction.response.defer()

            # Перейти до наступного питання
            progress["question"] += 1
            await show_test_question(self.user_id)

        return callback


# ============ БАНОЧКА МОЛОЧКА ============

class BankaCompleteView(discord.ui.View):
    """Вьюха після завершення баночки з кнопкою 'Зіграти ще раз'."""

    def __init__(self, user_id: int, server_id: int, ctx_or_interaction):
        super().__init__(timeout=600)
        self.user_id = user_id
        self.server_id = server_id
        self.ctx_or_interaction = ctx_or_interaction

    @discord.ui.button(label="Зіграти ще раз", style=discord.ButtonStyle.success, emoji="🔄")
    async def replay_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Клік на кнопку 'Зіграти ще раз'."""
        # Перевіряємо чи це той самий користувач
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Це не твоя баночка!", ephemeral=True)
            return

        # Скидаємо баночку
        reset_user_banka(self.user_id, self.server_id)

        # Отримуємо оновлені дані баночки
        banka = get_user_banka(self.user_id, self.server_id)

        # Показуємо нову баночку
        embed = discord.Embed(
            title=f"🥛 Баночка молочка {interaction.user.name}",
            description=f"Прогрес: {get_progress_bar(banka['progress'])} **{banka['progress']}%**\n\nКліки потрібно: 4",
            color=COLOR_INFO
        )
        embed.set_image(url=BANKA_IMAGE_URL)

        view = BankaView(self.user_id, self.server_id)
        await interaction.response.edit_message(embed=embed, view=view)

    async def on_timeout(self):
        """Час вичерпався."""
        pass


class BankaView(discord.ui.View):
    """Вьюха для баночки з молочком."""

    def __init__(self, user_id: int, server_id: int):
        super().__init__(timeout=600)  # 10 хвилин
        self.user_id = user_id
        self.server_id = server_id

    @discord.ui.button(label="Видояти", style=discord.ButtonStyle.primary, emoji="🥛")
    async def click_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Клік на кнопку 'Видояти'."""
        # Перевіряємо чи це той самий користувач
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Це не твоя баночка!", ephemeral=True)
            return

        # Додаємо 25% прогресу
        new_progress = add_progress(self.user_id, self.server_id)

        # Отримуємо дані баночки
        banka = get_user_banka(self.user_id, self.server_id)

        # Якщо не завершено - оновлюємо повідомлення
        if new_progress < 100:
            embed = discord.Embed(
                title=f"🥛 Баночка молочка {interaction.user.name}",
                description=f"Прогрес: {get_progress_bar(new_progress)} **{new_progress}%**\n\nКліки ще: {(100 - new_progress) // 25}",
                color=COLOR_INFO
            )
            embed.set_image(url=BANKA_IMAGE_URL)
            
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            # Баночка завершена! Додаємо до лічильника
            add_to_total_completed(self.user_id, self.server_id)
            total_count = get_total_completed_count(self.user_id, self.server_id)
            
            embed = discord.Embed(
                title="✅ Успішно!",
                description=f"🎉 {interaction.user.mention} успішно отримав баночку з молочком!\n\n📊 Всього баночок: **{total_count}**",
                color=COLOR_SUCCESS
            )
            embed.set_image(url=BANKA_COMPLETE_IMAGE_URL)
            
            # Показуємо кнопку "Зіграти ще раз"
            view = BankaCompleteView(self.user_id, self.server_id, interaction)
            await interaction.response.edit_message(embed=embed, view=view)

    async def on_timeout(self):
        """Час для баночки вичерпався."""
        pass


# ============ КОМАНДИ ============

@bot.command(name="start")
async def start_command(ctx):
    """Створити профіль."""
    user_id = ctx.author.id
    server_id = ctx.guild.id

    if get_player(user_id, server_id):
        embed = discord.Embed(
            title=EMOJI_ERROR + " Вже зареєстрований",
            description="У вас вже є профіль на цьому сервері!",
            color=COLOR_ERROR
        )
        await ctx.send(embed=embed)
        return

    if create_player(user_id, server_id):
        embed = discord.Embed(
            title=EMOJI_SUCCESS + " Профіль створено!",
            description=f"Ласкаво просимо в гру, {ctx.author.mention}!",
            color=COLOR_SUCCESS
        )
        embed.add_field(
            name="Стартова статистика",
            value=f"{EMOJI_MONEY} Гроші: 0\n{EMOJI_LEVEL} Рівень: 1\n💸 Дохід/Клік: 1",
            inline=False
        )
        embed.add_field(
            name="Що далі?",
            value="Використай `!profile` щоб переглянути статистику\nКліки на кнопку 💰 щоб заробити гроші!",
            inline=False
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title=EMOJI_ERROR + " Помилка",
            description="Не вдалося створити профіль.",
            color=COLOR_ERROR
        )
        await ctx.send(embed=embed)

@bot.command(name="profile")
async def profile_command(ctx):
    """Показати профіль гравця."""
    user_id = ctx.author.id
    server_id = ctx.guild.id

    player = get_player(user_id, server_id)

    if not player:
        embed = discord.Embed(
            title=EMOJI_ERROR + " Немає профілю",
            description="У вас немає профілю. Використайте `!start`!",
            color=COLOR_ERROR
        )
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(
        title=f"{EMOJI_PROFILE} Профіль {ctx.author.name}",
        color=COLOR_INFO
    )
    if ctx.author.avatar:
        embed.set_thumbnail(url=ctx.author.avatar.url)

    embed.add_field(
        name=f"{EMOJI_MONEY} Баланс",
        value=f"**{player['money']:,}** 💵",
        inline=True
    )
    embed.add_field(
        name=f"{EMOJI_LEVEL} Рівень",
        value=f"**{player['level']}**",
        inline=True
    )
    embed.add_field(
        name=f"{EMOJI_CLOCK} Створено",
        value=datetime.fromisoformat(player["created_at"]).strftime("%d.%m.%Y"),
        inline=True
    )

    embed.add_field(
        name="💸 Дохід за клік",
        value=f"**{player['income_per_click']}**",
        inline=False
    )

    click_upgrade_cost = calculate_upgrade_cost(BASE_CLICK_UPGRADE_COST, player["level"])

    embed.add_field(
        name="Вартість Апгрейду (Наступний Рівень)",
        value=f"💰 Апгрейд Клік: {click_upgrade_cost} 💵",
        inline=False
    )

    await ctx.send(embed=embed)

@bot.command(name="top")
async def top_command(ctx):
    """Показати лідербордус сервера."""
    server_id = ctx.guild.id

    top_players = get_server_top(server_id, limit=10)

    if not top_players:
        embed = discord.Embed(
            title=EMOJI_ERROR + " Немає гравців",
            description="На цьому сервері ще немає гравців!",
            color=COLOR_WARNING
        )
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(
        title=f"{EMOJI_TOP} Топ 10 Гравців - {ctx.guild.name}",
        description="Лідербордус сервера (тільки гроші)",
        color=COLOR_INFO
    )

    leaderboard_text = ""
    for player in top_players:
        try:
            user = await bot.fetch_user(player["user_id"])
            username = user.name
        except:
            username = f"Unknown User ({player['user_id']})"

        if player["position"] == 1:
            medal = "🥇"
        elif player["position"] == 2:
            medal = "🥈"
        elif player["position"] == 3:
            medal = "🥉"
        else:
            medal = "  "

        leaderboard_text += f"{medal} **{player['position']}. {username}**\n"
        leaderboard_text += f"   💵 {player['money']:,} | Lv. {player['level']} | 💸 +{player['income_per_click']}/клік\n"

    embed.description = leaderboard_text
    embed.set_footer(text="Топ 10 гравців на цьому сервері")

    await ctx.send(embed=embed)

@bot.command(name="clicker")
async def clicker_command(ctx):
    """Показати інтерфейс гри."""
    user_id = ctx.author.id
    server_id = ctx.guild.id

    player = get_player(user_id, server_id)

    if not player:
        embed = discord.Embed(
            title=EMOJI_ERROR + " Немає профілю",
            description="У вас немає профілю. Використайте `!start`!",
            color=COLOR_ERROR
        )
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(
        title=f"{EMOJI_CLICK} Гра Клікер - {ctx.author.name}",
        color=COLOR_INFO
    )
    embed.add_field(
        name=f"{EMOJI_MONEY} Баланс",
        value=f"**{player['money']:,}** 💵",
        inline=True
    )
    embed.add_field(
        name=f"{EMOJI_LEVEL} Рівень",
        value=f"**{player['level']}**",
        inline=True
    )
    embed.add_field(
        name="💸 Дохід за клік",
        value=f"**{player['income_per_click']}**",
        inline=True
    )

    # Додаємо прибиль від бізнесу
    business_profit = get_total_profit(user_id, server_id)
    if business_profit > 0:
        embed.add_field(
            name="💼 Прибиль від бізнесу",
            value=f"**{business_profit:.2f}** 💵 в 15 секунд",
            inline=False
        )

    view = GameView(user_id, server_id)

    message = await ctx.send(embed=embed, view=view)

    # Зберігаємо посилання на повідомлення для оновлення
    active_games[(user_id, server_id)] = (message, ctx.channel)

@bot.command(name="banochka")
async def banochka_command(ctx):
    """Показати баночку молочка."""
    user_id = ctx.author.id
    server_id = ctx.guild.id

    # Отримуємо дані баночки
    banka = get_user_banka(user_id, server_id)

    # Якщо баночка вже завершена, скидаємо її для нової гри
    if banka['completed']:
        reset_user_banka(user_id, server_id)
        banka = get_user_banka(user_id, server_id)

    # Створюємо embed
    embed = discord.Embed(
        title=f"🥛 Баночка молочка {ctx.author.name}",
        description=f"Прогрес: {get_progress_bar(banka['progress'])} **{banka['progress']}%**\n\nКліки потрібно: 4",
        color=COLOR_INFO
    )

    embed.set_image(url=BANKA_IMAGE_URL)
    view = BankaView(user_id, server_id)

    await ctx.send(embed=embed, view=view)

@bot.command(name="stats_banochka")
async def stats_banochka_command(ctx):
    """Показати статистику баночок юзера."""
    user_id = ctx.author.id
    server_id = ctx.guild.id

    # Отримуємо дані баночки
    banka = get_user_banka(user_id, server_id)
    total_completed = get_total_completed_count(user_id, server_id)

    # Створюємо embed зі статистикою
    embed = discord.Embed(
        title=f"🥛 Статистика баночок - {ctx.author.name}",
        color=COLOR_INFO
    )

    embed.add_field(
        name="📊 Всього завершено баночок",
        value=f"**{total_completed}** 🥛",
        inline=False
    )

    embed.add_field(
        name="📈 Поточний прогрес",
        value=f"{get_progress_bar(banka['progress'])} **{banka['progress']}%**",
        inline=False
    )

    embed.add_field(
        name="⏰ Перша баночка створена",
        value=datetime.fromisoformat(banka['created_at']).strftime("%d.%m.%Y %H:%M"),
        inline=False
    )

    if total_completed > 0:
        embed.add_field(
            name="🎯 Досяг",
            value="✅ Вже завершив хоча б одну баночку!",
            inline=False
        )

    if ctx.author.avatar:
        embed.set_thumbnail(url=ctx.author.avatar.url)

    await ctx.send(embed=embed)

# ============ КНОПКИ ============

class GameView(discord.ui.View):
    """Вьюха з кнопками гри."""

    def __init__(self, user_id: int, server_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.server_id = server_id

    @discord.ui.button(
        label="Клік",
        emoji=EMOJI_CLICK,
        style=discord.ButtonStyle.success,
        custom_id="btn_click"
    )
    async def click_button(self, interaction: discord.Interaction, item: discord.ui.Button):
        """Кнопка клік."""
        user_id = interaction.user.id
        server_id = interaction.guild.id

        if user_id != self.user_id:
            embed = discord.Embed(
                title=EMOJI_ERROR + " Не твоя кнопка",
                description="Ти не можеш користуватись кнопкою іншої людини!",
                color=COLOR_ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Перевірка cooldown
        key = (user_id, server_id)
        current_time = time.time()

        if key in click_cooldowns:
            last_click = click_cooldowns[key]
            if current_time - last_click < CLICK_COOLDOWN:
                remaining = round(CLICK_COOLDOWN - (current_time - last_click), 2)
                embed = discord.Embed(
                    title=EMOJI_ERROR + " Cooldown",
                    description=f"Чекай {remaining}s перед наступним кліком!",
                    color=COLOR_ERROR
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

        player = get_player(user_id, server_id)
        if not player:
            embed = discord.Embed(
                title=EMOJI_ERROR + " Немає профілю",
                description="У тебе немає профілю!",
                color=COLOR_ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        earned = player["income_per_click"]
        add_money(user_id, server_id, earned)
        update_click_time(user_id, server_id, current_time)
        click_cooldowns[key] = current_time

        player = get_player(user_id, server_id)

        embed = discord.Embed(
            title=f"{EMOJI_CLICK} Гра Клікер - {interaction.user.name}",
            color=COLOR_INFO
        )
        embed.add_field(
            name=f"{EMOJI_MONEY} Баланс",
            value=f"**{player['money']:,}** 💵",
            inline=True
        )
        embed.add_field(
            name="📊 Рівень Кліку",
            value=f"**{player['income_per_click']}**",
            inline=True
        )
        embed.add_field(
            name="💸 Дохід за клік",
            value=f"**{player['income_per_click']}**",
            inline=True
        )

        # Додаємо прибиль від бізнесу
        business_profit = get_total_profit(user_id, server_id)
        if business_profit > 0:
            embed.add_field(
                name="💼 Прибиль від бізнесу",
                value=f"**{business_profit:.2f}** 💵 в 15 секунд",
                inline=False
            )

        await interaction.response.defer()
        await interaction.message.edit(embed=embed)

    @discord.ui.button(
        label="Апгрейд Клік",
        emoji=EMOJI_UPGRADE,
        style=discord.ButtonStyle.primary,
        custom_id="btn_upgrade_click"
    )
    async def upgrade_click_button(self, interaction: discord.Interaction, item: discord.ui.Button):
        """Кнопка апгрейду кліка."""
        user_id = interaction.user.id
        server_id = interaction.guild.id

        if user_id != self.user_id:
            embed = discord.Embed(
                title=EMOJI_ERROR + " Не твоя кнопка",
                description="Ти не можеш користуватись кнопкою іншої людини!",
                color=COLOR_ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        player = get_player(user_id, server_id)
        if not player:
            embed = discord.Embed(
                title=EMOJI_ERROR + " Немає профілю",
                description="У тебе немає профілю!",
                color=COLOR_ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        cost = calculate_upgrade_cost(BASE_CLICK_UPGRADE_COST, player["level"])

        if player["money"] < cost:
            embed = discord.Embed(
                title=EMOJI_ERROR + " Не вистачає грошей",
                description=f"Тобі бракує {cost - player['money']} 💵",
                color=COLOR_ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if upgrade_income_per_click(user_id, server_id):
            player = get_player(user_id, server_id)

            embed = discord.Embed(
                title=f"{EMOJI_CLICK} Гра Клікер - {interaction.user.name}",
                color=COLOR_INFO
            )
            embed.add_field(
                name=f"{EMOJI_MONEY} Баланс",
                value=f"**{player['money']:,}** 💵",
                inline=True
            )
            embed.add_field(
                name="📊 Рівень Кліку",
                value=f"**{player['income_per_click']}**",
                inline=True
            )
            embed.add_field(
                name="💸 Дохід за клік",
                value=f"**{player['income_per_click']}**",
                inline=True
            )

            # Додаємо прибиль від бізнесу
            business_profit = get_total_profit(user_id, server_id)
            if business_profit > 0:
                embed.add_field(
                    name="💼 Прибиль від бізнесу",
                    value=f"**{business_profit:.2f}** 💵 в 15 секунд",
                    inline=False
                )

            await interaction.response.defer()
            await interaction.message.edit(embed=embed)
        else:
            embed = discord.Embed(
                title=EMOJI_ERROR + " Помилка Апгрейду",
                description="Щось пішло не так!",
                color=COLOR_ERROR
            )
            await interaction.response.defer()
            await interaction.message.edit(embed=embed)

# ============ ФОНОВИЙ ЦИКЛ (ОНОВЛЕННЯ МЕНЮ) ============

@tasks.loop(seconds=2)
async def update_game_display():
    """Оновлює меню клікера в реальному часі з інформацією про прибиль від бізнесу."""
    try:
        games_to_remove = []
        for (user_id, server_id), (message, channel) in active_games.items():
            try:
                player = get_player(user_id, server_id)
                if player:
                    embed = discord.Embed(
                        title=f"{EMOJI_CLICK} Гра Клікер",
                        color=COLOR_INFO
                    )
                    embed.add_field(
                        name=f"{EMOJI_MONEY} Баланс",
                        value=f"**{player['money']:,}** 💵",
                        inline=True
                    )
                    embed.add_field(
                        name=f"{EMOJI_LEVEL} Рівень",
                        value=f"**{player['level']}**",
                        inline=True
                    )
                    embed.add_field(
                        name="💸 Дохід за клік",
                        value=f"**{player['income_per_click']}**",
                        inline=True
                    )

                    # Додаємо загальну прибиль від всіх бізнесів
                    business_profit = get_total_profit(user_id, server_id)
                    if business_profit > 0:
                        embed.add_field(
                            name="💼 Прибиль від бізнесу",
                            value=f"**{business_profit:.2f}** 💵 в 15 секунд",
                            inline=False
                        )

                    await message.edit(embed=embed)
                else:
                    games_to_remove.append((user_id, server_id))
            except Exception as e:
                # Якщо помилка - видаляємо гру з активних
                games_to_remove.append((user_id, server_id))

        # Видаляємо неактивні ігри
        for key in games_to_remove:
            if key in active_games:
                del active_games[key]

    except Exception as e:
        print(f"❌ Помилка в оновленні меню: {e}")

@update_game_display.before_loop
async def before_update_game_display():
    """Чекає коли бот буде готовий перед стартом циклу."""
    await bot.wait_until_ready()

# ============ ЗАПУСК БОТА ============

if __name__ == "__main__":
    bot.run(TOKEN)





