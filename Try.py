import discord
from discord.ext import commands
import json
import os
import asyncio
from flask import Flask
from threading import Thread

# === Flask Keep-Alive ===
app = Flask('')


@app.route('/')
def home():
    return "Я живий! 🟢"


def run():
    app.run(host='0.0.0.0', port=8000)


def keep_alive():
    t = Thread(target=run)
    t.start()


# === Discord Bot ===
TOKEN = ""

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix=["!", "/"], intents=intents, help_command=None)

OWNER_ID = 
admin_ids = []

ACTIONS_FILE = "actions.json"
ADMINS_FILE = "admins.json"
user_warnings = {}


def load_actions():
    if not os.path.exists(ACTIONS_FILE):
        return {}
    with open(ACTIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_actions(actions):
    with open(ACTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(actions, f, ensure_ascii=False, indent=2)


def load_admins():
    if not os.path.exists(ADMINS_FILE):
        return []
    with open(ADMINS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_admins():
    with open(ADMINS_FILE, "w", encoding="utf-8") as f:
        json.dump(admin_ids, f, ensure_ascii=False, indent=2)


actions = load_actions()
admin_ids = load_admins()


@bot.event
async def on_ready():
    print(f"🔵 Бот запущено як {bot.user.name}")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

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

    if message.content.lower() == "привіт":
        await message.channel.send("Привіт!")

    await bot.process_commands(message)


# === Обробка помилок ===
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        if ctx.command.name == "setadm":
            await ctx.send("❌ Використання: `!setadm @користувач`")
        elif ctx.command.name == "deladmin":
            await ctx.send("❌ Використання: `/deladmin @користувач`")
        elif ctx.command.name == "addc":
            await ctx.send("❌ Використання: `!addc \"дія\": \"{author} робить щось {target}\"`")
        elif ctx.command.name in ["apn", "apnk"]:
            await ctx.send(f"❌ Використання: `!{ctx.command.name} @користувач`")
        else:
            await ctx.send(f"❌ Не вистачає аргументу для команди `{ctx.command.name}`")
    elif isinstance(error, commands.CommandNotFound):
        pass  # Ігноруємо невідомі команди
    else:
        print(f"Помилка: {error}")


@bot.event
async def on_voice_state_update(member, before, after):
    pass  # Можна додати логіку для голосових каналів тут


# === Нові команди для керування адмінами ===
@bot.command(name="setadm")
async def set_admin(ctx, member: discord.Member = None):
    """Додати адміністратора (тільки власник)"""
    if member is None:
        await ctx.send("❌ Використання: `!setadm @користувач`")
        return

    if ctx.author.id != OWNER_ID:
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
    """Видалити адміністратора (тільки власник)"""
    if member is None:
        await ctx.send("❌ Використання: `/deladmin @користувач`")
        return

    if ctx.author.id != OWNER_ID:
        await ctx.send("⛔ Тільки власник може видаляти адміністраторів.")
        return

    if member.id in admin_ids:
        admin_ids.remove(member.id)
        save_admins()
        await ctx.send(f"❌ {member.mention} більше не адміністратор.")
    else:
        await ctx.send(f"⚠️ {member.mention} не є адміністратором.")


# === Старі команди (залишив для сумісності) ===
@bot.command()
async def apn(ctx, to: discord.Member = None):
    if to is None:
        await ctx.send("❌ Використання: `!apn @користувач`")
        return

    if ctx.author.id == OWNER_ID:
        if to.id not in admin_ids:
            admin_ids.append(to.id)
            save_admins()
            await ctx.send(f"✅ {to.mention} тепер має доступ до адмін панелі.")
        else:
            await ctx.send(f"⚠️ {to.mention} вже є адміністратором.")
    else:
        await ctx.send("⛔ Тільки власник може видавати доступ до адмінки.")


@bot.command()
async def apnk(ctx, to: discord.Member = None):
    if to is None:
        await ctx.send("❌ Використання: `!apnk @користувач`")
        return

    if ctx.author.id != OWNER_ID:
        await ctx.send("⛔ Тільки власник може забирати доступ до адмінки.")
        return

    if to.id in admin_ids:
        admin_ids.remove(to.id)
        save_admins()
        await ctx.send(f"❌ Адмін-панель забрана у {to.mention}.")
    else:
        await ctx.send(f"⚠️ {to.mention} не є адміністратором.")


@bot.command()
async def addc(ctx, *, msg: str = None):
    """Додати нову дію (тільки власник та адміни)"""
    if msg is None:
        await ctx.send(
            "❌ Використання: `!addc \"дія\": \"{author} робить щось {target}\"`\nПриклад: `!addc \"обійняв\": \"{author} обійняв {target}\"`")
        return

    if ctx.author.id != OWNER_ID and ctx.author.id not in admin_ids:
        await ctx.send("⛔ Ти не маєш доступу до адмін-команд.")
        return

    if '":' not in msg and '": ' not in msg:
        await ctx.send("❌ Формат неправильний. Використовуй: `!addc \"дія\": \"{author} щось там {target}\"`")
        return

    try:
        # Спробуємо різні варіанти розділювача
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
async def delete_command(ctx, action: str = None):
    """Видалити дію (тільки власник та адміни)"""
    if action is None:
        await ctx.send("❌ Використання: `!delc назва_дії`")
        return

    if ctx.author.id != OWNER_ID and ctx.author.id not in admin_ids:
        await ctx.send("⛔ Ти не маєш доступу до адмін-команд.")
        return

    action = action.lower()
    if action in actions:
        del actions[action]
        save_actions(actions)
        await ctx.send(f"✅ Дія \"{action}\" видалена.")
    else:
        await ctx.send(f"❌ Дія \"{action}\" не знайдена.")


@bot.command(name="тест")
async def test_command(ctx):
    await ctx.send("Бот працює правильно!")


@bot.command(name="активність")
async def check_activity(ctx, member: discord.Member = None):
    member = member or ctx.author
    if member.activities:
        activities = [f"- {a.name}" for a in member.activities if hasattr(a, 'name') and a.name]
        await ctx.send(f"**{member.display_name}** зараз:\n" + "\n".join(
            activities) if activities else f"**{member.display_name}** нічого не робить")
    else:
        await ctx.send(f"**{member.display_name}** нічого не робить")


@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="📜 Довідка по боту",
        description="Список команд та функцій бота",
        color=discord.Color.blue()
    )

    # Команди для власника
    owner_cmds = (
        "`!setadm @user` - додати адміна\n"
        "`/deladmin @user` - видалити адміна\n"
        "`!apn @user` - додати адміна (старий спосіб)\n"
        "`!apnk @user` - видалити адміна (старий спосіб)"
    )
    embed.add_field(name="👑 Команди власника", value=owner_cmds, inline=False)

    # Команди для адмінів
    admin_cmds = (
        "`!addc \"дія\": \"{author} текст {target}\"` - додати дію\n"
        "`!delc назва` - видалити дію\n"
        "`!admins` - список адмінів"
    )
    embed.add_field(name="🛡️ Команди адмінів", value=admin_cmds, inline=False)

    # Звичайні команди
    user_cmds = (
        "`!тест` - перевірити роботу бота\n"
        "`!активність [@user]` - подивитись активність\n"
        "`!help` - ця довідка"
    )
    embed.add_field(name="👤 Команди користувачів", value=user_cmds, inline=False)

    # Список дій
    if actions:
        actions_list = ", ".join([f"`{a}`" for a in actions.keys()])
        embed.add_field(name="✨ Доступні дії", value=actions_list, inline=False)
        embed.add_field(
            name="💡 Як використовувати дії?",
            value="Напиши повідомлення з ключовим словом та згадай (@) користувача",
            inline=False
        )

    embed.set_footer(text=f"Бот: {bot.user.name}")
    await ctx.send(embed=embed)


@bot.command()
async def admins(ctx):
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


# ==== Запуск ====
keep_alive()
bot.run(TOKEN)
