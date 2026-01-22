import os
import re
import discord
from discord.ext import commands
from discord import app_commands

# ----------------------------
# CONFIG
# ----------------------------
GUILD_ID = 998651148829466745
REGISTRATION_CHANNEL_ID = 1463756329939374110  # <-- CHANGE THIS
VERIFIED_ROLE_ID = 1462585050779615355

PANEL_TITLE = "Server Access"
PANEL_DESC = "Click **Register** to set your in-game nickname and unlock the server."

NICKNAME_MIN_LEN = 3
NICKNAME_MAX_LEN = 20
NICKNAME_REGEX = re.compile(r"^[\w .\-]{3,20}$", re.UNICODE)

# ----------------------------
# BOT SETUP
# ----------------------------
intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
guild_obj = discord.Object(id=GUILD_ID)


def validate_nickname(nick: str):
    nick = nick.strip()

    if not (NICKNAME_MIN_LEN <= len(nick) <= NICKNAME_MAX_LEN):
        return False, "Nickname length is invalid."

    if not NICKNAME_REGEX.match(nick):
        return False, "Invalid characters in nickname."

    if "@everyone" in nick or "@here" in nick:
        return False, "That nickname is not allowed."

    return True, ""


# ----------------------------
# MODAL
# ----------------------------
class NicknameModal(discord.ui.Modal, title="Set your in-game nickname"):
    nickname = discord.ui.TextInput(
        label="In-game nickname",
        placeholder="Enter your nickname",
        min_length=NICKNAME_MIN_LEN,
        max_length=NICKNAME_MAX_LEN
    )

    async def on_submit(self, interaction: discord.Interaction):
        member = interaction.user
        guild = interaction.guild

        verified_role = guild.get_role(VERIFIED_ROLE_ID)
        if not verified_role:
            return await interaction.response.send_message(
                "Verified role not found. Contact staff.",
                ephemeral=True
            )

        if verified_role in member.roles:
            return await interaction.response.send_message(
                "You already have access.",
                ephemeral=True
            )

        nick = self.nickname.value.strip()
        ok, err = validate_nickname(nick)
        if not ok:
            return await interaction.response.send_message(f"❌ {err}", ephemeral=True)

        try:
            await member.edit(nick=nick, reason="Registration completed")
            await member.add_roles(verified_role, reason="Registration completed")
        except discord.Forbidden:
            return await interaction.response.send_message(
                "❌ Missing permissions. Contact staff.",
                ephemeral=True
            )

        await interaction.response.send_message(
            f"✅ Registration complete! Welcome **{nick}**",
            ephemeral=True
        )


# ----------------------------
# BUTTON VIEW
# ----------------------------
class RegisterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Register",
        style=discord.ButtonStyle.success,
        custom_id="register_button"
    )
    async def register(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NicknameModal())


# ----------------------------
# SLASH COMMAND
# ----------------------------
@bot.tree.command(
    name="postpanel",
    description="Post the registration panel",
    guild=guild_obj
)
@app_commands.checks.has_permissions(administrator=True)
async def postpanel(interaction: discord.Interaction):
    channel = interaction.guild.get_channel(REGISTRATION_CHANNEL_ID)
    if not channel:
        return await interaction.response.send_message(
            "Registration channel not found.",
            ephemeral=True
        )

    embed = discord.Embed(
        title=PANEL_TITLE,
        description=PANEL_DESC
    )

    await channel.send(embed=embed, view=RegisterView())
    await interaction.response.send_message(
        "✅ Registration panel posted.",
        ephemeral=True
    )


# ----------------------------
# EVENTS
# ----------------------------
@bot.event
async def setup_hook():
    bot.add_view(RegisterView())
    await bot.tree.sync(guild=guild_obj)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")


# ----------------------------
# RUN
# ----------------------------
token = os.getenv("DISCORD_TOKEN")
if not token:
    raise RuntimeError("DISCORD_TOKEN is missing")

bot.run(token)
