from discord import Embed, Colour, User
from discord.ext.commands import Cog, has_role
from discord.ext import tasks
from database.Player import Player, PlayerDoesNotExistError, UsernameAlreadyExistsError, UsernameDoesNotExistError, \
    DiscordAlreadyExistsError
from database.database import check_user_requests, add_register_request, get_register_request, \
    remove_register_request, get_all_register_requests, get_sorted_elo
from utils.utils import error_embed, success_embed, response_embed, create_list_pages, has_permissions
from utils.config import MOD_ROLE, BOT_OUTPUT_CHANNEL, IGN_TRACKER_INTERVAL_HOURS, REGISTER_REQUESTS_CHANNEL,\
    ELO_FLOOR, ADMIN_ROLE, PUBLIC_BOT_CHANNEL, UPDATE_NICKNAMES, SEND_JOIN_MESSAGE
from mojang import MojangAPI
from asyncio import sleep as async_sleep
from discord.errors import Forbidden
from discord.utils import get
import re
import logging

# Slash commands support
from discord_slash.cog_ext import cog_slash, manage_commands
from utils.config import SLASH_COMMANDS_GUILDS, BOT_START_MESSAGE


class RegistrationCommands(Cog, name="User Registration"):
    """
    This category contains commands related to user registration
    """

    def __init__(self, bot):
        self.bot = bot
        self.bot_channel = None

    def cog_unload(self):
        self.update_usernames.cancel()

    @Cog.listener()
    async def on_ready(self):
        self.bot_channel = self.bot.get_channel(BOT_OUTPUT_CHANNEL)
        if BOT_START_MESSAGE:
            await success_embed(self.bot_channel, "Bot has started")
        self.update_usernames.start()



    @cog_slash(name="list", description="Lists data",
               options=[manage_commands.create_option(name="data_type",
                                                      description="The object you want to list",
                                                      option_type=3, required=True,
                                                      choices=["players", "register_requests"])],
               guild_ids=SLASH_COMMANDS_GUILDS)
    async def list(self, ctx, data_type):
        if not has_permissions(ctx, MOD_ROLE):
            await ctx.send("You do not have sufficient permissions to perform this command", hidden=True)
            return False
        title = "List"
        info = []
        if data_type == "players":
            players = sorted(Player.fetch_players_list(), key=lambda item: item.minecraft_username)
            title = "Registered Users"
            for player in players:
                player_string = f"**{player.minecraft_username}** ({self.bot.get_user(player.discord_id).mention if self.bot.get_user(player.discord_id) else '<@' + str(player.discord_id) + '> 🚫' })\n"
                for key in player.__dict__.keys():
                    player_string += f"> {key}: `{player.__dict__[key]}`\n"
                info.append(player_string)
        elif data_type == "register_requests":
            title = "IGN Registration Requests"
            requests = sorted(get_all_register_requests(), key=lambda item: item[2])
            for request in requests:
                info.append(f"**{request[2]}** ({self.bot.get_user(request[1]).mention if self.bot.get_user(request[1]) else '<@' + str(request[1]) + '> 🚫'})")
        await create_list_pages(bot=self.bot, ctx=ctx, title=title, info=info,
                                if_empty="There are no registration requests" if data_type == "register_requests" else
                                "There are no registered players", elements_per_page=5)

    @cog_slash(name="register", description="Registers Minecraft username to Discord."
                                            " Required to sign up for PUGs.",
               options=[manage_commands.create_option(name="minecraft_username",
                                                      description="Your current minecraft username",
                                                      option_type=3, required=True)], guild_ids=SLASH_COMMANDS_GUILDS)
    async def register(self, ctx, minecraft_username=""):
        """
        Registers Minecraft username to Discord. Required to sign up for PUGs.
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
            condition = Player.player_check(uuid, ctx.author.id)
            if not condition:
                if check_user_requests(ctx.author.id):
                    await error_embed(ctx, "You have already submitted a register request")
                else:
                    request_channel = self.bot.get_channel(REGISTER_REQUESTS_CHANNEL)
                    embed = Embed(title=f"Register Request: {minecraft_username}",
                                  description=f"React below to verify {ctx.author.mention}",
                                  colour=Colour.dark_purple())
                    embed.set_thumbnail(url=f"https://cravatar.eu/helmavatar/{uuid}/128.png")
                    message = await request_channel.send(embed=embed)
                    await message.add_reaction("✅")
                    await message.add_reaction("❌")
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
    async def on_member_join(self, member):
        if not SEND_JOIN_MESSAGE:
            return
        channel = self.bot.get_channel(PUBLIC_BOT_CHANNEL)
        if Player.exists_discord_id(member.id):
            return
        else:
            try:
                await member.send(f"Welcome {member.mention} to the PUG server, do not forget to use **/register**"
                                  f" in the PUG server.")
                logging.info(f"Sent registration reminder for {member.name} in DMs")
            except Forbidden:
                # This means the bot can't DM the user
                await channel.send(f"Welcome {member.mention} to the PUG server, do not forget to use **/register**.")
                logging.info(f"Sent registration reminder for {member.name} in #{channel.name}")

    @Cog.listener()
    async def on_raw_reaction_add(self, payload):
        request = get_register_request(payload.message_id)
        if payload.channel_id == REGISTER_REQUESTS_CHANNEL and bool(request) and payload.user_id != self.bot.user.id:
            channel = await self.bot.fetch_channel(REGISTER_REQUESTS_CHANNEL)
            message = await channel.fetch_message(payload.message_id)
            server = self.bot.get_guild(payload.guild_id)
            mod_member = server.get_member(payload.user_id)
            player_member = server.get_member(request[1])
            required_role = get(server.roles, name=MOD_ROLE)
            if str(payload.emoji) == "✅" and required_role.position <= mod_member.top_role.position:
                Player.add_player(request[0], request[1])
                remove_register_request(payload.message_id)
                await message.clear_reactions()
                await message.edit(content=f"✅ {mod_member.name} accepted {player_member.mention}'s request for IGN"
                                           f" **{request[2]}**", embed=None)
                try:
                    await success_embed(player_member, f"Your IGN request for **{request[2]}** was approved")
                except Forbidden:
                    # This means the bot can't DM the user
                    await channel.send("This user has PMs off, failed to send DM.")
            elif str(payload.emoji) == "❌" and required_role.position <= mod_member.top_role.position:
                remove_register_request(payload.message_id)
                await message.clear_reactions()
                await message.edit(content=f"❌ {mod_member.name} denied {player_member.mention}'s request for IGN"
                                           f" **{request[2]}**", embed=None)
                try:
                    await player_member.send(embed=Embed(title="Denied IGN Request",
                                                         description=f"Your request for IGN **{request[2]}** was denied.",
                                                         color=Colour.dark_red()))
                except Forbidden:
                    # This means the bot can't DM the user
                    await channel.send("This user has PMs off, failed to send DM.")

    @cog_slash(name="unregister", description="Remove a user from the database",
               options=[manage_commands.create_option(name="user",
                                                      description="The user's discord @",
                                                      option_type=6, required=True)], guild_ids=SLASH_COMMANDS_GUILDS)
    async def unregister(self, ctx, user: User = None):
        if not has_permissions(ctx, MOD_ROLE):
            await ctx.send("You do not have sufficient permissions to perform this command", hidden=True)
            return False
        """
        Allows a PUG Mod to unregister a discord user from the Minecraft account they registered to.
        Usage: unregister <user_mention>

        Example:
            unregister @Ninsanity
        """
        if not user:
            await error_embed(ctx, "Missing Argument <input_user>")
        try:
            player = Player.from_discord_id(user.id)
        except PlayerDoesNotExistError:
            await error_embed(ctx, "Player is not registered in the database.")
            return
        await response_embed(ctx, "Confirm", f"""Are you sure you want to delete {user.mention} from the database?
                                                \nThis action is **permanent** and **irreversible**, and will remove their elo and priority **forever**.
                                                \nReply with yes or no.""")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        response = await self.bot.wait_for('message', check=check)
        if response.content.lower() == "y" or response.content.lower() == "yes":
            player.delete()
            await success_embed(ctx, f"User {user.mention} has been unregistered.")
        else:
            await response_embed(ctx, "Stopped Deletion", f"User {user.mention} will not be deleted from the database.")

    @cog_slash(name="user", description="Get or change information about a user",
               options=[manage_commands.create_option(name="discord_tag",
                                                      description="The user's discord @",
                                                      option_type=6, required=True),
                        manage_commands.create_option(name="action_type",
                                                      description="How you would like to interact with the user's data",
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
    async def user(self, ctx, discord_tag: User = None, action_type="get", variable_name=None, value=None):
        """
        Allows a PUG Mod to edit information about a user.
        Usage: user @Tom <get/set> <variable_name> <value>

        Examples:
            user @Tom get                       returns user profile
            user @Tom set elo [elo]             sets user ELO
        """
        if not has_permissions(ctx, MOD_ROLE):
            await ctx.send("You do not have sufficient permissions to perform this command", hidden=True)
            return False
        user = self.bot.get_user(discord_tag.id)
        if action_type == "get":
            try:
                player = Player.from_discord_id(user.id)
            except PlayerDoesNotExistError:
                await error_embed(ctx, "Player does not exist")
                return
            info = ""
            for key in player.__dict__.keys():
                info += f"**{key}**: {getattr(player, key)}\n"
            embed = Embed(description=info, title=f"User Profile - {user.name}", color=Colour.dark_purple())
            await ctx.send(embed=embed)

        elif action_type == "set":
            try:
                player = Player.from_discord_id(user.id)
            except PlayerDoesNotExistError:
                await error_embed(ctx, "Player does not exist")
                return
            if variable_name:
                if value:
                    if variable_name == "username":
                        old_username = player.update_minecraft_username()
                        try:
                            player.change_minecraft_username(value)
                            await success_embed(ctx, f"Changed {discord_tag.mention}'s username: **{old_username}** -> **{value}**")
                        except UsernameAlreadyExistsError:
                            await error_embed(ctx, f"Username **{value}** is already in the database")
                        except UsernameDoesNotExistError:
                            await error_embed(ctx, f"Username **{value}** is not a valid username")
                    elif variable_name == "discord":
                        value = value[3:-1]
                        if value.isdigit():
                            user = self.bot.get_user(int(value))
                            if user:
                                try:
                                    player.change_discord_id(user.id)
                                    await success_embed(ctx,
                                                        f"Changed discord user: {discord_tag.mention} -> {user.mention}")
                                except DiscordAlreadyExistsError:
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
                                await success_embed(ctx, f"Set {discord_tag.mention}'s elo: **{old_elo}** -> **{value}**")
                            else:
                                await error_embed(ctx, f"Elo given (**{value}**) is below Elo floor (**{ELO_FLOOR}**)")
                        else:
                            await error_embed(ctx, "Value must be an int")
                    else:
                        old_priority = player.get_priority()
                        if value.isdigit():
                            value = int(value)
                            if player.set_priority(value):
                                await success_embed(ctx, f"Set {discord_tag.mention}'s priority: **{old_priority}** -> **{value}**")
                            else:
                                await error_embed(ctx, f"Priority given (**{value}**) is negative")
                        else:
                            await error_embed(ctx, "Value must be an int")
                else:
                    await error_embed(ctx, "No value inputted")
            else:
                await error_embed(ctx, "No variable name inputted")
        else:
            await error_embed(ctx, "Invalid action argument. Use 'get' or 'set'")

    @cog_slash(name="profile", options=[manage_commands.create_option(name="user",
                                                      description="The user's discord @",
                                                      option_type=6, required=False)], guild_ids=SLASH_COMMANDS_GUILDS)
    async def profile(self, ctx, user: User = None):
        """
        Displays a user's profile
        """
        if user:
            if not isinstance(user, int):
                player_id = user.id
            else:
                player_id = user
        else:
            player_id = ctx.author.id
        try:
            player = Player.from_discord_id(player_id)
        except PlayerDoesNotExistError:
            await error_embed(ctx, "Player does not exist")
            return

        #Position in leaderboard
        data = get_sorted_elo()
        count = 1
        for item in data:
            if player:
                if player.minecraft_username == item[0]:
                    leader_pos = count
                    break
            count += 1

        stats = f"**ELO:** {getattr(player, 'elo')}\n**Rank**: #{leader_pos}\n**Discord:** <@{getattr(player, 'discord_id')}>"
        #for key in player.__dict__.keys():
        #    stats += f"**{key}:** {getattr(player, key)}\n"

        embed = Embed(description=stats, color=Colour.dark_purple())
        embed.set_author(name=f"User profile - {getattr(player, 'minecraft_username')}", icon_url=f"https://cravatar.eu/helmavatar/{getattr(player, 'minecraft_id')}/128.png")
        await ctx.send(embed=embed)

    @tasks.loop(hours=IGN_TRACKER_INTERVAL_HOURS)
    async def update_usernames(self):
        server = self.bot_channel.guild
        changes_list = []
        for player in Player.fetch_players_list():
            old_username = player.minecraft_username
            latest_username = player.update_minecraft_username()
            if latest_username != old_username and latest_username is not None:
                changes_list.append([player, old_username])
            await async_sleep(1)
        if len(changes_list) > 0:
            embed = Embed(title="IGNs Updated", color=Colour.dark_purple())
            for change in changes_list:
                player = change[0]
                member = server.get_member(player.discord_id)
                old_username = change[1]
                if not member.nick:
                    member.nick = member.name
                team_list = re.findall(r"^\[(\w{1,4})\]", member.nick)
                alias_list = re.findall(r"\s\((.*)\)$", member.nick)
                new_nick = f"{'[' + team_list[0] + '] ' if team_list else ''}{player.minecraft_username}" + \
                           (f" ({alias_list[0]})" if alias_list else "")
                if UPDATE_NICKNAMES:
                    try:
                        await member.edit(nick=new_nick)
                    except Forbidden:
                        embed_value = f"🔴 Failed to update nickname to `{new_nick}` (Forbidden)"
                    else:
                        embed_value = f"Updated server nickname to `{new_nick}`"
                        try:
                            await success_embed(member, f"PUG server nickname updated to `{new_nick}`")
                            embed_value += " (DM sent)"
                        except Forbidden:
                            embed_value += " (confirmation DM failed to send)"
                else:
                    embed_value = "Nickname updates disabled in config."
                embed.add_field(name=f"{old_username} → {player.minecraft_username}", value=embed_value, inline=False)
            await self.bot_channel.send(embed=embed)

    @cog_slash(guild_ids=SLASH_COMMANDS_GUILDS)
    async def examine_members(self, ctx):
        """Examines the status and checks nicknames for all server members (for debug purposes)"""
        if not has_permissions(ctx, ADMIN_ROLE):
            await ctx.send("You do not have sufficient permissions to perform this command", hidden=True)
            return False
        server = ctx.guild
        registered = []
        unregistered = []
        without_nick = []
        for member in server.members:
            if not member.bot:
                if member.nick is None:
                    without_nick.append(member.mention)
                else:
                    try:
                        player = Player.from_discord_id(member.id)
                    except PlayerDoesNotExistError:
                        unregistered.append(member.mention)
                    else:
                        team_list = re.findall(r"^\[(\w{1,4})\]", member.nick)
                        alias_list = re.findall(r"\s\((.*)\)$", member.nick)
                        new_nick = f"{'[' + team_list[0] + '] ' if team_list else ''}{player.minecraft_username}" + \
                                   (f" ({alias_list[0]})" if alias_list else "")
                        registered.append(f"{member.mention} → `{new_nick}`")
        await create_list_pages(self.bot, ctx, info=registered, title="Registered Users", elements_per_page=20)
        await create_list_pages(self.bot, ctx, info=unregistered, title="Unregistered Users", elements_per_page=20)
        await create_list_pages(self.bot, ctx, info=without_nick, title="Users without nicknames", elements_per_page=20)
