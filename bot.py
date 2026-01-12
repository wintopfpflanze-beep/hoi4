import discord
from discord.ext import commands
import json
import os

# ================== CONFIG ==================

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = "!"
SIGNUP_CHANNEL_ID = 1456720618329210995
SIGNUP_MESSAGE_ID = 1460232460787912838
DATA_FILE = "signups.json"

ROLE_KLEINE_MAYORS = "kleine Mayors"
ROLE_MAYOR_WUERDIG = "Mayor würdig"
ROLE_CHEF = "chef"

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

SMALL_COUNTRIES = [
    c for c in ALL_COUNTRIES
    if c not in MAJOR_COUNTRIES and c not in MID_MAJORS
]

# ================== FACTIONS (NEU – NUR UI) ==================

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

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
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

    data = load_data()
    coop_additions = coop_additions or {}

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

# ================== SIGNUP UI (NEU) ==================

class SignupCountrySelect(discord.ui.Select):
    def __init__(self, user, guild, countries):
        self.user = user
        self.guild = guild
        options = [discord.SelectOption(label=c) for c in countries]
        super().__init__(placeholder="Wähle dein Land", options=options)

    async def callback(self, interaction: discord.Interaction):
        data = load_data()
        uid = str(self.user.id)

        if uid in data:
            await interaction.response.send_message("Du bist bereits angemeldet.", ephemeral=True)
            return

        country = self.values[0]
        if country in data.values():
            await interaction.response.send_message("Land bereits vergeben.", ephemeral=True)
            return

        data[uid] = country
        save_data(data)

        await update_signup_message(self.guild)
        await interaction.response.edit_message(
            content=f"✅ Angemeldet als **{country}**",
            embed=None,
            view=None
        )

class FactionSignupView(discord.ui.View):
    def __init__(self, user, guild):
        super().__init__(timeout=120)
        self.user = user
        self.guild = guild

        for name, data in FACTIONS.items():
            button = discord.ui.Button(
                label=name,
                emoji=data["emoji"],
                style=discord.ButtonStyle.primary
            )
            button.callback = self.make_callback(name)
            self.add_item(button)

    def make_callback(self, faction_name):
        async def callback(interaction: discord.Interaction):
            faction = FACTIONS[faction_name]

            embed = discord.Embed(
                title=f"{faction['emoji']} {faction_name}",
                description="Wähle dein Land:",
                color=faction["color"]
            )

            view = discord.ui.View()
            view.add_item(
                SignupCountrySelect(
                    self.user,
                    self.guild,
                    faction["countries"]
                )
            )

            await interaction.response.edit_message(embed=embed, view=view)
        return callback

@bot.command()
async def signup(ctx):
    embed = discord.Embed(
        title="🌍 Länder-Anmeldung",
        description="Wähle zuerst deine Faction:",
        color=discord.Color.blurple()
    )

    await ctx.author.send(
        embed=embed,
        view=FactionSignupView(ctx.author, ctx.guild)
    )
    await ctx.message.delete()
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
    await update_signup_message(ctx.guild)
    await ctx.send("Alle Signups und Coops wurden gelöscht ✅")

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
            coops.setdefault(country, []).append(interaction.user.id)
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
# ================== EVENTS ==================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")




