import discord
from discord.ext.commands import Bot
from utils.config import bot_token
from utils.utils import save_json_file
from discord_slash import SlashCommand
from discord_slash.utils import manage_commands
import atexit
from utils.config import SLASH_COMMANDS_GUILDS

# Creating the bot object
intents = discord.Intents.all()
bot = Bot(command_prefix="-", intents=intents)
slash = SlashCommand(bot, sync_commands=True)


# Importing files from the commands directory to be initialised
from commands.BaseCommands import BaseCommands
from commands.RegistrationCommands import RegistrationCommands
from commands.CTFCommands import CTFCommands
from commands.EventCommands import EventCommands
from commands.HelpCommand import HelpCommand
from commands.AdminCommands import AdminCommands


# Adding commands to the bot now that its ready
bot.add_cog(BaseCommands(bot))
bot.add_cog(RegistrationCommands(bot))
bot.add_cog(CTFCommands(bot))
bot.add_cog(EventCommands(bot))
bot.add_cog(HelpCommand(bot, slash))
bot.add_cog(AdminCommands(bot, slash, bot_token))


@bot.event
async def on_ready():
    print('Logged on as {0}!'.format(bot.user))
    save_json_file("utils/command_names.json", [command for command in slash.commands])
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.competing, name="PUG Season 2"))


bot.run(bot_token)
