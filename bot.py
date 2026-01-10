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
ROLE_ACHSER = "Achse"
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

# ================== GLOBAL STATUS ==================

signup_enabled = True

# ================== BOT ==================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# ================== DATA HANDLING ==================

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

    # Länderblöcke
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

    # Backups
    if backups:
        backup_mentions = [f"<@{uid}>" for uid in backups.keys()]
        content += "\n\n**Backup:**\n" + "\n".join(backup_mentions)

    await message.edit(content=content)

# ================== ROLE LOGIC ==================

def get_available_countries(member):
    roles = [r.name for r in member.roles]
    if ROLE_MAYOR_WUERDIG in roles:
        return ALL_COUNTRIES
    if ROLE_KLEINE_MAYORS in roles:
        return SMALL_COUNTRIES + MID_MAJORS
    return SMALL_COUNTRIES

async def assign_roles(member):
    """Automatische Achse/Allies Rollen"""
    guild = member.guild
    signups = load_data(DATA_FILE)
    coops = load_data(COOPS_FILE)

    countries = []
    uid = str(member.id)
    if uid in signups:
        countries.append(signups[uid])
    for country, lst in coops.items():
        if int(uid) in lst:
            countries.append(country)

    # Achse
    if any(c in ["Deutschland", "Italien", "Rumänien", "Spanien", "Ungarn", "Bulgarien", "Finnland", "Jugoslawien", "Japan", "Mandschukuo", "Siam"] for c in countries):
        role = discord.utils.get(guild.roles, name=ROLE_ACHSER)
        if role and role not in member.roles:
            await member.add_roles(role)

    # Allies
    if any(c in ["UdSSR", "Mongolei", "Großbritannien", "USA", "Frankreich", "Kanada", "Südafrika", "Indien", "Australien", "Neuseeland", "Mexiko"] for c in countries):
        role = discord.utils.get(guild.roles, name=ROLE_ALLIES)
        if role and role not in member.roles:
            await member.add_roles(role)

async def remove_game_roles(member):
    guild = member.guild
    for role_name in [ROLE_ACHSER, ROLE_ALLIES]:
        role = discord.utils.get(guild.roles, name=role_name)
        if role and role in member.roles:
            await member.remove_roles(role)

# ================== SIGNUP ==================

class CountrySelect(discord.ui.Select):
    def __init__(self, user, guild_id):
        self.user = user
        self.guild_id = guild_id
        options = [discord.SelectOption(label=c) for c in get_available_countries(user)]
        super().__init__(placeholder="Select your country", options=options)

    async def callback(self, interaction):
        global signup_enabled
        if not signup_enabled:
            await interaction.response.send_message("Signups sind aktuell deaktiviert.", ephemeral=True)
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

        # Rollen vergeben
        await assign_roles(self.user)
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

# ================== BACKUP SIGNUP ==================

class BackupSelect(discord.ui.Select):
    def __init__(self, user):
        self.user = user
        options = [discord.SelectOption(label="Backup anmelden")]
        super().__init__(placeholder="Backup auswählen", options=options)

    async def callback(self, interaction):
        global signup_enabled
        if not signup_enabled:
            await interaction.response.send_message("Signups sind aktuell deaktiviert.", ephemeral=True)
            return

        backups = load_data(BACKUP_FILE)
        uid = str(self.user.id)
        if uid in backups:
            await interaction.response.send_message("Du bist bereits als Backup eingetragen.", ephemeral=True)
            return

        backups[uid] = True
        save_data(BACKUP_FILE, backups)
        await update_signup_message(interaction.guild)
        await interaction.response.edit_message(content="Du bist nun als **Backup** eingetragen.", view=None)

class BackupView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=120)
        self.add_item(BackupSelect(user))

@bot.command()
async def backup(ctx):
    await ctx.author.send("Möchtest du als Backup eingetragen werden?", view=BackupView(ctx.author))
    await ctx.message.delete()

# ================== UNSIGN (MAIN + COOP + BACKUP) ==================

@bot.command()
async def unsign(ctx):
    uid = str(ctx.author.id)
    removed = False

    # Main
    signups = load_data(DATA_FILE)
    if uid in signups:
        del signups[uid]
        save_data(DATA_FILE, signups)
        removed = True

    # Coop
    coops = load_data(COOPS_FILE)
    for country, lst in list(coops.items()):
        if int(uid) in lst:
            lst.remove(int(uid))
            if not lst:
                del coops[country]
            removed = True
    save_data(COOPS_FILE, coops)

    # Backup
    backups = load_data(BACKUP_FILE)
    if uid in backups:
        del backups[uid]
        save_data(BACKUP_FILE, backups)
        removed = True

    # Rollen entfernen
    await remove_game_roles(ctx.author)

    if removed:
        await update_signup_message(ctx.guild)
        await ctx.author.send("Du wurdest erfolgreich entfernt.")
    else:
        await ctx.author.send("Du bist weder Main-Spieler, Coop noch Backup.")

# ================== SIGNUP ON/OFF ==================

def is_chef(member):
    return ROLE_CHEF in [r.name for r in member.roles]

@bot.command()
async def signupoff(ctx):
    global signup_enabled
    if not is_chef(ctx.author):
        await ctx.send("Nur Chef kann Signups deaktivieren.")
        return
    signup_enabled = False
    await ctx.send("Signups wurden deaktiviert ✅")

@bot.command()
async def signupon(ctx):
    global signup_enabled
    if not is_chef(ctx.author):
        await ctx.send("Nur Chef kann Signups aktivieren.")
        return
    signup_enabled = True
    await ctx.send("Signups wurden aktiviert ✅")

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
            await assign_roles(interaction.user)
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

# ================== ADMIN COMMANDS ==================

def is_admin(ctx):
    return ctx.author.guild_permissions.administrator

@bot.command(name="clear")
async def clear_all(ctx, *, arg=None):
    if not is_admin(ctx):
        await ctx.send("Nur Admins können diesen Befehl ausführen.")
        return
    if arg != "all":
        await ctx.send("Verwendung: `!clear all`")
        return

    save_data(DATA_FILE, {})
    save_data(COOPS_FILE, {})
    save_data(BACKUP_FILE, {})
    await update_signup_message(ctx.guild)
    await ctx.send("Alle Signups, Coops und Backups wurden gelöscht ✅")

@bot.command(name="forceadd")
async def force_add(ctx, member: discord.Member, *, country):
    if not is_admin(ctx):
        await ctx.send("Nur Admins können diesen Befehl ausführen.")
        return

    if country not in ALL_COUNTRIES:
        await ctx.send(f"Ungültiges Land: {country}")
        return

    signups = load_data(DATA_FILE)
    signups[str(member.id)] = country
    save_data(DATA_FILE, signups)
    await assign_roles(member)
    await update_signup_message(ctx.guild)
    await ctx.send(f"{member} wurde als Main-Spieler von {country} hinzugefügt ✅")

@bot.command(name="forceremove")
async def force_remove(ctx, member: discord.Member):
    if not is_admin(ctx):
        await ctx.send("Nur Admins können diesen Befehl ausführen.")
        return

    uid = str(member.id)
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
    await remove_game_roles(member)
    await update_signup_message(ctx.guild)

    if removed:
        await ctx.send(f"{member} wurde entfernt ✅")
    else:
        await ctx.send(f"{member} war nicht angemeldet ❌")

# ================== GAMEOVER ==================

@bot.command()
async def gameover(ctx):
    if not is_chef(ctx.author):
        await ctx.send("Nur Chef kann ein Game beenden.")
        return

    dm_channel = await ctx.author.create_dm()
    answers = {}

    def check(m):
        return m.author == ctx.author and isinstance(m.channel, discord.DMChannel)

    # Schritt 1: Datum
    await dm_channel.send("📅 Welches Datum ist heute?")
    msg = await bot.wait_for("message", check=check)
    answers['date'] = msg.content

    # Schritt 2: Ingame-Endzeit
    await dm_channel.send("⏱️ Wann ist das Game ingame geendet?")
    msg = await bot.wait_for("message", check=check)
    answers['endtime'] = msg.content

    guild = ctx.guild

    # Schritt 3: MVP Achse
    axes_role = discord.utils.get(guild.roles, name=ROLE_ACHSER)
    axes_members = axes_role.members if axes_role else []
    options = [m.display_name for m in axes_members] or ["keiner"]

    await dm_channel.send(f"🏆 Wer ist der Achse MVP? Optionen: {', '.join(options)}")
    msg = await bot.wait_for("message", check=check)
    answers['mvp_achse'] = msg.content

    # Schritt 4: MVP Allies
    allies_role = discord.utils.get(guild.roles, name=ROLE_ALLIES)
    allies_members = allies_role.members if allies_role else []
    options = [m.display_name for m in allies_members] or ["keiner"]

    await dm_channel.send(f"🏆 Wer ist der Allies MVP? Optionen: {', '.join(options)}")
    msg = await bot.wait_for("message", check=check)
    answers['mvp_allies'] = msg.content

    # Schritt 5: Gewinner
    await dm_channel.send("🏅 Wer hat gewonnen? (Achse / Allies)")
    msg = await bot.wait_for("message", check=check)
    answers['winner'] = msg.content

    # Schritt 2: Signup kopieren
    channel = guild.get_channel(SIGNUP_CHANNEL_ID)
    message = await channel.fetch_message(SIGNUP_MESSAGE_ID)
    signup_text = message.content

    target_channel = guild.get_channel(1454892029267017821)
    report = (
        f"Game: Am {answers['date']} um {answers['endtime']}\n\n"
        f"Gewinner: {answers['winner']} am {answers['endtime']}\n"
        f"MVP Achse: {answers['mvp_achse']}\n"
        f"MVP Allies: {answers['mvp_allies']}\n\n"
        "--------------------------------\n"
        f"{signup_text}"
    )
    await target_channel.send(report)

    # Rollen entfernen
    for member in guild.members:
        await remove_game_roles(member)

    await ctx.send("Gameover abgeschlossen und Rollen zurückgesetzt ✅")

# ================== EVENTS ==================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

bot.run(TOKEN)



