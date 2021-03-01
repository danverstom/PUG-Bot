from discord import Embed, Colour
from discord.ext.commands import Cog, command
from mojang.api import MojangAPI
from utils.database import add_player, PlayerDoesNotExistError, Player


class UserRegistration(Cog, name="User Registration"):
    """
    This category contains commands related to user registration
    """

    def __init__(self, bot):
        self.bot = bot

    @command()
    async def register(self, ctx, minecraft_username=""):
        """
        Links Minecraft username to Discord.  This is required to sign up for PUGs.
        """
        if not minecraft_username:
            embed = Embed(title="Error ❌", description="Missing argument <minecraft_username>",
                          color=Colour.dark_red())
            embed.add_field(name="Example", value="-register Ninsanity")
            await ctx.send(embed=embed)
            return

        uuid = MojangAPI.get_uuid(minecraft_username)
        if uuid:
            condition = add_player(uuid, ctx.message.author.id, minecraft_username)
            if not condition:
                await ctx.send(embed=Embed(title="Success ✅",
                                           description=f"Successfully registered **{minecraft_username}** to {ctx.message.author.mention}",
                                           color=Colour.green()))
            elif condition == 1:
                await ctx.send(embed=Embed(title="Error ❌",
                                           description=f"**{minecraft_username}** is already registered",
                                           color=Colour.dark_red()))
            else:
                await ctx.send(embed=Embed(title="Error ❌",
                                           description=f"{ctx.message.author.mention} is already registered",
                                           color=Colour.dark_red()))
        else:
            await ctx.send(embed=Embed(title="Error ❌",
                                       description=f"**{minecraft_username}** does not exist",
                                       color=Colour.dark_red()))

