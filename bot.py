import discord
from discord.ext import commands
import json
import os

# ================== CONFIG ==================

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = "!"
SIGNUP_CHANNEL_ID = 1456720618329210995
SIGNUP_MESSAGE_ID = 1456968992215404590
BACKUP_CHANNEL_ID = 1454892029267017821  # Für Gameover-Kopie
DATA_FILE = "signups.json"
COOPS_FILE = "coops.json"
BACKUP_FILE = "backup.json"

ROLE_KLEINE_MAYORS = "kleine Mayors"
ROLE_MAYOR_WUERDIG = "Mayor würdig"
ROLE_CHEF = "Chef"
ROLE_ACHSE = "Achse"
ROLE_ALLIES = "Allies"
ROLE_HOST = "Host"

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
    )

    if backups:
        content += "**Backup:**\n"
        for uid, name in backups.items():
            content += f"<@{uid}> ({name})\n"

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
    guild_roles = {r.name: r for r in member.guild.roles}
    if country in MAJOR_COUNTRIES + MID_MAJORS + ["Rumänien","Spanien","Ungarn","Bulgarien","Finnland","Jugoslawien","Japan","Mandschukuo","Siam","Italien","Deutschland"]:
        await member.add_roles(guild_roles[ROLE_ACHSE])
    else:
        await member.add_roles(guild_roles[ROLE_ALLIES])

async def remove_roles(member):
    guild_roles = {r.name: r for r in member.guild.roles}
    for r in [ROLE_ACHSE, ROLE_ALLIES]:
        await member.remove_roles(guild_roles[r])

# ================== SIGNUP ==================
# --- unverändert, nur assign roles hinzufügen ---

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

# ================== UNSIGN (MAIN + COOP + BACKUP) ==================

@bot.command()
async def unsign(ctx):
    uid = str(ctx.author.id)
    signups = load_data(DATA_FILE)
    coops = load_data(COOPS_FILE)
    backups = load_data(BACKUP_FILE)
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

    if uid in backups:
        del backups[uid]
        save_data(BACKUP_FILE, backups)
        removed = True

    save_data(COOPS_FILE, coops)
    await remove_roles(ctx.author)
    await update_signup_message(ctx.guild)

    if not removed:
        await ctx.author.send("Du bist weder Main-Spieler noch Coop noch Backup.")
        return

    await ctx.author.send("Du wurdest erfolgreich entfernt.")

# ================== BACKUP ==================

@bot.command()
async def backup(ctx):
    backups = load_data(BACKUP_FILE)
    backups[str(ctx.author.id)] = str(ctx.author)
    save_data(BACKUP_FILE, backups)
    await update_signup_message(ctx.guild)
    await ctx.author.send("Du wurdest als Backup eingetragen ✅")

# ================== GAMEOVER ==================

@bot.command()
async def gameover(ctx):
    roles = [r.name for r in ctx.author.roles]
    if ROLE_CHEF not in roles and ROLE_HOST not in roles:
        await ctx.send("Nur Chef oder Host kann das Game beenden.")
        return

    def check(m):
        return m.author == ctx.author and isinstance(m.channel, discord.DMChannel)

    dm = ctx.author

    await dm.send("1️⃣ Welches Datum ist Heute? (z.B. 10.01.2026)")
    date_msg = await bot.wait_for("message", check=check)
    date = date_msg.content

    await dm.send("2️⃣ Wann ist das Game ingame geendet? (z.B. 20:30)")
    time_msg = await bot.wait_for("message", check=check)
    time = time_msg.content

    # Achse MVP
    await dm.send("3️⃣ Wer ist der Achse MVP?")
    guild = ctx.guild
    achse_role = discord.utils.get(guild.roles, name=ROLE_ACHSE)
    achse_members = [m for m in guild.members if achse_role in m.roles]
    options = [discord.SelectOption(label=m.display_name, value=str(m.id)) for m in achse_members]
    class AchseSelect(discord.ui.Select):
        def __init__(self):
            super().__init__(placeholder="Wähle Achse MVP", options=options)
            self.value = None
        async def callback(self, interaction):
            self.value = self.values[0]
            await interaction.response.send_message(f"Ausgewählt: <@{self.value}>", ephemeral=True)
            self.view.stop()
    view_achse = discord.ui.View()
    select_achse = AchseSelect()
    view_achse.add_item(select_achse)
    await dm.send("Wähle den Achse MVP:", view=view_achse)
    await view_achse.wait()
    mvp_achse = select_achse.value

    # Allies MVP
    await dm.send("4️⃣ Wer ist der Allies MVP?")
    allies_role = discord.utils.get(guild.roles, name=ROLE_ALLIES)
    allies_members = [m for m in guild.members if allies_role in m.roles]
    options = [discord.SelectOption(label=m.display_name, value=str(m.id)) for m in allies_members]
    class AlliesSelect(discord.ui.Select):
        def __init__(self):
            super().__init__(placeholder="Wähle Allies MVP", options=options)
            self.value = None
        async def callback(self, interaction):
            self.value = self.values[0]
            await interaction.response.send_message(f"Ausgewählt: <@{self.value}>", ephemeral=True)
            self.view.stop()
    view_allies = discord.ui.View()
    select_allies = AlliesSelect()
    view_allies.add_item(select_allies)
    await dm.send("Wähle den Allies MVP:", view=view_allies)
    await view_allies.wait()
    mvp_allies = select_allies.value

    # Gewinner
    await dm.send("5️⃣ Wer hat gewonnen?")
    class WinnerSelect(discord.ui.Select):
        def __init__(self):
            super().__init__(placeholder="Wähle Gewinner", options=[
                discord.SelectOption(label="Achse", value="Achse"),
                discord.SelectOption(label="Allies", value="Allies")
            ])
            self.value = None
        async def callback(self, interaction):
            self.value = self.values[0]
            await interaction.response.send_message(f"Ausgewählt: {self.value}", ephemeral=True)
            self.view.stop()
    view_winner = discord.ui.View()
    select_winner = WinnerSelect()
    view_winner.add_item(select_winner)
    await dm.send("Wähle den Gewinner:", view=view_winner)
    await view_winner.wait()
    winner = select_winner.value

    # Nachricht kopieren
    signup_channel = guild.get_channel(SIGNUP_CHANNEL_ID)
    backup_channel = guild.get_channel(BACKUP_CHANNEL_ID)
    signup_message = await signup_channel.fetch_message(SIGNUP_MESSAGE_ID)
    content = f"Game : {date} um {time}\nGewinner: {winner}\nMVP Achse: <@{mvp_achse}>\nMVP Allies: <@{mvp_allies}>\n\n{signup_message.content}"
    await backup_channel.send(content)

    # Rollen entfernen
    for m in guild.members:
        await remove_roles(m)

# ================== EVENTS ==================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

bot.run(TOKEN)


