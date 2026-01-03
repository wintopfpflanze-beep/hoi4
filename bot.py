import discord
from discord.ext import commands
import json
import os

# ================== CONFIG ==================

TOKEN = "DISCORD_BOT_TOKEN"
PREFIX = "!"
SIGNUP_CHANNEL_ID = 1456720618329210995
SIGNUP_MESSAGE_ID = 1456968992215404590
DATA_FILE = "signups.json"
COOPS_FILE = "coops.json"

ROLE_KLEINE_MAYORS = "kleine Mayors"
ROLE_MAYOR_WUERDIG = "Mayor würdig"
ROLE_CHEF = "Chef"

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
SMALL_COUNTRIES = [c for c in ALL_COUNTRIES if c not in MAJOR_COUNTRIES + MID_MAJORS]

# ================== BOT ==================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# ================== DATA ==================

def load_data(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)

def save_data(file, data):
    with open(file, "w") as f:
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

    signups = load_data(DATA_FILE)
    coops = load_data(COOPS_FILE)

    def line(country):
        main_id = next((uid for uid, c in signups.items() if c == country), None)
        coop_ids = coops.get(country, [])
        mentions = []
        if main_id:
            mentions.append(f"<@{main_id}>")
        mentions += [f"<@{cid}>" for cid in coop_ids]
        return f"{country}: {', '.join(mentions)}" if mentions else f"{country}:"

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

# ================== ROLLENLOGIK ==================

def get_available_countries(member):
    roles = [r.name for r in member.roles]
    if ROLE_MAYOR_WUERDIG in roles:
        return ALL_COUNTRIES
    if ROLE_KLEINE_MAYORS in roles:
        return SMALL_COUNTRIES + MID_MAJORS
    return SMALL_COUNTRIES

# ================== SIGNUP ==================

class CountrySelect(discord.ui.Select):
    def __init__(self, user, guild_id):
        self.user = user
        self.guild_id = guild_id
        options = [discord.SelectOption(label=c) for c in get_available_countries(user)]
        super().__init__(placeholder="Select your country", options=options)

    async def callback(self, interaction):
        signups = load_data(DATA_FILE)
        uid = str(self.user.id)

        if uid in signups:
            await interaction.response.send_message("Du bist bereits angemeldet.", ephemeral=True)
            return

        chosen = self.values[0]
        if chosen in signups.values():
            await interaction.response.send_message("Land bereits vergeben.", ephemeral=True)
            return

        signups[uid] = chosen
        save_data(DATA_FILE, signups)

        await update_signup_message(bot.get_guild(self.guild_id))
        await interaction.response.edit_message(content=f"Angemeldet als **{chosen}**.", view=None)

class CountryView(discord.ui.View):
    def __init__(self, user, guild_id):
        super().__init__(timeout=120)
        self.add_item(CountrySelect(user, guild_id))

@bot.command()
async def signup(ctx):
    await ctx.author.send("Bitte wähle dein Land:", view=CountryView(ctx.author, ctx.guild.id))
    await ctx.message.delete()

# ================== UNSIGN (MAIN + COOP) ==================

@bot.command()
async def unsign(ctx):
    uid = str(ctx.author.id)
    signups = load_data(DATA_FILE)
    coops = load_data(COOPS_FILE)

    removed = False

    if uid in signups:
        del signups[uid]
        save_data(DATA_FILE, signups)
        removed = True

    for country, lst in list(coops.items()):
        if int(uid) in lst:
            lst.remove(int(uid))
            if not lst:
                del coops[country]
            removed = True

    save_data(COOPS_FILE, coops)

    if not removed:
        await ctx.author.send("Du bist weder Main-Spieler noch Coop.")
        return

    await update_signup_message(ctx.guild)
    await ctx.author.send("Du wurdest erfolgreich entfernt.")

# ================== COOP ==================

COOP_OPTIONS = {
    "Deutschland coop 1": "Deutschland",
    "Deutschland coop 2": "Deutschland",
    "UdSSR coop 1": "UdSSR",
    "UdSSR coop 2": "UdSSR",
    "USA coop 1": "USA",
    "UK coop 1": "Großbritannien",
    "Japan coop 1": "Japan",
    "Italien coop 1": "Italien"
}

class CoopApprovalView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.approved = False

    @discord.ui.button(label="Ja", style=discord.ButtonStyle.success)
    async def yes(self, interaction, button):
        self.approved = True
        self.stop()
        await interaction.response.send_message("Zugestimmt ✅", ephemeral=True)

    @discord.ui.button(label="Nein", style=discord.ButtonStyle.danger)
    async def no(self, interaction, button):
        self.stop()
        await interaction.response.send_message("Abgelehnt ❌", ephemeral=True)

class CoopSelect(discord.ui.Select):
    def __init__(self, user, guild):
        self.user = user
        self.guild = guild
        options = [discord.SelectOption(label=o) for o in COOP_OPTIONS]
        super().__init__(placeholder="Wähle deinen Coop-Slot", options=options)

    async def callback(self, interaction):
        country = COOP_OPTIONS[self.values[0]]
        signups = load_data(DATA_FILE)
        coops = load_data(COOPS_FILE)

        main_id = next((uid for uid, c in signups.items() if c == country), None)
        if not main_id:
            await interaction.response.send_message("Kein Main-Spieler vorhanden.", ephemeral=True)
            return

        chef = next((m for m in self.guild.members if ROLE_CHEF in [r.name for r in m.roles]), None)
        if not chef:
            await interaction.response.send_message("Kein Chef gefunden.", ephemeral=True)
            return

        view1 = CoopApprovalView()
        view2 = CoopApprovalView()

        await self.guild.get_member(int(main_id)).send(f"{interaction.user} möchte Coop bei **{country}** spielen.", view=view1)
        await chef.send(f"{interaction.user} möchte Coop bei **{country}** spielen.", view=view2)

        await view1.wait()
        await view2.wait()

        if view1.approved and view2.approved:
            coops.setdefault(country, []).append(interaction.user.id)
            save_data(COOPS_FILE, coops)
            await update_signup_message(self.guild)
            await interaction.response.send_message("Coop genehmigt ✅", ephemeral=True)
        else:
            await interaction.response.send_message("Coop abgelehnt ❌", ephemeral=True)

class CoopView(discord.ui.View):
    def __init__(self, user, guild):
        super().__init__(timeout=120)
        self.add_item(CoopSelect(user, guild))

@bot.command()
async def coop(ctx):
    await ctx.author.send("Wähle deinen Coop-Slot:", view=CoopView(ctx.author, ctx.guild))
    await ctx.message.delete()

# ================== EVENTS ==================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

bot.run("DISCORD_BOT_TOKEN")
