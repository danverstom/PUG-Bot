import discord
from discord.ext.commands import Bot
from utils.config import bot_token

# Importing files from the commands directory to be initialised
from commands.BaseCommands import BaseCommands
from commands.UserRegistration import UserRegistration

intents = discord.Intents.all()

# Creating the bot object
bot = Bot(command_prefix="-", intents=intents)


@bot.event
async def on_ready():
    print('Logged on as {0}!'.format(bot.user))
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.competing, name="PUG Season 2"))

    # Adding commands to the bot now that its ready
    bot.add_cog(BaseCommands(bot))
    bot.add_cog(UserRegistration(bot))

bot.run(bot_token)
