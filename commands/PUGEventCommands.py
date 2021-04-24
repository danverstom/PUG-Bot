from discord.ext.commands import Cog
from discord import File, Embed, Colour
from utils.utils import get_json_data
from difflib import get_close_matches
from utils.utils import error_embed
# Slash commands support
from discord_slash.cog_ext import cog_slash, manage_commands
from utils.config import SLASH_COMMANDS_GUILDS


class PUGEventCommands(Cog, name="PUG Event Commands"):
    """
    This category contains commands related to PUG Events
    """

    def __init__(self, bot):
        self.bot = bot