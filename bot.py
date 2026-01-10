import discord
from discord.ext import commands
import json
import os

# ================== CONFIG ==================

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = "!"
SIGNUP_CHANNEL_ID = 1456720618329210995
SIGNUP_MESSAGE_ID = 1456968992215404590
BACKUP_CHANNEL_ID = 1454892029267017821
DATA_FILE = "signups.json"
COOPS_FILE = "coops.json"
BACKUP_FILE = "backup.json"

ROLE_KLEINE_MAYORS = "kleine Mayors"
ROLE_MAYOR_WUERDIG = "Mayor würdig"
ROLE_CHEF = "Chef"
ROLE_HOST = "Host"
ROLE_AXE = "Achse"
ROLE_ALLIES = "Allies"

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

AXIS_TEAMS = ["Deutschland","Italien","Rumänien","Spanien","Ungarn","Bulgarien","Finnland","Jugoslawien","Japan","Mandschukuo","Siam"]
ALLIES_TEAMS = ["UdSSR","Mongolei","Großbritannien","USA","Frankreich","Kanada","Südafrika","Indien","Australien","Neuseeland","Mexiko"]

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
        "**Achsenmächte:**\n" +
        "\n".join(line(c) for c in ["Deutschland","Italien","Rumänien","Spanien","Ungarn","Bulgarien","Finnland","Jugoslawien"]) + "\n\n" +
        "**Japan-Team:**\n" +
        "\n".join(line(c) for c in ["Japan","Mandschukuo","Siam"]) + "\n\n" +
        "**Komintern:**\n" +
        "\n".join(line(c) for c in ["UdSSR","Mongolei"]) + "\n\n" +
        "**Alliierte:**\n" +
        "\n".join(line(c) for c in ["Großbritannien","USA","Frankreich","Kanada","Südafrika","Indien","Australien","Neuseeland","Mexiko"])
    )

    if backups:
        backup_mentions = ", ".join(f"<@{uid}>" for uid in backups.keys())
        content += f"\n\n**Backups:** {backup_mentions}"

    await message.edit(content=content)

# ================== ROLLEN ==================

async def assign_role(member, country):
    guild = member.guild
    if country in AXIS_TEAMS:
        role = discord.utils.get(guild.roles, name=ROLE_AXE)
    elif country in ALLIES_TEAMS:
        role = discord.utils.get(guild.roles, name=ROLE_ALLIES)
    else:
        return
    if role not in member.roles:
        await member.add_roles(role)

async def remove_role(member):
    guild = member.guild
    axe_role = discord.utils.get(guild.roles, name=ROLE_AXE)
    allies_role = discord.utils.get(guild.roles, name=ROLE_ALLIES)
    if axe_role in member.roles:
        await member.remove_roles(axe_role)
    if allies_role in member.roles:
        await member.remove_roles(allies_role)

# ================== SIGNUP ==================

# **DEIN ORIGINAL SIGNUP-CODE**, unverändert
# Du kannst hier dein CountrySelect, CountryView, !signup, !unsign und Coop einfügen
# Wichtig: Ich setze nur Rollen-Assignment nach Signup ein

# Beispiel nach erfolgreichem Signup in CountrySelect.callback():
# await assign_role(self.user, chosen)

# Beispiel nach !unsign:
# await remove_role(ctx.author)

# ================== BACKUP ==================

@bot.command()
async def backup(ctx):
    backups = load_data(BACKUP_FILE)
    uid = str(ctx.author.id)
    if uid in backups:
        await ctx.send("Du bist bereits als Backup angemeldet.", delete_after=5)
        return
    backups[uid] = True
    save_data(BACKUP_FILE, backups)
    await update_signup_message(ctx.guild)
    await ctx.send("Du wurdest als Backup eingetragen ✅", delete_after=5)

# ================== ADMIN / HOST ==================

def is_host_or_chef(ctx):
    return any(r.name in [ROLE_CHEF, ROLE_HOST] for r in ctx.author.roles)

@bot.command(name="clearall")
async def clear_all(ctx):
    if not is_host_or_chef(ctx):
        await ctx.send("Nur Chef oder Host darf das ausführen ❌")
        return
    save_data(DATA_FILE, {})
    save_data(COOPS_FILE, {})
    save_data(BACKUP_FILE, {})
    await update_signup_message(ctx.guild)
    await ctx.send("Alles gelöscht ✅")

# forceadd und forceremove analog

# ================== GAMEOVER ==================
# Implementierung wie zuvor, mit MVP Auswahl per Dropdown, Gewinner Auswahl, Kopie der Signup-Nachricht
# und Rollen entfernen

# ================== EVENTS ==================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

bot.run(TOKEN)


