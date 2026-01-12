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
ROLE_ACHSE = "Achse"
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

MAJOR_COUNTRIES = ["Deutschland", "USA", "UdSSR"]
MID_MAJORS = ["Italien", "Großbritannien", "Frankreich", "Japan"]

SMALL_COUNTRIES = [
    c for c in ALL_COUNTRIES
    if c not in MAJOR_COUNTRIES and c not in MID_MAJORS
]

# ================== FACTIONS (NEU – NUR UI) ==================

FACTIONS = {
    "Achsenmächte": {
        "emoji": "⬛",
        "color": discord.Color.dark_red(),
        "countries": ["Deutschland", "Italien", "Rumänien", "Spanien", "Ungarn", "Bulgarien", "Finnland", "Jugoslawien"],
        "team_role": ROLE_AXIS
    },
    "Japan-Team": {
        "emoji": "🟨",
        "color": discord.Color.gold(),
        "countries": ["Japan", "Mandschukuo", "Siam"],
        "team_role": ROLE_JAPAN
    },
    "Komintern": {
        "emoji": "🟥",
        "color": discord.Color.purple(),
        "countries": ["UdSSR", "Mongolei"],
        "team_role": ROLE_KOMINTERN 
    },
    "Alliierte": {
        "emoji": "🟦",
        "color": discord.Color.blue(),
        "countries": ["Großbritannien", "USA", "Frankreich", "Kanada", "Südafrika", "Indien", "Australien", "Neuseeland", "Mexiko"],
        "team_role": ROLE_ALLIES
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

async def update_signup_message(guild, coop_additions=None):
    channel = guild.get_channel(SIGNUP_CHANNEL_ID)
    if not channel:
        return

    try:
        message = await channel.fetch_message(SIGNUP_MESSAGE_ID)
    except discord.NotFound:
        return

    data = load_data()
    coop_additions = coop_additions or {}

    def line(country):
        main_id = next((uid for uid, c in data.items() if c == country), None)
        coop_ids = coop_additions.get(country, [])

        if main_id:
            mentions = [f"<@{main_id}>"] + [f"<@{cid}>" for cid in coop_ids]
            return f"{country}: " + ", ".join(mentions)
        return f"{country}:"

    content = (
        "**Achsenmächte:**\n"
        f"{line('Deutschland')}\n"
        f"{line('Italien')}\n"
        f"{line('Rumänien')}\n"
        f"{line('Spanien')}\n"
        f"{line('Ungarn')}\n"
        f"{line('Bulgarien')}\n"
        f"{line('Finnland')}\n"
        f"{line('Jugoslawien')}\n\n"

        "**Japan-Team:**\n"
        f"{line('Japan')}\n"
        f"{line('Mandschukuo')}\n"
        f"{line('Siam')}\n\n"

        "**Komintern:**\n"
        f"{line('UdSSR')}\n"
        f"{line('Mongolei')}\n\n"

        "**Alliierte:**\n"
        f"{line('Großbritannien')}\n"
        f"{line('USA')}\n"
        f"{line('Frankreich')}\n"
        f"{line('Kanada')}\n"
        f"{line('Südafrika')}\n"
        f"{line('Indien')}\n"
        f"{line('Australien')}\n"
        f"{line('Neuseeland')}\n"
        f"{line('Mexiko')}"
    )

    await message.edit(content=content)

# ================== SIGNUP UI (NEU) ==================

class SignupCountrySelect(discord.ui.Select):
    def __init__(self, user, guild, countries):
        self.user = user
        self.guild = guild
        options = [discord.SelectOption(label=c) for c in countries]
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

        await update_signup_message(self.guild)
        await interaction.response.edit_message(
            content=f"✅ Angemeldet als **{country}**",
            embed=None,
            view=None
        )

class FactionSignupView(discord.ui.View):
    def __init__(self, user, guild):
        super().__init__(timeout=120)
        self.user = user
        self.guild = guild

        for name, data in FACTIONS.items():
            button = discord.ui.Button(
                label=name,
                emoji=data["emoji"],
                style=discord.ButtonStyle.primary
            )
            button.callback = self.make_callback(name)
            self.add_item(button)

    def make_callback(self, faction_name):
        async def callback(interaction: discord.Interaction):
            faction = FACTIONS[faction_name]

            embed = discord.Embed(
                title=f"{faction['emoji']} {faction_name}",
                description="Wähle dein Land:",
                color=faction["color"]
            )

            view = discord.ui.View()
            view.add_item(
                SignupCountrySelect(
                    self.user,
                    self.guild,
                    faction["countries"]
                )
            )

            await interaction.response.edit_message(embed=embed, view=view)
        return callback

@bot.command()
async def signup(ctx):
    embed = discord.Embed(
        title="🌍 Länder-Anmeldung",
        description="Wähle zuerst deine Faction:",
        color=discord.Color.blurple()
    )

    await ctx.author.send(
        embed=embed,
        view=FactionSignupView(ctx.author, ctx.guild)
    )
    await ctx.message.delete()

# ================== EVENTS ==================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

bot.run(TOKEN)


