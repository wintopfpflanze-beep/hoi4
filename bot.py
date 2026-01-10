import discord
from discord.ext import commands
import json
import os

# ================== CONFIG ==================

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = "!"
SIGNUP_CHANNEL_ID = 1456720618329210995
SIGNUP_MESSAGE_ID = 1456968992215404590
GAMEOVER_CHANNEL_ID = 1454892029267017821  # Channel für Gameover-Nachricht
DATA_FILE = "signups.json"
COOPS_FILE = "coops.json"
BACKUP_FILE = "backups.json"

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

    def backup_line():
        if not backups:
            return ""
        mentions = [f"<@{uid}>" for uid in backups]
        return f"Backup: {', '.join(mentions)}"

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
        f"{line('Mexiko')}\n\n"

        f"{backup_line()}"
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

async def assign_roles(member, country):
    guild = member.guild
    axe_countries = [
        "Deutschland", "Italien", "Rumänien", "Spanien", "Ungarn",
        "Bulgarien", "Finnland", "Jugoslawien", "Japan", "Mandschukuo", "Siam"
    ]
    allies_countries = [
        "Großbritannien", "USA", "Frankreich", "Kanada", "Südafrika",
        "Indien", "Australien", "Neuseeland", "Mexiko", "UdSSR", "Mongolei"
    ]
    if country in axe_countries:
        role = discord.utils.get(guild.roles, name=ROLE_AXE)
        await member.add_roles(role)
    elif country in allies_countries:
        role = discord.utils.get(guild.roles, name=ROLE_ALLIES)
        await member.add_roles(role)

async def remove_roles(member):
    guild = member.guild
    for role_name in [ROLE_AXE, ROLE_ALLIES]:
        role = discord.utils.get(guild.roles, name=role_name)
        if role in member.roles:
            await member.remove_roles(role)

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

        await assign_roles(self.user, chosen)
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

# ================== UNSIGN ==================

@bot.command()
async def unsign(ctx):
    uid = str(ctx.author.id)
    signups = load_data(DATA_FILE)
    coops = load_data(COOPS_FILE)
    backups = load_data(BACKUP_FILE)

    removed = False
    country_removed = None

    if uid in signups:
        country_removed = signups[uid]
        del signups[uid]
        save_data(DATA_FILE, signups)
        removed = True
        await remove_roles(ctx.author)

    for country, lst in list(coops.items()):
        if int(uid) in lst:
            lst.remove(int(uid))
            if not lst:
                del coops[country]
            removed = True

    if uid in backups:
        backups.remove(uid)
        save_data(BACKUP_FILE, backups)
        removed = True

    save_data(COOPS_FILE, coops)

    if not removed:
        await ctx.author.send("Du bist weder Main-Spieler noch Coop/Backup.")
        return

    await update_signup_message(ctx.guild)
    await ctx.author.send("Du wurdest erfolgreich entfernt.")

# ================== BACKUP ==================

@bot.command()
async def backup(ctx):
    uid = str(ctx.author.id)
    backups = load_data(BACKUP_FILE)
    if uid in backups:
        await ctx.send("Du bist bereits als Backup eingetragen.", ephemeral=True)
        return
    backups[uid] = uid
    save_data(BACKUP_FILE, backups)
    await update_signup_message(ctx.guild)
    await ctx.send("Du wurdest als Backup eingetragen ✅")

# ================== GAMEOVER ==================

class MVPSelect(discord.ui.Select):
    def __init__(self, placeholder, options):
        opts = [discord.SelectOption(label=o) for o in options]
        super().__init__(placeholder=placeholder, options=opts)

class GameOverView(discord.ui.View):
    def __init__(self, options, placeholder):
        super().__init__(timeout=300)
        self.value = None
        self.add_item(MVPSelect(placeholder, options))

@bot.command()
async def gameover(ctx):
    if ROLE_CHEF not in [r.name for r in ctx.author.roles]:
        await ctx.send("Nur Chef kann das Spiel beenden.")
        return

    guild = ctx.guild
    signups = load_data(DATA_FILE)
    coops = load_data(COOPS_FILE)

    # Spielerlisten
    members = {m.id: m.display_name for m in guild.members}
    axe_players = [m.display_name for m in guild.members if ROLE_AXE in [r.name for r in m.roles]]
    allies_players = [m.display_name for m in guild.members if ROLE_ALLIES in [r.name for r in m.roles]]

    # 5 Fragen per DM
    dm = await ctx.author.create_dm()
    await dm.send("Game Over Prozess gestartet. Bitte beantworte die Fragen.")

    await dm.send("1️⃣ Welches Datum ist heute?")
    def check_msg(m): return m.author == ctx.author and isinstance(m.channel, discord.DMChannel)
    date_msg = await bot.wait_for("message", check=check_msg)
    date_str = date_msg.content

    await dm.send("2️⃣ Wann ist das Game ingame geendet?")
    ingame_msg = await bot.wait_for("message", check=check_msg)
    ingame_str = ingame_msg.content

    # Achse MVP
    view_axe = GameOverView(axe_players, "Wähle Achse MVP")
    msg_axe = await dm.send("3️⃣ Wer ist Achse MVP?", view=view_axe)
    await view_axe.wait()
    mvp_axe = view_axe.children[0].values[0] if view_axe.children[0].values else "Keiner"

    # Allies MVP
    view_allies = GameOverView(allies_players, "Wähle Allies MVP")
    msg_allies = await dm.send("4️⃣ Wer ist Allies MVP?", view=view_allies)
    await view_allies.wait()
    mvp_allies = view_allies.children[0].values[0] if view_allies.children[0].values else "Keiner"

    # Gewinner
    view_winner = GameOverView(["Achse", "Allies"], "Wähle Gewinner")
    msg_win = await dm.send("5️⃣ Wer hat gewonnen?", view=view_winner)
    await view_winner.wait()
    winner = view_winner.children[0].values[0] if view_winner.children[0].values else "Unbekannt"

    # Gameover Nachricht
    content = (
        f"**Game:** Am {date_str} um {ingame_str}\n"
        f"**Gewinner:** {winner}\n"
        f"**MVP Achse:** {mvp_axe}\n"
        f"**MVP Allies:** {mvp_allies}"
    )

    go_channel = guild.get_channel(GAMEOVER_CHANNEL_ID)
    await go_channel.send(content)

    # Rollen entfernen
    for member in guild.members:
        await remove_roles(member)

# ================== ADMIN COMMANDS ==================

def is_admin(ctx):
    return ctx.author.guild_permissions.administrator or ROLE_HOST in [r.name for r in ctx.author.roles] or ROLE_CHEF in [r.name for r in ctx.author.roles]

@bot.command(name="clearall")
async def clear_all(ctx):
    if not is_admin(ctx):
        await ctx.send("Nur Admins können diesen Befehl ausführen.")
        return
    save_data(DATA_FILE, {})
    save_data(COOPS_FILE, {})
    save_data(BACKUP_FILE, {})
    await update_signup_message(ctx.guild)
    await ctx.send("Alle Signups, Coops und Backups wurden gelöscht ✅")

@bot.command(name="forceadd")
async def force_add(ctx, member: discord.Member, *, country):
    if not is_admin(ctx):
        await ctx.send("Nur Admins/Host/Chef können diesen Befehl ausführen.")
        return
    if country not in ALL_COUNTRIES:
        await ctx.send(f"Ungültiges Land: {country}")
        return
    signups = load_data(DATA_FILE)
    signups[str(member.id)] = country
    save_data(DATA_FILE, signups)
    await assign_roles(member, country)
    await update_signup_message(ctx.guild)
    await ctx.send(f"{member} wurde als Main-Spieler von {country} hinzugefügt ✅")

@bot.command(name="forceremove")
async def force_remove(ctx, member: discord.Member):
    if not is_admin(ctx):
        await ctx.send("Nur Admins/Host/Chef können diesen Befehl ausführen.")
        return
    uid = str(member.id)
    signups = load_data(DATA_FILE)
    coops = load_data(COOPS_FILE)
    backups = load_data(BACKUP_FILE)
    removed = False
    if uid in signups:
        del signups[uid]
        removed = True
        await remove_roles(member)
    for country, lst in list(coops.items()):
        if int(uid) in lst:
            lst.remove(int(uid))
            if not lst:
                del coops[country]
            removed = True
    if uid in backups:
        backups.pop(uid, None)
        removed = True
    save_data(DATA_FILE, signups)
    save_data(COOPS_FILE, coops)
    save_data(BACKUP_FILE, backups)
    await update_signup_message(ctx.guild)
    if removed:
        await ctx.send(f"{member} wurde entfernt ✅")
    else:
        await ctx.send(f"{member} war nicht angemeldet ❌")

# ================== EVENTS ==================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

bot.run(TOKEN)



