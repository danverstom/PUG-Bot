from discord.ext.commands import Cog
from discord import File, Embed, Colour
from utils.utils import get_json_data
from difflib import get_close_matches
from utils.utils import error_embed, create_list_pages
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
        manage_commands.create_option(name="command_name", description="Help regarding a specific command", option_type=3,
                                      required=False)
    ])
    async def help(self, ctx, command_name=None):
        print("Help command used")
        info_list = []
        if command_name:
            commands = None
            try:
                commands = {command_name: self.slash.commands[command_name]}
            except KeyError:
                matches = get_close_matches(command_name, self.slash.commands)
                return await error_embed(ctx, f"Command not found, did you mean `{', '.join(matches)}`?")
        else:
            commands = self.slash.commands
        info = ""
        for command in commands:
            options = commands[command].options if len(commands[command].options) > 0 else False
            guilds = ', '.join([self.bot.get_guild(guild_id).name for guild_id in commands[command].allowed_guild_ids])
            if options and command_name:
                options_string = ""
                for option in options:
                    choices = ""
                    if option["choices"]:
                        choices = f"\n> {', '.join('`' + c['name'] + '`' for c in option['choices'])}"
                    options_string += f"`{option['name']}` {'[REQUIRED]' if option['required'] else ''}\n" \
                                      f"> *{option['description']}*{choices}\n"
                options_string = options_string[:-1]
                info_list.append(f"**/{command}**\n{commands[command].description}\n\n{options_string}\n\n*Servers: {guilds}*")
            else:
                info_list.append(f"**/{command}** - {commands[command].description}\n")

        await create_list_pages(self.bot, ctx, "Help", sorted(info_list), elements_per_page=15, sep="")
