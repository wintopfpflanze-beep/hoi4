import discord
from discord.ext import commands
import json
import os

# ================== CONFIG ==================

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = "!"
SIGNUP_CHANNEL_ID = 1456720618329210995
SIGNUP_MESSAGE_ID = 1456968992215404590
DATA_FILE = "signups.json"

ROLE_AXIS = "Achse"
ROLE_ALLIES = "Allies"
ROLE_KOMINTERN = "Komintern"
ROLE_JAPAN = "Japan und co"

# ================== FACTIONS ==================

FACTIONS = {
    "Achsenmächte": {
        "emoji": "⚫",
        "color": discord.Color.dark_grey(),
        "countries": ["Deutschland", "Italien", "Rumänien", "Spanien", "Ungarn", "Bulgarien", "Finnland", "Jugoslawien"],
        "role": ROLE_AXIS
    },
    "Japan-Team": {
        "emoji": "🟡",
        "color": discord.Color.gold(),
        "countries": ["Japan", "Mandschukuo", "Siam"],
        "role": ROLE_JAPAN
    },
    "Komintern": {
        "emoji": "🔴",
        "color": discord.Color.red(),
        "countries": ["UdSSR", "Mongolei"],
        "role": ROLE_KOMINTERN
    },
    "Alliierte": {
        "emoji": "🔵",
        "color": discord.Color.blue(),
        "countries": ["Großbritannien", "USA", "Frankreich", "Kanada", "Südafrika", "Indien", "Australien", "Neuseeland", "Mexiko"],
        "role": ROLE_ALLIES
    }
}

# ================== BOT ==================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# ================== DATA ==================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ================== MESSAGE UPDATE ==================

async def update_signup_message(guild):
    channel = guild.get_channel(SIGNUP_CHANNEL_ID)
    if not channel:
        return
    try:
        message = await channel.fetch_message(SIGNUP_MESSAGE_ID)
    except discord.NotFound:
        return

    data = load_data()

    def line(country):
        uid = next((u for u, c in data.items() if c == country), None)
        return f"{country}: <@{uid}>" if uid else f"{country}:"

    content = ""
    for faction_name, faction in FACTIONS.items():
        content += f"**{faction_name}:**\n"
        for c in faction["countries"]:
            content += line(c) + "\n"
        content += "\n"

    await message.edit(content=content)

# ================== SIGNUP UI ==================

class SignupCountrySelect(discord.ui.Select):
    def __init__(self, user, guild, faction):
        self.user = user
        self.guild = guild
        self.faction = faction
        options = [discord.SelectOption(label=c) for c in faction["countries"]]
        super().__init__(placeholder="Wähle dein Land", options=options)

    async def callback(self, interaction: discord.Interaction):
        # ❌ Prüfen, ob es der richtige User ist
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Nicht dein Menü.", ephemeral=True)
            return

        # ⏳ Interaction sofort bestätigen
        await interaction.response.defer()

        data = load_data()
        uid = str(self.user.id)
        country = self.values[0]

        # Prüfen, ob der User bereits angemeldet ist
        if uid in data:
            await interaction.followup.send("Du bist bereits angemeldet.", ephemeral=True)
            return

        # Prüfen, ob das Land schon vergeben ist
        if country in data.values():
            await interaction.followup.send("Land bereits vergeben.", ephemeral=True)
            return

        # 💾 Speichern
        data[uid] = country
        save_data(data)

        # 🎭 Rolle vergeben
        role = discord.utils.get(self.guild.roles, name=self.faction["role"])
        if role:
            await self.user.add_roles(role, reason="Signup Faction")

        # Signup-Nachricht aktualisieren
        await update_signup_message(self.guild)

        # ✅ DM aktualisieren
        await interaction.followup.edit_message(
            interaction.message.id,
            content=f"✅ Angemeldet als **{country}**\n🎭 Rolle **{self.faction['role']}** erhalten",
            embed=None,
            view=None
        )

class FactionSignupView(discord.ui.View):
    def __init__(self, user, guild):
        super().__init__(timeout=120)
        self.user = user
        self.guild = guild

        for faction_name, faction in FACTIONS.items():
            btn = discord.ui.Button(
                label=faction_name,
                emoji=faction["emoji"],
                style=discord.ButtonStyle.primary
            )
            btn.callback = self.make_callback(faction_name, faction)
            self.add_item(btn)

    def make_callback(self, faction_name, faction):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user.id:
                await interaction.response.send_message("❌ Nicht dein Menü.", ephemeral=True)
                return

            embed = discord.Embed(
                title=f"{faction['emoji']} {faction_name}",
                description="Wähle dein Land:",
                color=faction["color"]
            )

            view = discord.ui.View()
            view.add_item(SignupCountrySelect(self.user, self.guild, faction))

            await interaction.response.edit_message(embed=embed, view=view)
        return callback

@bot.command()
async def signup(ctx):
    embed = discord.Embed(
        title="🌍 Länder-Anmeldung",
        description="Wähle zuerst deine Faction:",
        color=discord.Color.blurple()
    )
    await ctx.author.send(embed=embed, view=FactionSignupView(ctx.author, ctx.guild))
    await ctx.message.delete()

# ================== UNSIGN ==================

@bot.command()
async def unsign(ctx):
    data = load_data()
    uid = str(ctx.author.id)

    if uid not in data:
        await ctx.author.send("Du bist nicht angemeldet.")
        return

    del data[uid]
    save_data(data)

    roles = [
        ROLE_AXIS,
        ROLE_ALLIES,
        ROLE_KOMINTERN,
        ROLE_JAPAN
    ]

    to_remove = [r for r in ctx.guild.roles if r.name in roles and r in ctx.author.roles]
    if to_remove:
        await ctx.author.remove_roles(*to_remove, reason="Unsign")

    await update_signup_message(ctx.guild)
    await ctx.author.send("❌ Anmeldung aufgehoben & Rollen entfernt.")

# ================== EVENTS ==================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

bot.run(TOKEN)



