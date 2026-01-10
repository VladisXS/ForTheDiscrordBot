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

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

OWNER_ID = 
admin_ids = []

ACTIONS_FILE = "actions.json"
user_warnings = {}
last_arizona_location = {}

ARIZONA_CHANNEL_ID =   # ← твій канал для публікації локацій

def load_actions():
    if not os.path.exists(ACTIONS_FILE):
        return {}
    with open(ACTIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_actions(actions):
    with open(ACTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(actions, f, ensure_ascii=False, indent=2)

actions = load_actions()

@bot.event
async def on_ready():
    print(f"🔵 Бот запущено як {bot.user.name}")
    bot.loop.create_task(track_arizona_locations())

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

@bot.event
async def on_member_update(before, after):
    if before.activities != after.activities:
        for activity in after.activities:
            if hasattr(activity, 'name') and activity.name and "arizona" in activity.name.lower():
                if not any("arizona" in (a.name or "").lower() for a in before.activities if hasattr(a, 'name')):
                    channel = bot.get_channel(ARIZONA_CHANNEL_ID)
                    if channel and channel.permissions_for(after.guild.me).send_messages:
                        await channel.send(f"🎮 <@{after.id}> грає в Arizona RP!")
                break

@bot.event
async def on_presence_update(before, after):
    if before.activities != after.activities:
        before_arizona = next((a for a in before.activities if hasattr(a, "name") and a.name and "arizona" in a.name.lower()), None)
        after_arizona = next((a for a in after.activities if hasattr(a, "name") and a.name and "arizona" in a.name.lower()), None)

        channel = bot.get_channel(ARIZONA_CHANNEL_ID)
        if not channel or not channel.permissions_for(after.guild.me).send_messages:
            return

        if not before_arizona and after_arizona:
            location = after_arizona.details or after_arizona.state or "Невідома локація"
            await channel.send(f"🎮 <@{after.id}> зайшов в Arizona RP\n📍 Локація: **{location}**")
        elif before_arizona and not after_arizona:
            location = before_arizona.details or before_arizona.state or "Невідома локація"
            await channel.send(f"❌ <@{after.id}> вийшов з Arizona RP\n📍 Був у локації: **{location}**")

@bot.event
async def on_voice_state_update(member, before, after):
    channel = bot.get_channel(ARIZONA_CHANNEL_ID)
    if not channel or not channel.permissions_for(member.guild.me).send_messages:
        return

    if before.channel is None and after.channel is not None:
        await channel.send(f"👤 <@{member.id}> зайшов у голосовий канал **{after.channel.name}**!")
    elif before.channel is not None and after.channel is None:
        await channel.send(f"👋 <@{member.id}> вийшов з голосового каналу **{before.channel.name}**!")

@bot.command()
async def apn(ctx, to: discord.Member):
    if ctx.author.id == OWNER_ID:
        if to.id not in admin_ids:
            admin_ids.append(to.id)
            await ctx.send(f"✅ {to.mention} тепер має доступ до адмін панелі.")
        else:
            await ctx.send(f"⚠️ {to.mention} вже є адміністратором.")
    else:
        await ctx.send("⛔ Тільки власник може видавати доступ до адмінки.")

@bot.command()
async def apnk(ctx, to: discord.Member):
    if ctx.author.id != OWNER_ID:
        await ctx.send("⛔ Тільки власник може забирати доступ до адмінки.")
        return

    if to.id in admin_ids:
        admin_ids.remove(to.id)
        await ctx.send(f"❌ Адмін-панель забрана у {to.mention}.")
    else:
        await ctx.send(f"⚠️ {to.mention} не є адміністратором.")

@bot.command()
async def addc(ctx, *, msg: str):
    if ctx.author.id != OWNER_ID and ctx.author.id not in admin_ids:
        await ctx.send("⛔ Ти не маєш доступу до адмін-команд.")
        return

    if '":' not in msg:
        await ctx.send("❌ Формат неправильний. Використовуй: `!addc дія\": \"{author} щось там {target}`")
        return

    try:
        key, template = msg.split('":', 1)
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

@bot.command(name="тест")
async def test_command(ctx):
    await ctx.send("Бот працює правильно!")

@bot.command(name="активність")
async def check_activity(ctx, member: discord.Member = None):
    member = member or ctx.author
    if member.activities:
        activities = [f"- {a.name}" for a in member.activities if hasattr(a, 'name') and a.name]
        await ctx.send(f"**{member.display_name}** зараз:\n" + "\n".join(activities) if activities else f"**{member.display_name}** нічого не робить")
    else:
        await ctx.send(f"**{member.display_name}** нічого не робить")

@bot.command(name="help")
async def help_command(ctx):
    if not actions:
        await ctx.send("❌ Немає доступних команд.")
        return

    embed = discord.Embed(
        title="📜 Список доступних дій",
        description="Ось усі доступні дії, які реагують на згадування користувача та ключові слова.",
        color=discord.Color.blue()
    )

    for action, template in actions.items():
        embed.add_field(name=f"🔹 `{action}`", value=template, inline=False)

    embed.set_footer(text="Використовуй ці ключові слова при згадуванні когось у повідомленні.")
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

# === Arizona Location Tracker ===
async def track_arizona_locations():
    await bot.wait_until_ready()
    while not bot.is_closed():
        channel = bot.get_channel(ARIZONA_CHANNEL_ID)
        if not channel:
            await asyncio.sleep(60)
            continue

        for guild in bot.guilds:
            for member in guild.members:
                if member.bot:
                    continue
                for activity in member.activities:
                    if hasattr(activity, "name") and activity.name and "arizona" in activity.name.lower():
                        location = activity.details or activity.state or "Невідома локація"
                        prev_location = last_arizona_location.get(member.id)
                        if location != prev_location:
                            last_arizona_location[member.id] = location
                            if channel.permissions_for(guild.me).send_messages:
                                await channel.send(f"📍 <@{member.id}> зараз у локації: **{location}**")
                        break
        await asyncio.sleep(60)  # чекати 60 секунд

# ==== Запуск ====
keep_alive()
bot.run(TOKEN)
