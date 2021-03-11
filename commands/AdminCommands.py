from discord.ext.commands import Cog, has_role
from discord import File, Embed, Colour
from utils.utils import get_json_data, error_embed, success_embed, response_embed
import os
import sys
import platform
import subprocess

# Slash commands support
from discord_slash.cog_ext import cog_slash, manage_commands
from utils.config import SLASH_COMMANDS_GUILDS, ADMIN_ROLE, MOD_ROLE


class AdminCommands(Cog, name="Admin Commands"):
    """
    These commands can be used by admins
    """

    def __init__(self, bot, slash, token):
        self.bot = bot
        self.slash = slash
        self.token = token

    @cog_slash(name="removecommands", description="Removes all slash commands from the bot",
               guild_ids=SLASH_COMMANDS_GUILDS)
    async def removecommands(self, ctx):
        if ADMIN_ROLE.lower() not in [role.name.lower() for role in ctx.author.roles]:
            await error_embed(ctx, "You do not have sufficient permissions to do this")
            return
        message = await response_embed(ctx, "Removing commands", "Please wait, this process can take a while")
        await manage_commands.remove_all_commands(self.bot.user.id, self.token, guild_ids=SLASH_COMMANDS_GUILDS)
        await message.delete()
        await success_embed(ctx, "Removed all commands from this bot")

    @cog_slash(name="restart", description="Restarts the bot",
               guild_ids=SLASH_COMMANDS_GUILDS,
               options=[manage_commands.create_option(name="remove_commands",
                                                      option_type=5,
                                                      description="if true, remove commands before restart",
                                                      required=False),
               manage_commands.create_option(name="pull_changes",
                                             option_type=5,
                                             description="if true, pull the latest changes from github",
                                             required=False)])
    async def restart(self, ctx, remove_commands=False, pull_changes=False):
        if ADMIN_ROLE.lower() not in [role.name.lower() for role in ctx.author.roles]:
            await error_embed(ctx, "You do not have sufficient permissions to do this")
            return
        if remove_commands:
            message = await response_embed(ctx, "Removing commands", "Please wait, this process can take a while")
            await manage_commands.remove_all_commands(self.bot.user.id, self.token, guild_ids=SLASH_COMMANDS_GUILDS)
            await message.delete()
            await success_embed(ctx, "Removed all commands from this bot")
        await response_embed(ctx, "Info", "Bot is restarting")
        if pull_changes:
            output = subprocess.check_output("git pull", shell=True)
            await response_embed(ctx, "Update Summary", output.decode("utf8"))
        await self.bot.logout()

        # Checks for operating system
        operating_system = platform.system()
        if operating_system == "Windows":
            os.execv(sys.executable, ['python'] + sys.argv)
        elif operating_system == "Linux":
            os.execv(sys.executable, ['python3'] + sys.argv)
        else:
            await error_embed(ctx, "Bot is not running on Windows or Linux, failed to restart")
        quit()
