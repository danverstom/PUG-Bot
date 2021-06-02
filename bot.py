import discord
from discord.ext.commands import Bot
from utils.config import bot_token, get_debug_status, SYNC_COMMANDS
from utils.utils import save_json_file, error_embed
from discord_slash import SlashCommand
from discord_slash.utils import manage_commands
from utils.config import SLASH_COMMANDS_GUILDS
import traceback

# Creating the bot object
intents = discord.Intents.all()
bot = Bot(command_prefix="-", intents=intents)
slash = SlashCommand(bot, sync_commands=SYNC_COMMANDS)


# Importing files from the commands directory to be initialised
from commands.BaseCommands import BaseCommands
from commands.RegistrationCommands import RegistrationCommands
from commands.CTFCommands import CTFCommands
from commands.EventCommands import EventCommands
from commands.HelpCommand import HelpCommand
from commands.AdminCommands import AdminCommands
from commands.GameCommands import GameCommands
from commands.StrikeCommands import StrikeCommands
from commands.ReferralCommands import ReferralCommands


# Importing Quart app for web dashboard
from webserver.app import app

# Adding commands to the bot now that its ready
bot.add_cog(BaseCommands(bot))
bot.add_cog(RegistrationCommands(bot))
bot.add_cog(CTFCommands(bot))
bot.add_cog(EventCommands(bot))
bot.add_cog(HelpCommand(bot, slash))
bot.add_cog(AdminCommands(bot, slash, bot_token))
bot.add_cog(GameCommands(bot))
bot.add_cog(StrikeCommands(bot))
bot.add_cog(ReferralCommands(bot))


@bot.event
async def on_ready():
    print('Logged on as {0}!'.format(bot.user))
    save_json_file("utils/command_names.json", [command for command in slash.commands])
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.competing, name="PUG Season 2"))


@bot.event
async def on_slash_command_error(ctx, error):
    print(''.join(traceback.format_exception(etype=type(error), value=error, tb=error.__traceback__)))
    if get_debug_status():
        desc = f"```{''.join(traceback.format_exception(etype=type(error), value=error, tb=error.__traceback__))}```"
        desc += f"_command executed by {ctx.author.mention}_"
        embed = discord.Embed(title=type(error).__name__, description=desc, colour=discord.Colour.red())
        await ctx.send(embed=embed)
    else:
        await error_embed(ctx, f"`{type(error).__name__}: {error}`")



