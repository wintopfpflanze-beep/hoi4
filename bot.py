import discord
from discord.ext import commands
import json
import os

# ================== CONFIG ==================

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = "!"
SIGNUP_CHANNEL_ID = 1456720618329210995
SIGNUP_MESSAGE_ID = 1456964173253574850
DATA_FILE = "signups.json"

ROLE_KLEINE_MAYORS = "kleine Mayors"
ROLE_MAYOR_WUERDIG = "Mayor würdig"
ROLE_CHEF = "chef"

# 🔹 Faction Rollen
ROLE_AXIS = "Achse"
ROLE_ALLIES = "Allies"
ROLE_KOMINTERN = "Komintern"
ROLE_JAPAN = "Japan und co"

# ================== LÄNDER ==================

ALL_COUNTRIES = [
    "Deutschland", "Italien", "Rumänien", "Spanien", "Ungarn",
    "Bulgarien", "Finnland", "Jugoslawien",
    "Japan", "Mandschukuo", "Siam",
    "UdSSR", "Mongolei",
    "Großbritannien", "USA", "Frankreich", "Kanada", "Südafrika",
    "Indien", "Australien", "Neuseeland", "Mexiko"
]

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

    content = (
        "**Achsenmächte:**\n"
        "\n".join(line(c) for c in FACTIONS["Achsenmächte"]["countries"]) +
        "\n\n**Japan-Team:**\n" +
        "\n".join(line(c) for c in FACTIONS["Japan-Team"]["countries"]) +
        "\n\n**Komintern:**\n" +
        "\n".join(line(c) for c in FACTIONS["Komintern"]["countries"]) +
        "\n\n**Alliierte:**\n" +
        "\n".join(line(c) for c in FACTIONS["Alliierte"]["countries"])
    )

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
        data = load_data()
        uid = str(self.user.id)

        if uid in data:
            await interaction.response.send_message("Du bist bereits angemeldet.", ephemeral=True)
            return

        country = self.values[0]
        if country in data.values():
            await interaction.response.send_message("Land bereits vergeben.", ephemeral=True)
            return

        data[uid] = country
        save_data(data)

        role = discord.utils.get(self.guild.roles, name=self.faction["role"])
        if role:
            await self.user.add_roles(role, reason="Signup Faction Rolle")

        await update_signup_message(self.guild)

        await interaction.response.edit_message(
            content=f"✅ Angemeldet als **{country}**\n🎭 Rolle **{self.faction['role']}** erhalten",
            embed=None,
            view=None
        )

class FactionSignupView(discord.ui.View):
    def __init__(self, user, guild):
        super().__init__(timeout=120)
        self.user = user
        self.guild = guild

        for name, faction in FACTIONS.items():
            btn = discord.ui.Button(
                label=name,
                emoji=faction["emoji"],
                style=discord.ButtonStyle.primary
            )
            btn.callback = self.make_callback(faction)
            self.add_item(btn)

    def make_callback(self, faction):
        async def callback(interaction: discord.Interaction):
            embed = discord.Embed(
                title=f"{faction['emoji']} {interaction.component.label}",
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

    roles_to_remove = [
        r for r in ctx.guild.roles
        if r.name in [ROLE_AXIS, ROLE_ALLIES, ROLE_KOMINTERN, ROLE_JAPAN]
        and r in ctx.author.roles
    ]

    if roles_to_remove:
        await ctx.author.remove_roles(*roles_to_remove, reason="Unsign")

    await update_signup_message(ctx.guild)
    await ctx.author.send("❌ Anmeldung aufgehoben & Rollen entfernt.")

# ================== EVENTS ==================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

bot.run(TOKEN)



