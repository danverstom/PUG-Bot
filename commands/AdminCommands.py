from discord.ext.commands import Cog, has_role
from discord import File, Embed, Colour
from utils.utils import get_json_data, error_embed, success_embed, response_embed
import os
import sys

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

    @cog_slash(name="update", description="restarts the bot",
               guild_ids=SLASH_COMMANDS_GUILDS,
               options=[manage_commands.create_option(name="remove_commands",
                                                      option_type=5,
                                                      description="whether or not to remove commands before restart",
                                                      required=False)])
    async def update(self, ctx, remove_commands=False):
        if ADMIN_ROLE.lower() not in [role.name.lower() for role in ctx.author.roles]:
            await error_embed(ctx, "You do not have sufficient permissions to do this")
            return
        if remove_commands:
            message = await response_embed(ctx, "Removing commands", "Please wait, this process can take a while")
            await manage_commands.remove_all_commands(self.bot.user.id, self.token, guild_ids=SLASH_COMMANDS_GUILDS)
            await message.delete()
            await success_embed(ctx, "Removed all commands from this bot")
        await ctx.send("Restarting.....")
        os.system("git pull")
        await self.bot.logout()
        print("argv was", sys.argv)
        print("sys.executable was", sys.executable)
        print("restart now")
        os.execv(sys.executable, ['python'] + sys.argv)
