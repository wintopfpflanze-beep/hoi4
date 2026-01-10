import discord
from discord.ext import commands
import json
import os

# ================== CONFIG ==================

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = "!"
SIGNUP_CHANNEL_ID = 1456720618329210995
SIGNUP_MESSAGE_ID = 1456968992215404590
GAMEOVER_CHANNEL_ID = 1454892029267017821

DATA_FILE = "signups.json"
COOPS_FILE = "coops.json"
BACKUP_FILE = "backups.json"

ROLE_KLEINE_MAYORS = "kleine Mayors"
ROLE_MAYOR_WUERDIG = "Mayor würdig"
ROLE_CHEF = "Chef"
ROLE_ACHSE = "Achse"
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

AXIS = ["Deutschland", "Italien", "Rumänien", "Spanien", "Ungarn",
        "Bulgarien", "Finnland", "Jugoslawien",
        "Japan", "Mandschukuo", "Siam"]

ALLIES = ["Großbritannien", "USA", "Frankreich", "Kanada", "Südafrika",
          "Indien", "Australien", "Neuseeland", "Mexiko", "UdSSR", "Mongolei"]

MAJOR_COUNTRIES = ["Deutschland", "USA", "UdSSR"]
MID_MAJORS = ["Italien", "Großbritannien", "Frankreich", "Japan"]
SMALL_COUNTRIES = [c for c in ALL_COUNTRIES if c not in MAJOR_COUNTRIES + MID_MAJORS]

# ================== BOT ==================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

signup_enabled = True

# ================== DATA ==================

def load_data(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)

def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# ================== SIGNUP MESSAGE ==================

async def update_signup_message(guild):
    channel = guild.get_channel(SIGNUP_CHANNEL_ID)
    message = await channel.fetch_message(SIGNUP_MESSAGE_ID)

    signups = load_data(DATA_FILE)
    coops = load_data(COOPS_FILE)
    backups = load_data(BACKUP_FILE)

    def line(country):
        main = next((uid for uid, c in signups.items() if c == country), None)
        mentions = []
        if main:
            mentions.append(f"<@{main}>")
        mentions += [f"<@{cid}>" for cid in coops.get(country, [])]
        return f"{country}: {', '.join(mentions)}" if mentions else f"{country}:"

    content = (
        "**Achsenmächte:**\n" +
        "\n".join(line(c) for c in AXIS if c not in ["Japan", "Mandschukuo", "Siam"]) +
        "\n\n**Japan-Team:**\n" +
        "\n".join(line(c) for c in ["Japan", "Mandschukuo", "Siam"]) +
        "\n\n**Alliierte & Komintern:**\n" +
        "\n".join(line(c) for c in ALLIES)
    )

    if backups:
        content += "\n\n**Backup:**\n" + "\n".join(f"<@{uid}>" for uid in backups)

    await message.edit(content=content)

# ================== ROLE HELPERS ==================

async def update_player_role(member, country=None, remove=False):
    if not member:
        return
    if country in AXIS:
        role = discord.utils.get(member.guild.roles, name=ROLE_ACHSE)
    else:
        role = discord.utils.get(member.guild.roles, name=ROLE_ALLIES)

    if remove:
        await member.remove_roles(role)
    else:
        await member.add_roles(role)

# ================== BACKUP ==================

@bot.command()
async def backup(ctx):
    if not signup_enabled:
        return
    backups = load_data(BACKUP_FILE)
    backups[str(ctx.author.id)] = True
    save_data(BACKUP_FILE, backups)
    await update_signup_message(ctx.guild)
    await ctx.message.delete()

# ================== SIGNUP ON/OFF ==================

@bot.command()
@commands.has_role(ROLE_CHEF)
async def signupoff(ctx):
    global signup_enabled
    signup_enabled = False
    await ctx.send("Anmeldung deaktiviert ❌")

@bot.command()
@commands.has_role(ROLE_CHEF)
async def signupon(ctx):
    global signup_enabled
    signup_enabled = True
    await ctx.send("Anmeldung aktiviert ✅")

# ================== UNSIGN ==================

@bot.command()
async def unsign(ctx):
    uid = str(ctx.author.id)
    signups = load_data(DATA_FILE)
    coops = load_data(COOPS_FILE)
    backups = load_data(BACKUP_FILE)

    if uid in signups:
        country = signups[uid]
        del signups[uid]
        await update_player_role(ctx.author, country, remove=True)

    backups.pop(uid, None)

    for c, lst in list(coops.items()):
        if ctx.author.id in lst:
            lst.remove(ctx.author.id)
            await update_player_role(ctx.author, c, remove=True)

    save_data(DATA_FILE, signups)
    save_data(COOPS_FILE, coops)
    save_data(BACKUP_FILE, backups)

    await update_signup_message(ctx.guild)
    await ctx.author.send("Du wurdest entfernt.")

# ================== GAMEOVER ==================

@bot.command()
@commands.has_role(ROLE_CHEF)
async def gameover(ctx):
    guild = ctx.guild
    chef = ctx.author

    def members_with(role_name):
        role = discord.utils.get(guild.roles, name=role_name)
        return [m for m in guild.members if role in m.roles]

    dm = await chef.create_dm()
    await dm.send("Welches Datum ist heute?")
    date = (await bot.wait_for("message", check=lambda m: m.author == chef)).content

    await dm.send("Wann ist das Game ingame geendet?")
    ingame = (await bot.wait_for("message", check=lambda m: m.author == chef)).content

    async def select_user(title, users):
        options = [discord.SelectOption(label=u.display_name, value=str(u.id)) for u in users]
        select = discord.ui.Select(placeholder=title, options=options)
        view = discord.ui.View()
        view.add_item(select)
        await dm.send(title, view=view)
        await view.wait()
        return guild.get_member(int(select.values[0]))

    achse_mvp = await select_user("Achse MVP", members_with(ROLE_ACHSE))
    allies_mvp = await select_user("Allies MVP", members_with(ROLE_ALLIES))

    win_select = discord.ui.Select(
        placeholder="Wer hat gewonnen?",
        options=[discord.SelectOption(label="Achse"), discord.SelectOption(label="Allies")]
    )
    view = discord.ui.View()
    view.add_item(win_select)
    await dm.send("Wer hat gewonnen?", view=view)
    await view.wait()
    winner = win_select.values[0]

    src = await guild.get_channel(SIGNUP_CHANNEL_ID).fetch_message(SIGNUP_MESSAGE_ID)
    target = guild.get_channel(GAMEOVER_CHANNEL_ID)

    text = (
        f"**Game: Am {date}**\n"
        f"**Gewinner:** {winner} am {ingame}\n\n"
        f"**MVP Achse:** {achse_mvp.mention}\n"
        f"**MVP Allies:** {allies_mvp.mention}\n\n"
        "-----------------------------\n"
        f"{src.content}"
    )

    await target.send(text)

    for m in members_with(ROLE_ACHSE):
        await m.remove_roles(discord.utils.get(guild.roles, name=ROLE_ACHSE))
    for m in members_with(ROLE_ALLIES):
        await m.remove_roles(discord.utils.get(guild.roles, name=ROLE_ALLIES))

# ================== READY ==================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

bot.run(TOKEN)

bot.run(TOKEN)

