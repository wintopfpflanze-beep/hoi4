import discord
from discord.ext import commands
import json
import os

# ================== CONFIG ==================

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = "!"
SIGNUP_CHANNEL_ID = 1456720618329210995
SIGNUP_MESSAGE_ID = 1460232460787912838
STORE_CHANNEL_ID = 1454892029267017821  # Ziel-Channel für !store
STORE_QUESTIONS_CHANNEL_ID = 1460274020418060388  # Channel für Fragen
DATA_FILE = "signups.json"
COOPS_FILE = "coops.json"

ROLE_KLEINE_MAYORS = "kleine Mayors"
ROLE_MAYOR_WUERDIG = "Mayor würdig"
ROLE_CHEF = "chef"
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

# ================== FACTIONS ==================

FACTIONS = {
    "Achsenmächte": {
        "emoji": "⬛",
        "color": discord.Color.dark_red(),
        "countries": ["Deutschland", "Italien", "Rumänien", "Spanien", "Ungarn", "Bulgarien", "Finnland", "Jugoslawien"]
    },
    "Japan-Team": {
        "emoji": "🟨",
        "color": discord.Color.gold(),
        "countries": ["Japan", "Mandschukuo", "Siam"]
    },
    "Komintern": {
        "emoji": "🟥",
        "color": discord.Color.purple(),
        "countries": ["UdSSR", "Mongolei"]
    },
    "Alliierte": {
        "emoji": "🟦",
        "color": discord.Color.blue(),
        "countries": ["Großbritannien", "USA", "Frankreich", "Kanada", "Südafrika", "Indien", "Australien", "Neuseeland", "Mexiko"]
    }
}

# ================== BOT ==================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# ================== DATA ==================

def load_data(file_path):
    if not os.path.exists(file_path):
        return {}
    with open(file_path, "r") as f:
        return json.load(f)

def save_data(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

# ================== MESSAGE UPDATE ==================

async def update_signup_message(guild, coop_additions=None):
    channel = guild.get_channel(SIGNUP_CHANNEL_ID)
    if not channel:
        return
    try:
        message = await channel.fetch_message(SIGNUP_MESSAGE_ID)
    except discord.NotFound:
        return

    data = load_data(DATA_FILE)
    coop_additions = coop_additions or load_data(COOPS_FILE)

    def line(country):
        main_id = next((uid for uid, c in data.items() if c == country), None)
        coop_ids = coop_additions.get(country, [])
        if main_id:
            mentions = [f"<@{main_id}>"] + [f"<@{cid}>" for cid in coop_ids]
            return f"{country}: " + ", ".join(mentions)
        return f"{country}:"

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
    return content  # für !store

# ================== SIGNUP UI ==================

class SignupCountrySelect(discord.ui.Select):
    def __init__(self, user, guild, countries):
        self.user = user
        self.guild = guild
        options = [discord.SelectOption(label=c) for c in countries]
        super().__init__(placeholder="Wähle dein Land", options=options)

    async def callback(self, interaction: discord.Interaction):
        data = load_data(DATA_FILE)
        uid = str(self.user.id)
        if uid in data:
            await interaction.response.send_message("Du bist bereits angemeldet.", ephemeral=True)
            return
        country = self.values[0]
        if country in data.values():
            await interaction.response.send_message("Land bereits vergeben.", ephemeral=True)
            return
        data[uid] = country
        save_data(DATA_FILE, data)
        await update_signup_message(self.guild)
        await interaction.response.edit_message(content=f"✅ Angemeldet als **{country}**", embed=None, view=None)

class FactionSignupView(discord.ui.View):
    def __init__(self, user, guild):
        super().__init__(timeout=120)
        self.user = user
        self.guild = guild
        for name, data in FACTIONS.items():
            button = discord.ui.Button(label=name, emoji=data["emoji"], style=discord.ButtonStyle.primary)
            button.callback = self.make_callback(name)
            self.add_item(button)

    def make_callback(self, faction_name):
        async def callback(interaction: discord.Interaction):
            faction = FACTIONS[faction_name]
            embed = discord.Embed(title=f"{faction['emoji']} {faction_name}", description="Wähle dein Land:", color=faction["color"])
            view = discord.ui.View()
            view.add_item(SignupCountrySelect(self.user, self.guild, faction["countries"]))
            await interaction.response.edit_message(embed=embed, view=view)
        return callback

@bot.command()
async def signup(ctx):
    embed = discord.Embed(title="🌍 Länder-Anmeldung", description="Wähle zuerst deine Faction:", color=discord.Color.blurple())
    await ctx.author.send(embed=embed, view=FactionSignupView(ctx.author, ctx.guild))
    await ctx.message.delete()

# ================== ROLE CHECK ==================

def is_host(ctx):
    host_role = discord.utils.get(ctx.guild.roles, name=ROLE_HOST)
    return host_role in ctx.author.roles

# ================== ADMIN COMMANDS ==================

@bot.command(name="clear")
async def clear_all(ctx, *, arg=None):
    if not is_host(ctx):
        await ctx.send("Nur Hosts können diesen Befehl ausführen.")
        return
    if arg != "all":
        await ctx.send("Verwendung: `!clear all`")
        return
    save_data(DATA_FILE, {})
    save_data(COOPS_FILE, {})
    await update_signup_message(ctx.guild)
    await ctx.send("Alle Signups und Coops wurden gelöscht ✅")

@bot.command(name="forceadd")
async def force_add(ctx, member: discord.Member, *, country):
    if not is_host(ctx):
        await ctx.send("Nur Hosts können diesen Befehl ausführen.")
        return
    if country not in ALL_COUNTRIES:
        await ctx.send(f"Ungültiges Land: {country}")
        return
    signups = load_data(DATA_FILE)
    signups[str(member.id)] = country
    save_data(DATA_FILE, signups)
    await update_signup_message(ctx.guild)
    await ctx.send(f"{member} wurde als Main-Spieler von {country} hinzugefügt ✅")

@bot.command(name="forceremove")
async def force_remove(ctx, member: discord.Member):
    if not is_host(ctx):
        await ctx.send("Nur Hosts können diesen Befehl ausführen.")
        return
    uid = str(member.id)
    signups = load_data(DATA_FILE)
    coops = load_data(COOPS_FILE)
    removed = False
    if uid in signups:
        del signups[uid]
        removed = True
    for country, lst in list(coops.items()):
        if uid in lst:
            lst.remove(uid)
            if not lst:
                del coops[country]
            removed = True
    save_data(DATA_FILE, signups)
    save_data(COOPS_FILE, coops)
    await update_signup_message(ctx.guild)
    if removed:
        await ctx.send(f"{member} wurde entfernt ✅")
    else:
        await ctx.send(f"{member} war nicht angemeldet ❌")

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
            coops.setdefault(country, []).append(str(interaction.user.id))
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

# ================== UNSIGN ==================

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
        if uid in lst:
            lst.remove(uid)
            if not lst:
                del coops[country]
            removed = True
    save_data(COOPS_FILE, coops)
    if not removed:
        await ctx.author.send("Du bist weder Main-Spieler noch Coop.")
        return
    await update_signup_message(ctx.guild)
    await ctx.author.send("Du wurdest erfolgreich entfernt.")

# ================== STORE ==================

class WinnerSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label="Allies"), discord.SelectOption(label="Achse")]
        super().__init__(placeholder="Wer hat gewonnen?", options=options)
        self.value_selected = None
    async def callback(self, interaction: discord.Interaction):
        self.value_selected = self.values[0]
        self.view.stop()
        await interaction.response.send_message(f"Gewinner ausgewählt: {self.values[0]}", ephemeral=True)

class StoreView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.winner = None
        self.date = None
        self.ingame_time = None
        self.mvp_achse = None
        self.mvp_allies = None
        self.game_number = None

@bot.command()
async def store(ctx):
    if not is_host(ctx):
        await ctx.send("Nur Hosts können diesen Befehl ausführen.")
        return
    store_channel = bot.get_channel(STORE_CHANNEL_ID)
    question_channel = bot.get_channel(STORE_QUESTIONS_CHANNEL_ID)
    if not store_channel or not question_channel:
        await ctx.send("Fehler: Ziel- oder Frage-Channel nicht gefunden.")
        return

    # 1. Gewinner abfragen
    view = discord.ui.View()
    winner_select = WinnerSelect()
    view.add_item(winner_select)
    await question_channel.send("Wer hat gewonnen?", view=view)
    await view.wait()
    winner = winner_select.value_selected

    # 2. Datum
    await question_channel.send("Wann war das Game? (Datum/Uhrzeit eingeben)")
    def check_msg(m):
        return m.author == ctx.author and m.channel == question_channel
    msg = await bot.wait_for("message", check=check_msg)
    date = msg.content

    # 3. Ingame Zeit
    await question_channel.send("Ingame Zeit?")
    msg = await bot.wait_for("message", check=check_msg)
    ingame_time = msg.content

    # 4. MVP Achse
    await question_channel.send("MVP Achse? (Mention eingeben)")
    msg = await bot.wait_for("message", check=check_msg)
    mvp_achse = msg.content

    # 5. MVP Allies
    await question_channel.send("MVP Allies? (Mention eingeben)")
    msg = await bot.wait_for("message", check=check_msg)
    mvp_allies = msg.content

    # 6. Game Nummer
    await question_channel.send("Das wie vielte Game war das?")
    msg = await bot.wait_for("message", check=check_msg)
    game_number = msg.content

    # Signups kopieren
    content = await update_signup_message(ctx.guild)  # gibt content zurück
    final_content = (
        f"Game: {game_number} am {date} 
        (Ingame Zeit: {ingame_time})\n\n"
        f"Gewinner: {winner}\n"
        f"MVP Achse: {mvp_achse}\n"
        f"MVP Allies: {mvp_allies}\n\n"
        f"{content}"
    )
    await store_channel.send(final_content)
    await ctx.send("Game wurde erfolgreich gespeichert ✅")

# ================== EVENTS ==================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

bot.run(TOKEN)





