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
        main_mentions = []
        main_id = next((uid for uid, c in signups.items() if c == country), None)
        if main_id:
            main_mentions.append(f"<@{main_id}>")
        coop_ids = coops.get(country, [])
        main_mentions += [f"<@{cid}>" for cid in coop_ids]
        return f"{country}: {', '.join(main_mentions)}" if main_mentions else f"{country}:"

    content = "**Achsenmächte:**\n" + "\n".join([line(c) for c in [
        "Deutschland","Italien","Rumänien","Spanien","Ungarn","Bulgarien","Finnland","Jugoslawien"]])
    content += "\n\n**Japan-Team:**\n" + "\n".join([line(c) for c in ["Japan","Mandschukuo","Siam"]])
    content += "\n\n**Komintern:**\n" + "\n".join([line(c) for c in ["UdSSR","Mongolei"]])
    content += "\n\n**Alliierte:**\n" + "\n".join([line(c) for c in [
        "Großbritannien","USA","Frankreich","Kanada","Südafrika","Indien","Australien","Neuseeland","Mexiko"]])

    if backups:
        content += "\n\n**Backup:**\n"
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
    roles = [r.name for r in member.roles]
    guild_roles = {r.name:r for r in member.guild.roles}
    if country in ["Deutschland","Italien","Rumänien","Spanien","Ungarn","Bulgarien","Finnland","Jugoslawien","Japan","Mandschukuo","Siam"]:
        if "Achse" in guild_roles and "Achse" not in roles:
            await member.add_roles(guild_roles["Achse"])
    elif country in ["UdSSR","Mongolei","Großbritannien","USA","Frankreich","Kanada","Südafrika","Indien","Australien","Neuseeland","Mexiko"]:
        if "Allies" in guild_roles and "Allies" not in roles:
            await member.add_roles(guild_roles["Allies"])

async def remove_roles(member):
    guild_roles = {r.name:r for r in member.guild.roles}
    for rname in ["Achse","Allies"]:
        if rname in guild_roles and guild_roles[rname] in member.roles:
            await member.remove_roles(guild_roles[rname])

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

    if uid in signups:
        del signups[uid]
        save_data(DATA_FILE, signups)
        await remove_roles(ctx.author)
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
    await update_signup_message(ctx.guild)
    if removed:
        await ctx.author.send("Du wurdest erfolgreich entfernt.")
    else:
        await ctx.author.send("Du bist weder Main-Spieler noch Coop noch Backup.")

# ================== BACKUP ==================
@bot.command()
async def backup(ctx):
    backups = load_data(BACKUP_FILE)
    uid = str(ctx.author.id)
    if uid in backups:
        await ctx.author.send("Du bist bereits als Backup eingetragen.")
        return
    backups[uid] = str(ctx.author)
    save_data(BACKUP_FILE, backups)
    await update_signup_message(ctx.guild)
    await ctx.author.send("Du wurdest als Backup eingetragen ✅")

# ================== ADMIN / HOST COMMANDS ==================
def is_admin(ctx):
    return any(r.name in ["Host", ROLE_CHEF] for r in ctx.author.roles) or ctx.author.guild_permissions.administrator

@bot.command(name="clearall")
async def clear_all(ctx):
    if not is_admin(ctx):
        await ctx.send("Nur Admins/Hosts können diesen Befehl ausführen.")
        return
    save_data(DATA_FILE,{})
    save_data(COOPS_FILE,{})
    save_data(BACKUP_FILE,{})
    await update_signup_message(ctx.guild)
    await ctx.send("Alle Signups, Coops und Backups wurden gelöscht ✅")

@bot.command(name="forceadd")
async def force_add(ctx, member: discord.Member, *, country):
    if not is_admin(ctx):
        await ctx.send("Nur Admins/Hosts können diesen Befehl ausführen.")
        return
    if country not in ALL_COUNTRIES:
        await ctx.send("Ungültiges Land.")
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
        await ctx.send("Nur Admins/Hosts können diesen Befehl ausführen.")
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
    for country,lst in list(coops.items()):
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
    await ctx.send(f"{member} wurde entfernt ✅" if removed else f"{member} war nicht angemeldet ❌")

# ================== EVENTS ==================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

bot.run(TOKEN)



