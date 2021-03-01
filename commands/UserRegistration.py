from discord.ext.commands import Cog, command
from mojang.api import MojangAPI
from utils.database import add_player


class UserRegistration(Cog, name="User Registration"):
    """
    This category contains commands related to user registration
    """

    def __init__(self, bot):
        self.bot = bot

    @command()
    async def register(self, ctx, minecraft_username):
        """
        Links Minecraft username to Discord
        """
        uuid = MojangAPI.get_uuid(minecraft_username)
        if uuid:
            condition = add_player(uuid, ctx.message.author.id, minecraft_username)
            if not condition:
                await ctx.send("Successfully registered {} to {}".format(minecraft_username, ctx.message.author.mention))
            elif condition == 1:
                await ctx.send("Failed to register {}: {} is already registered".format(minecraft_username,
                                                                                        minecraft_username))
            else:
                await ctx.send("Failed to register {}: {} is already registered".format(minecraft_username,
                                                                                        ctx.message.author.mention))
        else:
            await ctx.send("Failed to register {}: {} does not exist".format(minecraft_username, minecraft_username))
