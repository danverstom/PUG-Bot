from discord import Embed, Colour, User
from discord.ext.commands import Cog, has_role
from discord.ext import tasks
from utils.database import *
from utils.utils import error_embed, success_embed, response_embed
from utils.config import MOD_ROLE, BOT_OUTPUT_CHANNEL, IGN_TRACKER_INTERVAL_HOURS, REGISTER_REQUESTS_CHANNEL
from asyncio import sleep as async_sleep

# Slash commands support
from discord_slash.cog_ext import cog_slash, manage_commands
from utils.config import SLASH_COMMANDS_GUILDS


class UserRegistration(Cog, name="User Registration"):
    """
    This category contains commands related to user registration
    """

    def __init__(self, bot):
        self.bot = bot
        self.bot_channel = self.bot.get_channel(BOT_OUTPUT_CHANNEL)
        self.update_usernames.start()

    def cog_unload(self):
        self.update_usernames.cancel()

    @cog_slash(name="register", description="Registers Minecraft username to Discord."
                                            "  This is required to sign up for PUGs.",
               options=[manage_commands.create_option(name="minecraft_username",
                                                      description="Your current minecraft username",
                                                      option_type=3, required=True)], guild_ids=SLASH_COMMANDS_GUILDS)
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
            condition = player_check(uuid, ctx.author.id)
            if not condition:
                if check_user_requests(ctx.author.id):
                    await error_embed(ctx, "You have already submitted a register request")
                else:
                    request_channel = self.bot.get_channel(REGISTER_REQUESTS_CHANNEL)
                    embed = Embed(title=f"Register Request: {minecraft_username}",
                                  description=f"React below to verify {ctx.author.mention}",
                                  colour=Colour.dark_purple())
                    embed.set_thumbnail(url=f"https://cravatar.eu/helmavatar/{minecraft_username}/128.png")
                    message = await request_channel.send(embed=embed)
                    await message.add_reaction("✅")
                    await message.add_reaction("❌")
                    # TODO: Add check to see if the register request already exists
                    if add_register_request(uuid, ctx.author.id, minecraft_username, message.id):
                        await ctx.send(embed=Embed(title="Registration Pending",
                                                   description=f"Requested to register **{minecraft_username}**"
                                                               f" to {ctx.author.mention}",
                                                   color=Colour.dark_purple()))

                    else:
                        await error_embed(ctx, "There was an error storing your register request. Contact a PUG Dev")
            elif condition == 1:
                await ctx.send(embed=Embed(title="Error ❌",
                                           description=f"**{minecraft_username}** is already registered",
                                           color=Colour.dark_red()))
            else:
                await ctx.send(embed=Embed(title="Error ❌",
                                           description=f"{ctx.author.mention} is already registered",
                                           color=Colour.dark_red()))
        else:
            await ctx.send(embed=Embed(title="Error ❌",
                                       description=f"**{minecraft_username}** does not exist",
                                       color=Colour.dark_red()))

    @Cog.listener()
    async def on_raw_reaction_add(self, payload):
        request = get_register_request(payload.message_id)
        if payload.channel_id == REGISTER_REQUESTS_CHANNEL and bool(request):
            channel = await self.bot.fetch_channel(REGISTER_REQUESTS_CHANNEL)
            message = await channel.fetch_message(payload.message_id)
            server = self.bot.get_guild(payload.guild_id)
            mod_member = server.get_member(payload.user_id)
            player_member = server.get_member(request[1])
            if str(payload.emoji) == "✅" and MOD_ROLE in [role.name for role in mod_member.roles]:
                await message.clear_reactions()
                await message.edit(content=f"✅ {mod_member.name} accepted {player_member.mention}'s request for IGN"
                                           f" **{request[2]}**", embed=None)
                await success_embed(player_member, f"Your IGN request for **{request[2]}** was approved")
                add_player(request[0], request[1], request[2])
                remove_register_request(payload.message_id)
            elif str(payload.emoji) == "❌" and MOD_ROLE in [role.name for role in mod_member.roles]:
                await message.clear_reactions()
                await message.edit(content=f"❌ {mod_member.name} denied {player_member.mention}'s request for IGN"
                                           f" **{request[2]}**", embed=None)
                await player_member.send(embed=Embed(title="Denied IGN Request",
                                                     description=f"Your request for IGN **{request[2]}** was denied.",
                                                     color=Colour.dark_red()))
                remove_register_request(payload.message_id)

    @cog_slash(name="unregister", description="Remove a user from the database",
               options=[manage_commands.create_option(name="discord_tag",
                                                      description="The user's discord @",
                                                      option_type=6, required=True)], guild_ids=SLASH_COMMANDS_GUILDS)
    @has_role(MOD_ROLE)
    async def unregister(self, ctx, input_user: User = None):
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
            return m.author == ctx.author

        response = await self.bot.wait_for('message', check=check)
        if response.content.lower() == "y" or response.content.lower() == "yes":
            delete_player(player.minecraft_id)
            await success_embed(ctx, f"User {user.mention} has been unregistered.")
        else:
            await response_embed(ctx, "Stopped Deletion", f"User {user.mention} will not be deleted from the database.")

    @cog_slash(name="user", description="Get or change information about a user",
               options=[manage_commands.create_option(name="discord_tag",
                                                      description="The user's discord @",
                                                      option_type=6, required=True),
                        manage_commands.create_option(name="action_type",
                                                      description="'get' or 'set'",
                                                      option_type=3, required=False,
                                                      choices=["get", "set"]),
                        manage_commands.create_option(name="variable_name",
                                                      description="Variable to change",
                                                      option_type=3, required=False,
                                                      choices=["username", "discord", "elo", "priority"]),
                        manage_commands.create_option(name="value",
                                                      description="Value to set",
                                                      option_type=3, required=False)],
               guild_ids=SLASH_COMMANDS_GUILDS)
    @has_role(MOD_ROLE)
    async def user(self, ctx, discord_tag: User = None, action_type="get", variable_name=None, value=None):
        """
        Allows a PUG Mod to edit information about a user.
        Usage: user @Tom <get/set> <variable_name> <value>

        Examples:
            user @Tom get                       returns user profile
            user @Tom set elo [elo]             sets user ELO
        """
        user = self.bot.get_user(discord_tag.id)
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
            try:
                player = Player(user.id)
            except PlayerDoesNotExistError:
                await error_embed(ctx, "Player does not exist")
                return
            if variable_name:
                if value:
                    if variable_name == "username":
                        old_username = player.update_minecraft_username()
                        condition = player.change_minecraft_username(value)
                        if not condition:
                            await success_embed(ctx, f"Changed username: {old_username} -> {value}")
                        elif condition == 1:
                            await error_embed(ctx, f"Username {value} is already in the database")
                        else:
                            await error_embed(ctx, f"Username {value} is not a valid username")
                    elif variable_name == "discord":
                        value = value[3:-1]
                        if value.isdigit():
                            user = self.bot.get_user(int(value))
                            if user:
                                if player.change_discord_id(user.id):
                                    await success_embed(ctx, f"Changed discord user: {discord_tag.mention} -> {user.mention}")
                                else:
                                    await error_embed(ctx, f"User {user.mention} is already in the database")
                            else:
                                await error_embed(ctx, "Value must be a User")
                        else:
                            await error_embed(ctx, "Value must be a User")
                    elif variable_name == "elo":
                        old_elo = player.get_elo()
                        if value.isdigit():
                            value = int(value)
                            if player.set_elo(value):
                                await success_embed(ctx, f"Set elo: {old_elo} -> {value}")
                            else:
                                await error_embed(ctx, f"Elo given ({value}) is below Elo floor ({ELO_FLOOR})")
                        else:
                            await error_embed(ctx, "Value must be an int")
                    else:
                        old_priority = player.get_priority()
                        if value.isdigit():
                            value = int(value)
                            if player.set_priority(value):
                                await success_embed(ctx, f"Set priority: {old_priority} -> {value}")
                            else:
                                await error_embed(ctx, f"Priority given ({value}) is negative")
                        else:
                            await error_embed(ctx, "Value must be an int")
                else:
                    await error_embed(ctx, "No value inputted")
            else:
                await error_embed(ctx, "No variable name inputted")
        else:
            await error_embed(ctx, "Invalid action argument. Use 'get' or 'set'")

    @cog_slash(name="elo", description="Returns your or someone else's ELO",
               options=[manage_commands.create_option(name="discord_tag",
                                                      description="The user's discord @",
                                                      option_type=6, required=False)], guild_ids=SLASH_COMMANDS_GUILDS)
    async def elo(self, ctx, user: User = None):
        """
        Allows you to check your (or someone else's) ELO
        """
        if user:
            player_id = user.id
        else:
            player_id = ctx.author.id
        try:
            player = Player(player_id)
        except PlayerDoesNotExistError:
            await error_embed(ctx, "Player does not exist")
            return False
        await response_embed(ctx, f"{player.minecraft_username}'s ELO", str(player.get_elo()))

    @tasks.loop(hours=IGN_TRACKER_INTERVAL_HOURS)
    async def update_usernames(self):
        changes_list = []
        for player in fetch_players_list():
            old_username = player.minecraft_username
            latest_username = player.update_minecraft_username()
            if latest_username != old_username:
                changes_list.append([player, old_username])
            await async_sleep(3)
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
