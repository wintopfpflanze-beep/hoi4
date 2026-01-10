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

# ================== ROLLENLOGIK ==================

async def assign_roles(guild):
    signups = load_data(DATA_FILE)
    for uid, country in signups.items():
        member = guild.get_member(int(uid))
        if not member:
            continue
        if country in AXIS_TEAMS:
            role = discord.utils.get(guild.roles, name=ROLE_AXE)
            if role not in member.roles:
                await member.add_roles(role)
        elif country in ALLIES_TEAMS:
            role = discord.utils.get(guild.roles, name=ROLE_ALLIES)
            if role not in member.roles:
                await member.add_roles(role)

async def remove_roles(guild):
    signups = load_data(DATA_FILE)
    coops = load_data(COOPS_FILE)
    all_ids = set(list(signups.keys()) + [str(i) for lst in coops.values() for i in lst])
    for member in guild.members:
        if str(member.id) not in all_ids:
            axe_role = discord.utils.get(guild.roles, name=ROLE_AXE)
            allies_role = discord.utils.get(guild.roles, name=ROLE_ALLIES)
            if axe_role in member.roles:
                await member.remove_roles(axe_role)
            if allies_role in member.roles:
                await member.remove_roles(allies_role)

# ================== SIGNUP / UNSIGN ==================
# Hier bleibt exakt dein funktionierender Code unverändert
# Dein ursprünglicher !signup, !unsign, Coop Code kommt hier
# ...

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

# ================== ADMIN / HOST COMMANDS ==================

def is_host_or_chef(ctx):
    return any(r.name in [ROLE_CHEF, ROLE_HOST] for r in ctx.author.roles)

# !clearall
@bot.command(name="clearall")
async def clear_all(ctx):
    if not is_host_or_chef(ctx):
        await ctx.send("Nur Chef oder Host darf das ausführen ❌")
        return
    save_data(DATA_FILE, {})
    save_data(COOPS_FILE, {})
    save_data(BACKUP_FILE, {})
    await update_signup_message(ctx.guild)
    await ctx.send("Alle Signups, Coops und Backups gelöscht ✅")

# !forceadd
@bot.command(name="forceadd")
async def force_add(ctx, member: discord.Member, *, country):
    if not is_host_or_chef(ctx):
        await ctx.send("Nur Chef oder Host darf das ausführen ❌")
        return
    if country not in ALL_COUNTRIES:
        await ctx.send("Ungültiges Land ❌")
        return
    signups = load_data(DATA_FILE)
    signups[str(member.id)] = country
    save_data(DATA_FILE, signups)
    await update_signup_message(ctx.guild)
    await ctx.send(f"{member} als Main-Spieler für {country} hinzugefügt ✅")

# !forceremove
@bot.command(name="forceremove")
async def force_remove(ctx, member: discord.Member):
    if not is_host_or_chef(ctx):
        await ctx.send("Nur Chef oder Host darf das ausführen ❌")
        return
    uid = str(member.id)
    signups = load_data(DATA_FILE)
    coops = load_data(COOPS_FILE)
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
    save_data(DATA_FILE, signups)
    save_data(COOPS_FILE, coops)
    await update_signup_message(ctx.guild)
    await ctx.send(f"{member} wurde entfernt ✅" if removed else f"{member} war nicht angemeldet ❌")

# ================== GAMEOVER ==================

@bot.command(name="gameover")
async def gameover(ctx):
    if not is_host_or_chef(ctx):
        await ctx.send("Nur Chef oder Host darf das ausführen ❌")
        return

    guild = ctx.guild
    chef = ctx.author

    # 5 Fragen via DM
    dm = await chef.create_dm()
    await dm.send("1. Welches Datum ist heute?")
    date_msg = await bot.wait_for("message", check=lambda m: m.author == chef and isinstance(m.channel, discord.DMChannel))
    await dm.send("2. Wann ist das Game ingame geendet?")
    end_msg = await bot.wait_for("message", check=lambda m: m.author == chef and isinstance(m.channel, discord.DMChannel))

    # MVP Achse
    axe_members = [m for m in guild.members if discord.utils.get(m.roles, name=ROLE_AXE)]
    axe_options = [discord.SelectOption(label=m.display_name, value=str(m.id)) for m in axe_members]

    allies_members = [m for m in guild.members if discord.utils.get(m.roles, name=ROLE_ALLIES)]
    allies_options = [discord.SelectOption(label=m.display_name, value=str(m.id)) for m in allies_members]

    class MVPSelect(discord.ui.Select):
        def __init__(self, options, question):
            super().__init__(placeholder=question, options=options)
            self.selected = None
        async def callback(self, interaction):
            self.selected = self.values[0]
            self.view.stop()
            await interaction.response.send_message(f"{self.placeholder} ausgewählt ✅", ephemeral=True)

    class MVPView(discord.ui.View):
        def __init__(self, select):
            super().__init__()
            self.add_item(select)

    select1 = MVPSelect(axe_options, "Achse MVP")
    view1 = MVPView(select1)
    await dm.send("3. Wer ist Achse MVP?", view=view1)
    await view1.wait()
    mvp_axe = guild.get_member(int(select1.selected)) if select1.selected else None

    select2 = MVPSelect(allies_options, "Allies MVP")
    view2 = MVPView(select2)
    await dm.send("4. Wer ist Allies MVP?", view=view2)
    await view2.wait()
    mvp_allies = guild.get_member(int(select2.selected)) if select2.selected else None

    # Gewinner Achse/Allies
    winner_select = discord.ui.Select(
        placeholder="Wer hat gewonnen?",
        options=[
            discord.SelectOption(label="Achse", value="Achse"),
            discord.SelectOption(label="Allies", value="Allies")
        ]
    )
    class WinnerView(discord.ui.View):
        def __init__(self, select):
            super().__init__()
            self.add_item(select)
            self.selected = None
        async def interaction_check(self, interaction):
            return interaction.user == chef
        async def on_timeout(self):
            pass
    winner_view = WinnerView(winner_select)
    await dm.send("5. Wer hat gewonnen?", view=winner_view)
    # Manuell warten
    def check(i):
        return i.user == chef and i.data["component_type"] == 3
    winner_inter = await bot.wait_for("interaction", check=check)
    winner = winner_inter.data["values"][0]

    # Update Signup Nachricht kopieren
    signup_channel = guild.get_channel(SIGNUP_CHANNEL_ID)
    message = await signup_channel.fetch_message(SIGNUP_MESSAGE_ID)
    backup_channel = guild.get_channel(BACKUP_CHANNEL_ID)
    content = f"Game : Am {date_msg.content} um {end_msg.content}\n\nGewinner: {winner}\n\nMVP Achse: {mvp_axe.display_name if mvp_axe else 'N/A'}\nMVP Allies: {mvp_allies.display_name if mvp_allies else 'N/A'}\n\n{message.content}"
    await backup_channel.send(content)

    # Rollen entfernen
    await remove_roles(guild)

# ================== EVENTS ==================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

bot.run(TOKEN)

