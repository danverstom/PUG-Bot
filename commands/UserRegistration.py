from discord import Embed, Colour, User, Member
from discord.ext.commands import Cog, command, has_role
from discord.ext import tasks
from mojang.api import MojangAPI
from utils.database import add_player, delete_player, PlayerDoesNotExistError, Player, fetch_players_list
from utils.utils import error_embed, success_embed, response_embed
from utils.config import MOD_ROLE, BOT_OUTPUT_CHANNEL, IGN_TRACKER_INTERVAL_HOURS


class UserRegistration(Cog, name="User Registration"):
    """
    This category contains commands related to user registration
    """

    def __init__(self, bot):
        self.bot = bot
        self.bot_channel = self.bot.get_channel(BOT_OUTPUT_CHANNEL)
        self.update_usernames.start()

    @command()
    async def register(self, ctx, minecraft_username=""):
        """
        Registers Minecraft username to Discord.  This is required to sign up for PUGs.
        Usage: register <minecraft_username>

        Example:
            register Ninsanity
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
    async def unregister(self, ctx, input_user: User=None):
        """
        Allows a PUG Mod to unregister a discord user from the Minecraft account they registered to.
        Usage: unregister <user_mention>

        Example:
            unregister @Ninsanity
        """
        if not input_user:
            await error_embed(ctx, "Missing Argument <input_user>")
        user = self.bot.get_user(input_user.id)
        try:
            player = Player(user.id)
        except PlayerDoesNotExistError:
            await error_embed(ctx, "Player is not registered in the database.")
            return
        await response_embed(ctx, "Confirm", f"""Are you sure you want to delete {user.mention} from the database?
                                                \nThis action is permanent, and will remove their elo and priority.
                                                \nReply with yes or no.""")

        def check(m):
            return m.author == ctx.message.author

        response = await self.bot.wait_for('message', check=check)
        if response.content == "y" or response.content == "yes":
            delete_player(player.minecraft_id)
            await success_embed(ctx, f"User {user.mention} has been unregistered.")
        else:
            await response_embed(ctx, "Stopped Deletion", f"User {user.mention} will not be deleted from the database.")

    @command()
    @has_role(MOD_ROLE)
    async def user(self, ctx, input_user: User = None, action_type="get", variable_name=None, value=None):
        """
        Allows a PUG Mod to edit information about a user.
        Usage: user @Tom <get/set> <variable_name> <value>

        Examples:
            user @Tom get                       returns user profile
            user @Tom set elo [elo]             sets user ELO
        """
        if not input_user:
            await error_embed(ctx, "Missing Argument <input_user>")
            return
        user = self.bot.get_user(input_user.id)
        if action_type == "get":
            try:
                player = Player(user.id)
            except PlayerDoesNotExistError:
                await error_embed(ctx, "Player does not exist")
                return
            embed = Embed(title=f"User Profile - {user.name}", color=Colour.dark_purple())
            for key in player.__dict__.keys():
                embed.add_field(name=key, value=getattr(player, key), inline=False)
            await ctx.send(embed=embed)

        elif action_type == "set":
            # TODO: implement set command
            pass
        else:
            await error_embed(ctx, "Invalid action argument. Use 'get' or 'set'")

    @command()
    async def elo(self, ctx, member: Member = None):
        """
        Allows you to check your (or someone else's) ELO
        """
        if member:
            player_id = member.id
        else:
            player_id = ctx.message.author.id
        try:
            player = Player(player_id)
        except PlayerDoesNotExistError:
            await error_embed(ctx, "Player does not exist")
            return False
        await response_embed(ctx, f"{player.minecraft_username}'s ELO", player.get_elo())

    @tasks.loop(hours=IGN_TRACKER_INTERVAL_HOURS)
    async def update_usernames(self):
        changes_list = []
        for player in fetch_players_list():
            old_username = player.minecraft_username
            latest_username = player.update_minecraft_username()
            if latest_username != old_username:
                changes_list.append([player, old_username])
        if len(changes_list) == 0:
            await self.bot_channel.send(embed=Embed(title="IGN Tracker",
                                                    description=f"No IGNs were updated in the last"
                                                                f" {IGN_TRACKER_INTERVAL_HOURS} hours",
                                                    color=Colour.dark_purple()))
        else:
            embed = Embed(title="IGNs Updated", color=Colour.dark_purple())
            for change in changes_list:
                player = change[0]
                user = self.bot.get_user(player.discord_id)
                old_username = change[1]
                embed.add_field(name=f"{old_username} → {player.minecraft_username}", value=user.mention, inline=False)
            await self.bot_channel.send(embed=embed)
