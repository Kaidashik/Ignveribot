import os
import re
import discord
from discord.ext import commands

# ----------------------------
# CONFIG (edit these)
# ----------------------------
GUILD_ID = 998651148829466745                 # your server ID
REGISTRATION_CHANNEL_ID = 1463756329939374110  # channel where panel will be posted
VERIFIED_ROLE_ID = 1462585050779615355        # role to grant after nickname is set

PANEL_TITLE = "Server Access"
PANEL_DESC = "Click **Register** to set your in-game nickname and unlock the server."

NICKNAME_MIN_LEN = 3
NICKNAME_MAX_LEN = 20

# Allow letters (unicode), digits, spaces, underscore, dash, dot
NICKNAME_REGEX = re.compile(r"^[\w .\-]{3,20}$", re.UNICODE)

# ----------------------------
# BOT SETUP
# ----------------------------
intents = discord.Intents.default()
intents.members = True  # needed to edit nicknames / add roles

bot = commands.Bot(command_prefix="!", intents=intents)


def validate_nickname(nick: str) -> tuple[bool, str]:
    nick = nick.strip()

    if len(nick) < NICKNAME_MIN_LEN or len(nick) > NICKNAME_MAX_LEN:
        return False, f"Nickname must be between {NICKNAME_MIN_LEN} and {NICKNAME_MAX_LEN} characters."

    if not NICKNAME_REGEX.match(nick):
        return False, "Nickname contains unsupported characters. Use letters/numbers/spaces/_-."

    if "@everyone" in nick or "@here" in nick:
        return False, "That nickname is not allowed."

    return True, ""


class NicknameModal(discord.ui.Modal, title="Set your in-game nickname"):
    nickname = discord.ui.TextInput(
        label="In-game nickname",
        placeholder="Type your nickname here",
        min_length=NICKNAME_MIN_LEN,
        max_length=NICKNAME_MAX_LEN,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "This can only be used inside a server.",
                ephemeral=True
            )

        member: discord.Member = interaction.user
        guild: discord.Guild = interaction.guild

        # Optional: lock to a specific guild
        if guild.id != GUILD_ID:
            return await interaction.response.send_message(
                "This registration is not configured for this server.",
                ephemeral=True
            )

        verified_role = guild.get_role(VERIFIED_ROLE_ID)
        if verified_role is None:
            return await interaction.response.send_message(
                "Server error: verified role not found. Admin must check VERIFIED_ROLE_ID.",
                ephemeral=True
            )

        # If already verified, you can allow updates or block
        if verified_role in member.roles:
            return await interaction.response.send_message(
                "You already have access ✅",
                ephemeral=True
            )

        nick = str(self.nickname.value).strip()
        ok, err = validate_nickname(nick)
        if not ok:
            return await interaction.response.send_message(
                f"❌ {err}",
                ephemeral=True
            )

        # Set nickname
        try:
            await member.edit(nick=nick, reason="Completed registration via modal")
        except discord.Forbidden:
            return await interaction.response.send_message(
                "❌ I can't change your nickname.\n"
                "Admin: move my bot role ABOVE members and grant **Manage Nicknames**.",
                ephemeral=True
            )
        except discord.HTTPException:
            return await interaction.response.send_message(
                "❌ Discord rejected that nickname. Please try another.",
                ephemeral=True
            )

        # Give role
        try:
            await member.add_roles(verified_role, reason="Completed registration via modal")
        except discord.Forbidden:
            return await interaction.response.send_message(
                "❌ I can't give roles.\n"
                "Admin: grant **Manage Roles** and move my bot role ABOVE the verified role.",
                ephemeral=True
            )
        except discord.HTTPException:
            return await interaction.response.send_message(
                "❌ Discord error while assigning the role. Try again later.",
                ephemeral=True
            )

        await interaction.response.send_message(
            f"✅ Done! Your server nickname is now **{nick}** and you have access.",
            ephemeral=True
        )


class RegisterView(discord.ui.View):
    def __init__(self):
        # timeout=None makes the view "persistent" (survives restarts if you re-add it in setup_hook)
        super().__init__(timeout=None)

    @discord.ui.button(label="Register", style=discord.ButtonStyle.success, custom_id="register:open_modal")
    async def register(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NicknameModal())


@bot.event
async def setup_hook():
    # Re-register the persistent view on startup (required for buttons to work after reboot)
    bot.add_view(RegisterView())


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")


@bot.command(name="postpanel")
@commands.has_permissions(administrator=True)
async def post_panel(ctx: commands.Context):
    """Posts the registration panel in the configured channel."""
    if not ctx.guild or ctx.guild.id != GUILD_ID:
        return await ctx.reply("This command is not configured for this server.")

    channel = ctx.guild.get_channel(REGISTRATION_CHANNEL_ID)
    if channel is None:
        return await ctx.reply("Registration channel not found. Check REGISTRATION_CHANNEL_ID.")

    embed = discord.Embed(title=PANEL_TITLE, description=PANEL_DESC)
    embed.set_footer(text="If the button doesn't respond, ask an admin to re-run !postpanel.")

    await channel.send(embed=embed, view=RegisterView())
    await ctx.reply("✅ Panel posted.", delete_after=10)


@post_panel.error
async def post_panel_error(ctx: commands.Context, error: Exception):
    if isinstance(error, commands.MissingPermissions):
        await ctx.reply("❌ You need Administrator permission to run this.")
    else:
        await ctx.reply(f"❌ Error: {error}")


# ----------------------------
# RUN
# ----------------------------
token = os.getenv("DISCORD_TOKEN")
if not token:
    raise RuntimeError("Missing DISCORD_TOKEN env var. Set it before running.")

bot.run(token)
