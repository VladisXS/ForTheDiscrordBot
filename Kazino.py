"""
Discord Casino Module - Азартні ігри з вибором множника
"""

import discord
from discord.ext import commands
from discord import app_commands
import random
import json
from clicker import get_player, set_player_money, load_data, save_data

# Файл для зберігання казино статистики
CASINO_DATA_FILE = "casino_data.json"

def load_casino_data():
    """Завантажити дані казино."""
    try:
        with open(CASINO_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"players": {}}

def save_casino_data(data):
    """Зберегти дані казино."""
    with open(CASINO_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_user_key(user_id, server_id):
    """Отримати ключ користувача."""
    return f"{user_id}_{server_id}"

def reset_casino_stats(user_id: int, server_id: int) -> bool:
    """Скидує казино статистику гравця. Повертає True якщо успішно."""
    data = load_casino_data()
    user_key = get_user_key(user_id, server_id)

    if user_key in data["players"]:
        del data["players"][user_key]
        save_casino_data(data)
        return True
    return True  # Повертаємо True навіть якщо немає статистики

# ============ МЕНЮ КАЗИНО ============

class CasinoResultView(discord.ui.View):
    """Кнопки для результату гри"""
    def __init__(self, user_id, server_id, bet_amount, bot_instance):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.server_id = server_id
        self.bet_amount = bet_amount
        self.bot = bot_instance
    
    @discord.ui.button(label="🔄 Ще раз", style=discord.ButtonStyle.success)
    async def play_again_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Грати з тією ж ставкою"""
        await interaction.response.defer()
        
        # Показати вибір кольору з тією ж ставкою
        view = CasinoBetTypeView(self.user_id, self.server_id, self.bet_amount)
        embed = discord.Embed(
            title="🎰 Казино - Вибір кольору",
            description=f"Твоя ставка: **{self.bet_amount:,}** 💵\n\nВибери на який колір хочеш ставити:",
            color=0xFFD700
        )
        await interaction.edit_original_response(embed=embed, view=view)
    
    @discord.ui.button(label="💰 Змінити ставку", style=discord.ButtonStyle.primary)
    async def change_bet_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Змінити ставку та грати ще раз"""
        await interaction.response.defer()
        
        embed = discord.Embed(
            title="🎰 Казино - Нова ставка",
            description="Введи нову суму ставки (мінімум 100):",
            color=0xFFD700
        )
        
        view = CasinoNewBetView(self.user_id, self.server_id)
        await interaction.edit_original_response(embed=embed, view=view)

class CasinoNewBetView(discord.ui.View):
    """View для введення нової ставки"""
    def __init__(self, user_id, server_id):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.server_id = server_id
    
    @discord.ui.button(label="100", style=discord.ButtonStyle.primary)
    async def bet_100_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_bet(interaction, 100)
    
    @discord.ui.button(label="500", style=discord.ButtonStyle.primary)
    async def bet_500_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_bet(interaction, 500)
    
    @discord.ui.button(label="1000", style=discord.ButtonStyle.primary)
    async def bet_1000_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_bet(interaction, 1000)
    
    @discord.ui.button(label="Власна сума", style=discord.ButtonStyle.success)
    async def bet_custom_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CasinoAmountModal(self.user_id, self.server_id, None)
        await interaction.response.send_modal(modal)
    
    async def process_bet(self, interaction: discord.Interaction, bet_amount: int):
        """Обробити ставку"""
        await interaction.response.defer()
        
        # Отримати гроші користувача
        player = get_player(self.user_id, self.server_id)
        if not player:
            embed = discord.Embed(
                title="❌ Помилка",
                description="Ти ще не грав у клікер. Спочатку клікай!",
                color=0xE74C3C
            )
            await interaction.edit_original_response(embed=embed, view=None)
            return
        
        current_money = player["money"]
        
        if current_money < bet_amount:
            embed = discord.Embed(
                title="❌ Недостатньо грошей",
                description=f"У тебе: **{current_money:,}** 💵\nНеобхідно: **{bet_amount:,}** 💵",
                color=0xE74C3C
            )
            await interaction.edit_original_response(embed=embed, view=None)
            return
        
        # Показати вибір типу ставки
        view = CasinoBetTypeView(self.user_id, self.server_id, bet_amount)
        embed = discord.Embed(
            title="🎰 Казино - Вибір кольору",
            description=f"Твоя ставка: **{bet_amount:,}** 💵\n\nВибери на який колір хочеш ставити:",
            color=0xFFD700
        )
        await interaction.edit_original_response(embed=embed, view=view)

class CasinoAmountModal(discord.ui.Modal):
    """Модаль для введення суми ставки"""
    def __init__(self, user_id, server_id, bot_instance):
        super().__init__(title="Казино - Ставка", timeout=300)
        self.user_id = user_id
        self.server_id = server_id
        self.bot = bot_instance
        
        self.amount_input = discord.ui.TextInput(
            label="Введи суму ставки",
            placeholder="Мінімум 100",
            required=True,
            min_length=1,
            max_length=20
        )
        self.add_item(self.amount_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Обробка введення суми"""
        await interaction.response.defer()
        
        try:
            bet_amount = int(self.amount_input.value)
            
            # Перевірка мінімальної суми
            if bet_amount < 100:
                embed = discord.Embed(
                    title="❌ Помилка",
                    description="Мінімальна ставка: 100 грошей!",
                    color=0xE74C3C
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Отримати гроші користувача
            player = get_player(self.user_id, self.server_id)
            if not player:
                embed = discord.Embed(
                    title="❌ Помилка",
                    description="Ти ще не грав у клікер. Спочатку клікай!",
                    color=0xE74C3C
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            current_money = player["money"]
            
            if current_money < bet_amount:
                embed = discord.Embed(
                    title="❌ Недостатньо грошей",
                    description=f"У тебе: **{current_money:,}** 💵",
                    color=0xE74C3C
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Показати вибір типу ставки
            view = CasinoBetTypeView(self.user_id, self.server_id, bet_amount)
            embed = discord.Embed(
                title="🎰 Казино - Вибір кольору",
                description=f"Твоя ставка: **{bet_amount:,}** 💵\n\nВибери на який колір хочеш ставити:",
                color=0xFFD700
            )
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except ValueError:
            embed = discord.Embed(
                title="❌ Помилка",
                description="Введи число!",
                color=0xE74C3C
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

class CasinoBetTypeView(discord.ui.View):
    """Вибір кольору ставки"""
    def __init__(self, user_id, server_id, bet_amount):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.server_id = server_id
        self.bet_amount = bet_amount
    
    @discord.ui.button(label="🔴 Червоне", style=discord.ButtonStyle.red)
    async def red_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_multiplier_menu(interaction, "red")
    
    @discord.ui.button(label="⚫ Чорне", style=discord.ButtonStyle.secondary)
    async def black_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_multiplier_menu(interaction, "black")
    
    @discord.ui.button(label="🟡 Жовтий", style=discord.ButtonStyle.success)
    async def yellow_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_multiplier_menu(interaction, "yellow")
    
    async def show_multiplier_menu(self, interaction: discord.Interaction, bet_type: str):
        """Показати меню вибору множника"""
        await interaction.response.defer()
        
        bet_type_name = "Червоний" if bet_type == "red" else "Чорний" if bet_type == "black" else "Жовтий"
        
        embed = discord.Embed(
            title="🎰 Вибір множника",
            description=f"Твій вибір: **{bet_type_name}**\n"
                        f"Ставка: **{self.bet_amount:,}** 💵\n\n"
                        f"**Вибери множник** (більший множник = менший шанс):\n\n"
                        f"x2 - 40% шанс\n"
                        f"x3 - 31% шанс\n"
                        f"x5 - 20% шанс\n"
                        f"x10 - 10% шанс",
            color=0xFFD700
        )
        
        view = CasinoMultiplierView(self.user_id, self.server_id, self.bet_amount, bet_type)
        await interaction.edit_original_response(embed=embed, view=view)

class CasinoMultiplierView(discord.ui.View):
    """Вибір множника"""
    def __init__(self, user_id, server_id, bet_amount, bet_type):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.server_id = server_id
        self.bet_amount = bet_amount
        self.bet_type = bet_type
    
    @discord.ui.button(label="x2 (40%)", style=discord.ButtonStyle.success)
    async def mult_2x_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.spin_roulette(interaction, 2, 40)
    
    @discord.ui.button(label="x3 (31%)", style=discord.ButtonStyle.primary)
    async def mult_3x_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.spin_roulette(interaction, 3, 31)
    
    @discord.ui.button(label="x5 (20%)", style=discord.ButtonStyle.danger)
    async def mult_5x_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.spin_roulette(interaction, 5, 20)
    
    @discord.ui.button(label="x10 (10%)", style=discord.ButtonStyle.secondary)
    async def mult_10x_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.spin_roulette(interaction, 10, 10)
    
    async def spin_roulette(self, interaction: discord.Interaction, multiplier: int, win_chance_percent: int):
        """Запустити рулетку"""
        await interaction.response.defer()
        
        # Перевірити баланс ще раз
        player = get_player(self.user_id, self.server_id)
        if not player or player["money"] < self.bet_amount:
            await interaction.edit_original_response(content="❌ У тебе більше немає достатньо грошей!")
            return
        
        # Відняти ставку
        new_balance = player["money"] - self.bet_amount
        set_player_money(self.user_id, self.server_id, new_balance)
        
        # Рандом результат
        win_chance = random.randint(1, 100)
        is_win = win_chance <= win_chance_percent
        
        # Рахунок результату
        if is_win:
            winnings = int(self.bet_amount * multiplier)
            final_balance = new_balance + winnings
            set_player_money(self.user_id, self.server_id, final_balance)
            
            # Повідомлення про перемогу
            bet_type_name = "Червоний" if self.bet_type == "red" else "Чорний" if self.bet_type == "black" else "Жовтий"
            result_emoji = "✅"
            result_text = f"Ти виграв на **{bet_type_name}**!"
            
            embed = discord.Embed(
                title="🎰 КАЗИНО - ПЕРЕМОГА!",
                description=f"{result_emoji} {result_text}\n\n"
                            f"**Ставка:** {self.bet_amount:,} 💵\n"
                            f"**Множник:** x{multiplier}\n"
                            f"**Виграш:** {winnings:,} 💵\n"
                            f"**Новий баланс:** {final_balance:,} 💵",
                color=0x2ECC71
            )
            embed.set_footer(text=f"Шанс виграшу: {win_chance_percent}%")
            
        else:
            final_balance = new_balance
            
            embed = discord.Embed(
                title="🎰 КАЗИНО - ПОРАЗКА",
                description=f"❌ На цей раз не пощастило...\n\n"
                            f"**Ставка:** {self.bet_amount:,} 💵\n"
                            f"**Множник:** x{multiplier}\n"
                            f"**Виграш:** 0 💵\n"
                            f"**Новий баланс:** {final_balance:,} 💵",
                color=0xE74C3C
            )
            embed.set_footer(text=f"Шанс виграшу був: {win_chance_percent}%")
        
        # Зберегти статистику
        casino_data = load_casino_data()
        user_key = get_user_key(self.user_id, self.server_id)
        
        if user_key not in casino_data["players"]:
            casino_data["players"][user_key] = {"wins": 0, "losses": 0, "total_bet": 0}
        
        casino_data["players"][user_key]["total_bet"] += self.bet_amount
        if is_win:
            casino_data["players"][user_key]["wins"] += 1
        else:
            casino_data["players"][user_key]["losses"] += 1
        
        save_casino_data(casino_data)
        
        # Додати кнопки результату
        view = CasinoResultView(self.user_id, self.server_id, self.bet_amount, None)
        await interaction.edit_original_response(embed=embed, view=view)

# ============ КОМАНДА КАЗИНО ============

async def setup_casino(bot: commands.Bot):
    """Налаштувати казино модуль"""
    
    @bot.command(name="kazino")
    async def casino_command(ctx):
        """🎰 Вступи в казино!"""
        
        # Перевірити чи користувач має профіль
        player = get_player(ctx.author.id, ctx.guild.id)
        if not player:
            embed = discord.Embed(
                title="❌ Ты ще не грав!",
                description="Спочатку клікай у клікері: `!click`",
                color=0xE74C3C
            )
            await ctx.send(embed=embed)
            return
        
        # Показати меню казино
        embed = discord.Embed(
            title="🎰 КАЗИНО",
            description=f"Ласкаво просимо в казино!\n\n"
                        f"**Твій баланс:** {player['money']:,} 💵\n\n"
                        f"**Як працює казино:**\n"
                        f"1️⃣ Введи суму ставки (мінімум 100)\n"
                        f"2️⃣ Вибери колір: 🔴 Червоне, ⚫ Чорне, 🟡 Жовтий\n"
                        f"3️⃣ Вибери множник своєї ставки (x2, x3, x5, x10)\n"
                        f"4️⃣ Більший множник = менший шанс виграшу\n\n"
                        f"⚠️ Граючи в казино, ти ризикуєш своїми грошима!",
            color=0xFFD700
        )
        embed.set_footer(text="Удачі! 🍀")
        
        # Кнопка для початку
        view = discord.ui.View()
        button = discord.ui.Button(label="Розпочати гру", style=discord.ButtonStyle.success)
        
        async def start_game(interaction: discord.Interaction):
            if interaction.user.id != ctx.author.id:
                await interaction.response.send_message("❌ Це не твоя гра!", ephemeral=True)
                return
            
            modal = CasinoAmountModal(ctx.author.id, ctx.guild.id, bot)
            await interaction.response.send_modal(modal)
        
        button.callback = start_game
        view.add_item(button)
        
        await ctx.send(embed=embed, view=view)
    
    @bot.command(name="kazino_stats")
    async def casino_stats_command(ctx):
        """📊 Твоя казино статистика"""
        
        casino_data = load_casino_data()
        user_key = get_user_key(ctx.author.id, ctx.guild.id)
        
        if user_key not in casino_data["players"]:
            embed = discord.Embed(
                title="📊 Казино Статистика",
                description="Ти ще не грав у казино!",
                color=0x3498DB
            )
            await ctx.send(embed=embed)
            return
        
        stats = casino_data["players"][user_key]
        total_games = stats["wins"] + stats["losses"]
        win_rate = (stats["wins"] / total_games * 100) if total_games > 0 else 0
        
        embed = discord.Embed(
            title=f"📊 Казино Статистика - {ctx.author.name}",
            color=0x3498DB
        )
        embed.add_field(name="✅ Перемог", value=f"{stats['wins']}", inline=True)
        embed.add_field(name="❌ Поразок", value=f"{stats['losses']}", inline=True)
        embed.add_field(name="🎮 Всього ігор", value=f"{total_games}", inline=True)
        embed.add_field(name="📈 Процент перемог", value=f"{win_rate:.1f}%", inline=True)
        embed.add_field(name="💰 Всього поставлено", value=f"{stats['total_bet']:,} 💵", inline=True)
        
        await ctx.send(embed=embed)
