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
ROLE_HOST = "Host"
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

MAJOR_COUNTRIES = ["Deutschland", "USA", "UdSSR"]
MID_MAJORS = ["Italien", "Großbritannien", "Frankreich", "Japan"]
SMALL_COUNTRIES = [c for c in ALL_COUNTRIES if c not in MAJOR_COUNTRIES + MID_MAJORS]

AXIS_COUNTRIES = ["Deutschland", "Italien", "Rumänien", "Spanien", "Ungarn",
                  "Bulgarien", "Finnland", "Jugoslawien", "Japan", "Mandschukuo", "Siam"]
ALLIES_COUNTRIES = ["Großbritannien", "USA", "Frankreich", "Kanada", "Südafrika",
                    "Indien", "Australien", "Neuseeland", "Mexiko", "UdSSR", "Mongolei"]

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

    content_lines = []

    content_lines.append("**Achsenmächte:**")
    for c in ["Deutschland", "Italien", "Rumänien", "Spanien", "Ungarn",
              "Bulgarien", "Finnland", "Jugoslawien"]:
        content_lines.append(line(c))

    content_lines.append("\n**Japan-Team:**")
    for c in ["Japan", "Mandschukuo", "Siam"]:
        content_lines.append(line(c))

    content_lines.append("\n**Komintern:**")
    for c in ["UdSSR", "Mongolei"]:
        content_lines.append(line(c))

    content_lines.append("\n**Alliierte:**")
    for c in ["Großbritannien", "USA", "Frankreich", "Kanada", "Südafrika",
              "Indien", "Australien", "Neuseeland", "Mexiko"]:
        content_lines.append(line(c))

    # Backups
    backup_mentions = [f"<@{uid}>" for uid in backups.values()]
    if backup_mentions:
        content_lines.append("\n**Backup:** " + ", ".join(backup_mentions))

    content = "\n".join(content_lines)
    await message.edit(content=content)

# ================== ROLLEN ==================

async def assign_roles(member, country):
    guild = member.guild
    if country in AXIS_COUNTRIES:
        role = discord.utils.get(guild.roles, name=ROLE_ACHSE)
        if role:
            await member.add_roles(role)
    elif country in ALLIES_COUNTRIES:
        role = discord.utils.get(guild.roles, name=ROLE_ALLIES)
        if role:
            await member.add_roles(role)

async def remove_roles(member):
    guild = member.guild
    role1 = discord.utils.get(guild.roles, name=ROLE_ACHSE)
    role2 = discord.utils.get(guild.roles, name=ROLE_ALLIES)
    roles_to_remove = [r for r in [role1, role2] if r in member.roles]
    if roles_to_remove:
        await member.remove_roles(*roles_to_remove)

# ================== BACKUP ==================

@bot.command()
async def backup(ctx):
    uid = str(ctx.author.id)
    backups = load_data(BACKUP_FILE)
    if uid in backups:
        await ctx.send("Du bist bereits als Backup eingetragen.", delete_after=5)
        return
    backups[uid] = uid
    save_data(BACKUP_FILE, backups)
    await update_signup_message(ctx.guild)
    await ctx.send(f"{ctx.author.mention} wurde als Backup eingetragen ✅", delete_after=5)

# ================== UNSIGN (MAIN + COOP + BACKUP) ==================

@bot.command()
async def unsign(ctx):
    uid = str(ctx.author.id)
    signups = load_data(DATA_FILE)
    coops = load_data(COOPS_FILE)
    backups = load_data(BACKUP_FILE)
    removed = False

    if uid in signups:
        country = signups[uid]
        del signups[uid]
        removed = True
        await remove_roles(ctx.author)

    if uid in backups:
        del backups[uid]
        removed = True

    for country, lst in list(coops.items()):
        if int(uid) in lst:
            lst.remove(int(uid))
            if not lst:
                del coops[country]
            removed = True

    save_data(DATA_FILE, signups)
    save_data(COOPS_FILE, coops)
    save_data(BACKUP_FILE, backups)

    if not removed:
        await ctx.author.send("Du bist weder Main-Spieler noch Coop oder Backup.")
        return

    await update_signup_message(ctx.guild)
    await ctx.author.send("Du wurdest erfolgreich entfernt.")

# ================== ADMIN / HOST COMMANDS ==================

def is_admin(ctx):
    roles = [r.name for r in ctx.author.roles]
    return ctx.author.guild_permissions.administrator or ROLE_CHEF in roles or ROLE_HOST in roles

@bot.command()
async def clearall(ctx):
    if not is_admin(ctx):
        await ctx.send("Nur Host oder Admin kann das ausführen.")
        return
    save_data(DATA_FILE, {})
    save_data(COOPS_FILE, {})
    save_data(BACKUP_FILE, {})
    await update_signup_message(ctx.guild)
    await ctx.send("Alle Signups, Coops und Backups wurden gelöscht ✅")

@bot.command()
async def forceadd(ctx, member: discord.Member, *, country):
    if not is_admin(ctx):
        await ctx.send("Nur Host oder Admin kann das ausführen.")
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

@bot.command()
async def forceremove(ctx, member: discord.Member):
    if not is_admin(ctx):
        await ctx.send("Nur Host oder Admin kann das ausführen.")
        return
    uid = str(member.id)
    signups = load_data(DATA_FILE)
    coops = load_data(COOPS_FILE)
    backups = load_data(BACKUP_FILE)

    if uid in signups:
        del signups[uid]
        await remove_roles(member)
    if uid in backups:
        del backups[uid]
    for country, lst in list(coops.items()):
        if int(uid) in lst:
            lst.remove(int(uid))
            if not lst:
                del coops[country]

    save_data(DATA_FILE, signups)
    save_data(COOPS_FILE, coops)
    save_data(BACKUP_FILE, backups)
    await update_signup_message(ctx.guild)
    await ctx.send(f"{member} wurde entfernt ✅")

# ================== GAMEOVER ==================

@bot.command()
async def gameover(ctx):
    if ROLE_CHEF not in [r.name for r in ctx.author.roles] and ROLE_HOST not in [r.name for r in ctx.author.roles]:
        await ctx.send("Nur Chef oder Host kann das ausführen.")
        return

    # DM Fragen
    def check(m):
        return m.author == ctx.author and isinstance(m.channel, discord.DMChannel)

    await ctx.author.send("Gameover wird gestartet. Bitte beantworte die folgenden Fragen per DM:")

    await ctx.author.send("1️⃣ Welches Datum ist heute? (z.B. 10.01.2026)")
    msg1 = await bot.wait_for('message', check=check)
    date_today = msg1.content

    await ctx.author.send("2️⃣ Wann ist das Game ingame geendet? (z.B. 15:30)")
    msg2 = await bot.wait_for('message', check=check)
    ingame_time = msg2.content

    # MVP Auswahl
    guild = ctx.guild
    axis_members = [m for m in guild.members if ROLE_ACHSE in [r.name for r in m.roles]]
    allies_members = [m for m in guild.members if ROLE_ALLIES in [r.name for r in m.roles]]

    axis_options = [discord.SelectOption(label=m.display_name, value=str(m.id)) for m in axis_members]
    allies_options = [discord.SelectOption(label=m.display_name, value=str(m.id)) for m in allies_members]
    winner_options = [discord.SelectOption(label="Achse", value="Achse"),
                      discord.SelectOption(label="Allies", value="Allies")]

    class MVPSelect(discord.ui.Select):
        def __init__(self, options):
            super().__init__(placeholder="Wähle aus", options=options)
            self.result = None

        async def callback(self, interaction):
            self.result = self.values[0]
            self.view.stop()
            await interaction.response.send_message(f"Ausgewählt: {self.result}", ephemeral=True)

    async def ask_select(options, prompt):
        view = discord.ui.View(timeout=300)
        select = MVPSelect(options)
        view.add_item(select)
        await ctx.author.send(prompt, view=view)
        await view.wait()
        return select.result

    mvp_axis_id = await ask_select(axis_options, "3️⃣ Wer ist der Achse MVP?")
    mvp_allies_id = await ask_select(allies_options, "4️⃣ Wer ist der Allies MVP?")
    winner_side = await ask_select(winner_options, "5️⃣ Wer hat gewonnen?")

    # Nachricht kopieren
    signups = load_data(DATA_FILE)
    coops = load_data(COOPS_FILE)
    backups = load_data(BACKUP_FILE)
    signup_channel = guild.get_channel(SIGNUP_CHANNEL_ID)
    try:
        message = await signup_channel.fetch_message(SIGNUP_MESSAGE_ID)
    except:
        await ctx.send("Signup Nachricht nicht gefunden.")
        return

    lines = [f"Game :  Am {date_today} um {ingame_time}",
             f"Gewinner: {winner_side} am ({ingame_time})",
             f"MVP Achse: {discord.utils.get(guild.members, id=int(mvp_axis_id)).mention if mvp_axis_id else 'Keine'}",
             f"MVP Allies: {discord.utils.get(guild.members, id=int(mvp_allies_id)).mention if mvp_allies_id else 'Keine'}",
             "\n**Signups:**"]

    def line(country):
        main_id = next((uid for uid, c in signups.items() if c == country), None)
        coop_ids = coops.get(country, [])
        mentions = []
        if main_id:
            mentions.append(f"<@{main_id}>")
        mentions += [f"<@{cid}>" for cid in coop_ids]
        return f"{country}: {', '.join(mentions)}" if mentions else f"{country}:"

    for c in ALL_COUNTRIES:
        lines.append(line(c))

    # Backups
    backup_mentions = [f"<@{uid}>" for uid in backups.values()]
    if backup_mentions:
        lines.append("\n**Backup:** " + ", ".join(backup_mentions))

    target_channel = guild.get_channel(1454892029267017821)
    if target_channel:
        await target_channel.send("\n".join(lines))

    # Rollen entfernen von allen
    for m in guild.members:
        await remove_roles(m)

# ================== EVENTS ==================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

bot.run(TOKEN)

