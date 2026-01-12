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
COOPS_FILE = "coops.json"
BACKUP_FILE = "backups.json"

ROLE_KLEINE_MAYORS = "kleine Mayors"
ROLE_MAYOR_WUERDIG = "Mayor würdig"
ROLE_CHEF = "Chef"
ROLE_ACHSE = "Achse"
ROLE_ALLIES = "Allies"

signup_enabled = True

# ================== LÄNDER ==================

ALL_COUNTRIES = [
    "Deutschland", "Italien", "Rumänien", "Spanien", "Ungarn",
    "Bulgarien", "Finnland", "Jugoslawien",
    "Japan", "Mandschukuo", "Siam",
    "UdSSR", "Mongolei",
    "Großbritannien", "USA", "Frankreich", "Kanada", "Südafrika",
    "Indien", "Australien", "Neuseeland", "Mexiko"
]

AXIS_COUNTRIES = [
    "Deutschland", "Italien", "Rumänien", "Spanien", "Ungarn",
    "Bulgarien", "Finnland", "Jugoslawien",
    "Japan", "Mandschukuo", "Siam"
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
    backups = load_data(BACKUP_FILE)

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

    if backups:
        content += "\n\n**Backup:**\n"
        for uid in backups.keys():
            content += f"<@{uid}>\n"

    await message.edit(content=content)

# ================== ROLLENLOGIK ==================

def get_available_countries(member):
    roles = [r.name for r in member.roles]
    if ROLE_MAYOR_WUERDIG in roles:
        return ALL_COUNTRIES
    if ROLE_KLEINE_MAYORS in roles:
        return SMALL_COUNTRIES + MID_MAJORS
    return SMALL_COUNTRIES

async def update_faction_roles(guild):
    signups = load_data(DATA_FILE)
    coops = load_data(COOPS_FILE)

    role_achse = discord.utils.get(guild.roles, name=ROLE_ACHSE)
    role_allies = discord.utils.get(guild.roles, name=ROLE_ALLIES)

    axis_ids = set()
    allies_ids = set()

    for uid, country in signups.items():
        if country in AXIS_COUNTRIES:
            axis_ids.add(int(uid))
        else:
            allies_ids.add(int(uid))

    for country, lst in coops.items():
        for uid in lst:
            if country in AXIS_COUNTRIES:
                axis_ids.add(uid)
            else:
                allies_ids.add(uid)

    for member in guild.members:
        if member.id in axis_ids:
            await member.add_roles(role_achse)
            await member.remove_roles(role_allies)
        elif member.id in allies_ids:
            await member.add_roles(role_allies)
            await member.remove_roles(role_achse)
        else:
            await member.remove_roles(role_achse, role_allies)

# ================== SIGNUP ==================

class CountrySelect(discord.ui.Select):
    def __init__(self, user, guild):
        self.user = user
        self.guild = guild
        options = [discord.SelectOption(label=c) for c in get_available_countries(user)]
        super().__init__(placeholder="Select your country", options=options)

    async def callback(self, interaction):
        global signup_enabled
        if not signup_enabled:
            await interaction.response.send_message("Anmeldung deaktiviert ❌", ephemeral=True)
            return

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

        await update_signup_message(self.guild)
        await update_faction_roles(self.guild)
        await interaction.response.edit_message(content=f"Angemeldet als **{chosen}**.", view=None)

class CountryView(discord.ui.View):
    def __init__(self, user, guild):
        super().__init__(timeout=120)
        self.add_item(CountrySelect(user, guild))

@bot.command()
async def signup(ctx):
    global signup_enabled
    if not signup_enabled:
        await ctx.author.send("Anmeldung deaktiviert ❌")
        return
    await ctx.author.send("Bitte wähle dein Land:", view=CountryView(ctx.author, ctx.guild))
    await ctx.message.delete()

# ================== BACKUP ==================

@bot.command()
async def backup(ctx):
    global signup_enabled
    if not signup_enabled:
        await ctx.author.send("Anmeldung deaktiviert ❌")
        return

    backups = load_data(BACKUP_FILE)
    uid = str(ctx.author.id)

    if uid in backups:
        await ctx.author.send("Du bist bereits Backup.")
        return

    backups[uid] = True
    save_data(BACKUP_FILE, backups)
    await update_signup_message(ctx.guild)
    await ctx.author.send("Als Backup eingetragen ✅")

# ================== UNSIGN ==================

@bot.command()
async def unsign(ctx):
    uid = str(ctx.author.id)
    signups = load_data(DATA_FILE)
    coops = load_data(COOPS_FILE)
    backups = load_data(BACKUP_FILE)

    removed = False

    if uid in signups:
        del signups[uid]
        removed = True

    for country, lst in list(coops.items()):
        if int(uid) in lst:
            lst.remove(int(uid))
            if not lst:
                del coops[country]
            removed = True

    if uid in backups:
        del backups[uid]
        removed = True

    save_data(DATA_FILE, signups)
    save_data(COOPS_FILE, coops)
    save_data(BACKUP_FILE, backups)

    await update_signup_message(ctx.guild)
    await update_faction_roles(ctx.guild)

    if removed:
        await ctx.author.send("Du wurdest entfernt ✅")
    else:
        await ctx.author.send("Du warst nicht angemeldet ❌")

# ================== SIGNUP ON / OFF ==================

@bot.command()
async def signupoff(ctx):
    global signup_enabled
    if ROLE_CHEF not in [r.name for r in ctx.author.roles]:
        return
    signup_enabled = False
    await ctx.send("Anmeldungen deaktiviert 🔒")

@bot.command()
async def signupon(ctx):
    global signup_enabled
    if ROLE_CHEF not in [r.name for r in ctx.author.roles]:
        return
    signup_enabled = True
    await ctx.send("Anmeldungen aktiviert ✅")

# ================== GAMEOVER ==================

@bot.command()
async def gameover(ctx):
    if ROLE_CHEF not in [r.name for r in ctx.author.roles]:
        return

    role_achse = discord.utils.get(ctx.guild.roles, name=ROLE_ACHSE)
    role_allies = discord.utils.get(ctx.guild.roles, name=ROLE_ALLIES)

    for m in ctx.guild.members:
        await m.remove_roles(role_achse, role_allies)

    await ctx.send("Game beendet – Rollen entfernt 🧹")

# ================== EVENTS ==================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

bot.run(TOKEN)


