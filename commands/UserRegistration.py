from discord import Embed, Colour, User
from discord.ext.commands import Cog, command, has_role
from mojang.api import MojangAPI
from utils.database import add_player, PlayerDoesNotExistError, Player
from utils.utils import error_embed, success_embed, response_embed
from utils.config import MOD_ROLE


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

    @command()
    @has_role(MOD_ROLE)
    async def user(self, ctx, input_user: User, action_type="", variable_name=None, value=None):
        """
        Allows a PUG Mod to edit information about a user.
        Usage: user @Tom <get/set> <variable_name> <value>

        Examples:
            user @Tom get                       returns user profile
            user @Tom set elo [elo]             sets user ELO
        """
        user = self.bot.get_user(input_user.id)
        if action_type == "get":
            try:
                player = Player(user.id)
            except PlayerDoesNotExistError:
                await error_embed(ctx, "Player does not exist")
                return False
            embed = Embed(title=f"User Profile - {user.name}", color=Colour.dark_purple())
            for key in player.__dict__.keys():
                embed.add_field(name=key, value=getattr(player, key), inline=False)
            await ctx.send(embed=embed)

        elif action_type == "set":
            # TODO: implement set command
            pass
        else:
            await error_embed(ctx, "Invalid action argument. Use 'get' or 'set'")

