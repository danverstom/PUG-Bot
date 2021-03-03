from discord.ext.commands import Cog
from discord import File, Embed, Colour
from utils.ctf_stats import get_server_games, CTFGame
from utils.utils import response_embed, create_list_pages, get_json_data
from random import choice
from json import load

# Slash commands support
from discord_slash.cog_ext import cog_slash, manage_commands
from utils.config import SLASH_COMMANDS_GUILDS


class HelpCommand(Cog, name="Help Command"):
    """
    This category contains the help command
    """

    def __init__(self, bot, slash):
        self.bot = bot
        self.slash = slash

    @cog_slash(name="help", description="Help command", guild_ids=SLASH_COMMANDS_GUILDS, options=[
        manage_commands.create_option(name="command", description="Help regarding a specific command", option_type=3,
                                      choices=list(get_json_data("utils/command_names.json")), required=False)
    ])
    async def help(self, ctx, command_name=None):
        if command_name:
            commands = {command_name: self.slash.commands[command_name]}
        else:
            commands = self.slash.commands
        embed = Embed(title="Help", colour=Colour.dark_purple())
        for command in commands:
            options = commands[command].options if len(commands[command].options) > 0 else False
            guilds = ', '.join([self.bot.get_guild(guild_id).name for guild_id in commands[command].allowed_guild_ids])
            if options and command_name:
                options_string = ""
                for option in options:
                    options_string += f"\t{option['name']} {'[REQUIRED]' if option['required'] else ''}\n" \
                                      f"\t\t*{option['description']}*\n"
                options_string = options_string[:-1]
                options_formatted = f"\n{options_string}\n\nServers: {guilds}"
            else:
                options_formatted = ''
            '''
            print(f"Name: {command}\n"
                  f"Description: {commands[command].description}\n"
                  f"{options_formatted}"
                  f"Guilds: {[bot.get_guild(guild_id).name for guild_id in commands[command].allowed_guild_ids]}")
            '''
            field_value = f"{commands[command].description}\n{options_formatted}"
            embed.add_field(name=f"/{command}", value=field_value)
        await ctx.send(embed=embed)
