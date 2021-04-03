from discord import Embed, Colour
import re
from discord.channel import TextChannel
from discord.ext import tasks
from discord.ext.commands import Cog
from discord.utils import get
from discord_slash.cog_ext import cog_slash, cog_subcommand
from discord_slash.utils import manage_commands as mc

from utils.config import SLASH_COMMANDS_GUILDS, MOD_ROLE, SIGNUPS_TRACKER_INTERVAL_SECONDS, SIGNED_ROLE_NAME, \
    BOT_OUTPUT_CHANNEL, ADMIN_ROLE, GENERAL_CHAT, TIMEZONE
from utils.event_util import get_event_time, check_if_cancel, announce_event, reaction_changes, save_signups, \
    priority_rng_signups, get_embed_time_string, generate_signups_embed
from utils.utils import response_embed, error_embed, success_embed, has_permissions
from database.Event import Event, EventDoesNotExistError
from database.Signup import Signup
from database.Player import Player, PlayerDoesNotExistError
from asyncio import TimeoutError
from random import shuffle
import logging
from datetime import datetime, timedelta
from pytz import timezone


class EventCommands(Cog, name="Event Commands"):
    """
    This category contains event commands that can be used by pug mods+
    """

    def __init__(self, bot):
        self.bot = bot
        self.events = Event.fetch_active_events_dict()
        self.signups = dict()
        self.bot_channel = None
        for event_id in self.events.keys():
            self.signups[event_id] = Signup.fetch_signups_list(event_id)

    def cog_unload(self):
        self.check_signups.cancel()

    @Cog.listener()
    async def on_ready(self):
        self.bot_channel = self.bot.get_channel(BOT_OUTPUT_CHANNEL)
        self.check_signups.start()

    @cog_slash(name="event", description="Creates an event.",
               options=[mc.create_option(name="title",
                                         description="The title of the event",
                                         option_type=3, required=True),
                        mc.create_option(name="announcement_channel",
                                         description="Channel to announce the event",
                                         option_type=7, required=True),
                        mc.create_option(name="mention_role",
                                         description="Role to mention when event is announced.  Use everyone for "
                                                     "@everyone and None to not mention anyone",
                                         option_type=3, required=True),
                        mc.create_option(name="signup_channel",
                                         description="Channel to list the signups of the event",
                                         option_type=7, required=True),
                        mc.create_option(name="signup_role",
                                         description="Role to give users that signed up",
                                         option_type=8, required=True),
                        mc.create_option(name="event_time",
                                         description="Time (in EST) of the event.",
                                         option_type=3, required=True),
                        mc.create_option(name="event_date",
                                         description="Date of the event.  Must be in YYYY-MM-DD format",
                                         option_type=3, required=False),
                        mc.create_option(name="signup_deadline",
                                         description="Amount of time (in minutes) before the event for signup "
                                                     "deadline.  Default is 20 minutes",
                                         option_type=4, required=False)],
               guild_ids=SLASH_COMMANDS_GUILDS)
    async def event(self, ctx, title, announcement_channel, mention_role, signup_channel, signup_role, event_time,
                    event_date="", signup_deadline=20):
        if not has_permissions(ctx, MOD_ROLE):
            await ctx.send("You do not have sufficient permissions to perform this command", hidden=True)
            return False
        if not isinstance(announcement_channel, TextChannel):
            await error_embed(ctx, f"Announcement channel {announcement_channel.mention} is not a text channel")
            return

        if not isinstance(signup_channel, TextChannel):
            await error_embed(ctx, f"Signups list channel {signup_channel.mention} is not a text channel")
            return

        if mention_role.lower() == "everyone":
            mention_role = "@everyone"
        elif mention_role.lower() == "none":
            mention_role = "None"
        else:
            mention_roles = [role for role in ctx.guild.roles if role.mention == mention_role]
            if mention_roles:
                mention_role = mention_roles[0].mention
            else:
                await error_embed(ctx, f"Given mention role {mention_role} is not a valid role")
                return

        event_time_package = await get_event_time(ctx, event_time, event_date, signup_deadline)
        if not event_time_package:
            return

        def check(m):
            return m.author == ctx.author

        embed = Embed(title="Event Creation", color=Colour.dark_purple())
        embed.add_field(name="Description:", value="Enter the description of the event")
        embed.set_footer(text="Type \"cancel\" to cancel the event")
        message = await ctx.send(embed=embed)
        response = await self.bot.wait_for("message", check=check)
        if await check_if_cancel(ctx, response):
            return
        description = response.content
        await message.delete()
        await response.delete()

        embed_description = f"**Title:** {title}\n**Time:** {event_time_package[0][1]}\n**Signup Deadline:** " \
                            f"{event_time_package[1][1]}\n**Description:**\n{description}\n**Announcement Channel:** " \
                            f"{announcement_channel.mention}\n**Mention Role:**: {mention_role}\n**Signups List " \
                            f"Channel:** {signup_channel.mention}\n**Signup Role:** {signup_role.mention}"
        message = await ctx.send(embed=Embed(title="Is everything correct? (y/n):", description=embed_description,
                                             color=Colour.dark_purple()))
        response = await self.bot.wait_for("message", check=check)
        is_correct = response.content.lower() == "y" or response.content.lower() == "yes"
        await message.delete()
        await response.delete()
        if not is_correct:
            await ctx.send(embed=Embed(description="❌ Event Creation Cancelled", color=Colour.dark_red()))
            return
        await response_embed(ctx, "Confirmed", "✅ Creating event")
        event_message_ids = await announce_event(title, description, announcement_channel, signup_channel,
                                                 mention_role, event_time_package[0][1], event_time_package[1][1])

        new_event = Event.add_event(event_message_ids[0], title, description, event_time_package[0][0].isoformat(),
                                    datetime.now(timezone(TIMEZONE)).isoformat(), ctx.author.id, ctx.guild.id,
                                    announcement_channel.id, signup_channel.id, event_message_ids[1], signup_role.id,
                                    event_time_package[1][0].isoformat())
        self.events[event_message_ids[0]] = new_event
        self.signups[event_message_ids[0]] = []

    @tasks.loop(seconds=SIGNUPS_TRACKER_INTERVAL_SECONDS)
    async def check_signups(self):
        for event in list(self.events.values()):
            event.update()
            # print(f"Event: \n{event.title} Active: {event.is_active}\nTime: {event.time_est}\nDeadline: {event.signup_deadline}")
            if datetime.now(timezone(TIMEZONE)) >= datetime.fromisoformat(event.time_est) + timedelta(days=1):
                event.set_is_active(False)
                await success_embed(self.bot.get_channel(event.signup_channel),
                                    f"Set event {event.event_id} / {event.title} to **inactive**")
                message = await self.bot.get_channel(event.announcement_channel).fetch_message(event.event_id)
                embed = message.embeds[0]
                embed.description = "This event is no longer active."
                await message.edit(embed=embed)
                await message.clear_reactions()
            elif not event.is_signups_active:
                continue
            elif datetime.now(timezone(TIMEZONE)) >= datetime.fromisoformat(event.signup_deadline):
                event.set_is_signup_active(False)
                signups = self.signups.setdefault(event.event_id)
                if not signups:
                    signups = Signup.fetch_signups_list(event.event_id)
                signups = list(filter(lambda sign: sign.can_play, signups))
                if signups:
                    await self.bot.get_channel(event.signup_channel).send(embed=generate_signups_embed(self.bot,
                                                                                                       signups, event))
                else:
                    await error_embed(self.bot.get_channel(event.signup_channel), "No signups on signup deadline :(\n"
                                                                                  f"{event.title}")
                continue

            can_play_users = []
            is_muted_users = []
            can_sub_users = []
            announcement_channel = self.bot.get_channel(event.announcement_channel)
            announcement_message = await announcement_channel.fetch_message(event.event_id)
            signup_channel = self.bot.get_channel(event.signup_channel)
            signup_message = await signup_channel.fetch_message(event.signup_message)
            reactions = announcement_message.reactions
            signups = self.signups[event.event_id]

            for reaction in reactions:
                if reaction.emoji == "✅":
                    can_play_users = [user.id for user in await reaction.users().flatten() if
                                      user.id != self.bot.user.id]
                elif reaction.emoji == "🔇":
                    is_muted_users = [user.id for user in await reaction.users().flatten() if
                                      user.id != self.bot.user.id]
                elif reaction.emoji == "🛗":
                    can_sub_users = [user.id for user in await reaction.users().flatten() if
                                     user.id != self.bot.user.id]

            [signups, change] = reaction_changes(signups, can_play_users, is_muted_users, can_sub_users, event.event_id)
            if change:
                logging.info(f"{event.title}: Reaction change detected")
                save_signups(self.signups[event.event_id], signups)
                logging.info(f"{event.title}: Signups saved")
                self.signups[event.event_id] = signups
                can_play = [user for user in signups if user.can_play]
                can_sub = [user for user in signups if user.can_sub]
                guild = self.bot.get_guild(event.guild_id)
                signup_role = guild.get_role(event.signup_role)
                for member in signup_role.members:
                    if member.id not in can_play_users:
                        await member.remove_roles(signup_role)
                        logging.info(f"{event.title}: Removed role {signup_role.name} from {member}")
                reaction_member_ids = [member.id for member in signup_role.members]
                for user_id in can_play_users:
                    if user_id not in reaction_member_ids:
                        member = guild.get_member(user_id)
                        await member.add_roles(signup_role)
                        logging.info(f"{event.title}: Allocated role {signup_role.name} to {member}")
                embed = signup_message.embeds[0]
                if can_play:
                    value = [f"{index + 1}: <@{user.user_id}> {'🔇' if user.is_muted else ''}"
                             for index, user in enumerate(can_play)]
                    embed.set_field_at(index=0, name=f"✅ Players: {len(can_play)}", value="\n".join(value),
                                       inline=False)
                    logging.info(f"{event.title}: Generated new can_play field")
                else:
                    embed.set_field_at(index=0, name=f"✅ Players: 0", value="No one :(", inline=False)
                if can_sub:
                    value = [f"{index + 1}: <@{user.user_id}> {'🔇' if user.is_muted else ''}"
                             for index, user in enumerate(can_sub)]
                    embed.set_field_at(index=1, name=f"🛗 Subs: {len(can_sub)}", value="\n".join(value), inline=False)
                    logging.info(f"{event.title}: Generated new can_sub field")
                else:
                    embed.set_field_at(index=1, name=f"🛗 Subs: 0", value="No one :(", inline=False)
                await signup_message.edit(embed=embed)
                logging.info(f"{event.title}: Finished editing signup message")

            if not event.is_active:
                del self.events[event.event_id]
                del self.signups[event.event_id]

    @cog_slash(name="removeroles", options=[mc.create_option(name="roles",
                                                             description="Tag roles to remove from all members",
                                                             option_type=3, required=True)],
               guild_ids=SLASH_COMMANDS_GUILDS)
    async def removeroles(self, ctx, *args):
        """Remove multiple roles"""
        if not has_permissions(ctx, MOD_ROLE):
            await ctx.send("You do not have sufficient permissions to perform this command", hidden=True)
            return False
        counter = {}
        roles = []
        total_to_remove = 0
        total_removed = 0
        expr = "\<(.*?)\>"  # Match between <>

        for role_id in re.findall(expr, args[0]):
            role_id = role_id.strip(" <@&!>")
            role = ctx.guild.get_role(int(role_id))
            if role:
                roles.append(role)
                counter[role.name] = len(role.members)
                total_to_remove += len(role.members)

        removing_embed = Embed(title="Removing roles", colour=Colour.dark_purple())
        removing_embed.description = f"Progress: ({total_removed}/{total_to_remove})"

        removing_msg = await ctx.send(embed=removing_embed)

        for role in roles:
            for member in role.members:
                await member.remove_roles(role)
                total_removed += 1
                if total_removed % 5 == 0:
                    removing_embed.description = f"Progress: ({total_removed}/{total_to_remove})"
                    await removing_msg.edit(embed=removing_embed)

        removing_embed.description = f"Progress: ({total_removed}/{total_to_remove})"
        await removing_msg.edit(embed=removing_embed)

        stats = ""
        for roles in list(counter.keys()):
            stats += "{} `{}` roles were removed\n".format(counter[roles], roles)
        if stats:
            return await success_embed(ctx, stats)
        await response_embed(ctx, "No roles removed", "Check your usage")

    @cog_slash(options=[mc.create_option(name="event_id",
                                         description="The message ID of the event announcement",
                                         option_type=3, required=True)],
               guild_ids=SLASH_COMMANDS_GUILDS)
    async def getsignups(self, ctx, event_id):
        """Gets a list of discord tags who are signed up to an event"""
        if not has_permissions(ctx, MOD_ROLE):
            await ctx.send("You do not have sufficient permissions to perform this command", hidden=True)
            return False
        try:
            event_id = int(event_id)
        except ValueError:
            await error_embed(ctx, "Please enter an integer")
            return
        signups = Signup.fetch_signups_list(event_id)
        try:
            event = Event.from_event_id(event_id)
        except EventDoesNotExistError:
            await error_embed(ctx, "This event does not exist")
            return False
        if signups:
            embed = generate_signups_embed(self.bot, signups, event)
            await ctx.send(embed=embed)
        else:
            await error_embed(ctx, "There are no signups for this event")

    @cog_slash(options=[mc.create_option(name="event_id",
                                         description="The message ID of the event announcement",
                                         option_type=3, required=True),
                        mc.create_option(name="size",
                                         description="The maximum players to include in the RNG list. Default 22",
                                         option_type=4, required=False),
                        mc.create_option(name="priority_role",
                                         description="A role to prioritise over other roles",
                                         option_type=8, required=False),
                        mc.create_option(name="results_channel",
                                         description="The channel to send the RNG results",
                                         option_type=7, required=False),
                        mc.create_option(name="do_priority",
                                         description="Whether to process priority",
                                         option_type=5, required=False)
                        ], guild_ids=SLASH_COMMANDS_GUILDS)
    async def rngsignups(self, ctx, event_id, size=22, priority_role=None, results_channel=None, do_priority=True):
        """Randomises signups for an event"""
        if not has_permissions(ctx, MOD_ROLE):
            await ctx.send("You do not have sufficient permissions to perform this command", hidden=True)
            return False
        try:
            event_id = int(event_id)
        except ValueError:
            await error_embed(ctx, "Please enter an integer for the event ID. This is the message ID of the event "
                                   "announcement.")
            return
        signups = self.signups.setdefault(event_id)
        results_embed = Embed(title="RNG Signups - Results", colour=Colour.green())
        if not signups:
            signups = Signup.fetch_signups_list(event_id)
        signups = list(filter(lambda signup: signup.can_play, signups))
        shuffle(signups)
        if do_priority:
            # key is player.priority if player exists else its 0
            signups = sorted(signups, key=lambda signup: Player.from_discord_id(signup.user_id)
                             .priority if Player.exists_discord_id(signup.user_id) else -1, reverse=True)
            results_embed.description = "Here are the results - these take into account priority, for which you must" \
                                        " be registered. In order to register, use the `/register` command"
        else:
            results_embed.description = f"Here are the results - these do not take into account priority, as" \
                                        f" priority is reserved for PUGs and requires players to be registered."
        if priority_role:
            signups = sorted(signups, key=lambda signup: 1 if priority_role in ctx.guild.get_member(signup.user_id)
                             .roles else 0, reverse=True)
        selected_players = signups[:size]
        benched_players = signups[size:]

        if selected_players:
            results_embed.add_field(name=f"Playing ({len(selected_players)})", value='\n'.join(
                [self.bot.get_user(signup.user_id).mention + ('🔇' if signup.is_muted else '') +
                 ("" if Player.exists_discord_id(signup.user_id) else " (Unregistered)") for signup in
                 selected_players]))
            if do_priority:
                for signup in selected_players:
                    player = Player.exists_discord_id(signup.user_id)
                    if player:
                        player.change_priority(-1)
        if benched_players:
            results_embed.add_field(name=f"Not Playing ({len(benched_players)})", value='\n'.join(
                [self.bot.get_user(signup.user_id).mention + ('🔇' if signup.is_muted else '') +
                 ("" if Player.exists_discord_id(signup.user_id) else " (Unregistered)") for signup in
                 benched_players]))
            if do_priority:
                for signup in benched_players:
                    player = Player.exists_discord_id(signup.user_id)
                    if player:
                        player.change_priority(1)

        if not results_channel:
            await ctx.send(content=f"{get(ctx.guild.roles, name=SIGNED_ROLE_NAME).mention} RNG results:",
                           embed=results_embed)
        else:
            await results_channel.send(content=f"{get(ctx.guild.roles, name=SIGNED_ROLE_NAME).mention} RNG results:",
                                       embed=results_embed)
            await success_embed(ctx, f"Sent results embed to {results_channel}")

        tag_str = ""
        for signup in selected_players:
            user = self.bot.get_user(signup.user_id)
            tag_str += f"@{user} \n"
        await self.bot_channel.send(f"{ctx.author.mention} here is a list of tags to make the setroles process easy."
                                    f"\n```{tag_str}```")

    @cog_slash(guild_ids=SLASH_COMMANDS_GUILDS)
    async def setroles(self, ctx):
        """
        Use this command to set many roles, quickly.
        """
        if not has_permissions(ctx, MOD_ROLE):
            await ctx.send("You do not have sufficient permissions to perform this command", hidden=True)
            return False

        def check(m):
            return m.author == ctx.author

        roles_dict = {}
        while True:
            info_embed = Embed(title="/setroles - Enter information", colour=Colour.dark_purple())
            info_embed.description = "Please enter a message tagging the role and all the members who you would like " \
                                     "to assign it to."
            info_embed.set_footer(text='"done/finished/yes/y" to continue\n"no/cancel/n/stop" to cancel')

            for role in roles_dict:
                users_string = f"{role.mention}\n"
                for user in roles_dict[role]:
                    users_string += f"{user.mention}\n"
                info_embed.add_field(name=f"{role.name} ({len(roles_dict[role])})", value=users_string)

            info_message = await ctx.send(embed=info_embed)

            response = await self.bot.wait_for("message", check=check)
            if response.content.lower() in ["done", "finished", "yes", "y"]:
                if len(roles_dict.keys()) > 0:
                    await response.delete()
                    await info_message.delete()
                    total_roles_count = 0
                    embed = Embed(title="Roles Summary", description="Please review the roles you are about to set\n\n"
                                                                     "*this message has a timeout of 5 minutes*",
                                  colour=Colour.dark_purple())
                    embed.set_footer(text=f"✅ to set roles\n❌ to cancel")
                    for role in roles_dict:
                        users_string = f"{role.mention}\n"
                        for user in roles_dict[role]:
                            users_string += f"{user.mention}\n"
                        total_roles_count += len(roles_dict[role])
                        embed.add_field(name=f"{role.name} ({len(roles_dict[role])})", value=users_string)
                    embed.description += f"\n*{total_roles_count} members in total*"
                    message = await ctx.send(embed=embed)
                    await message.add_reaction("✅")
                    await message.add_reaction("❌")

                    def check_reaction(r, u):
                        return r.message.id == message.id and u == ctx.author and str(r.emoji) in ["✅", "❌"]

                    set_roles = False
                    while True:
                        try:
                            reaction, user = await self.bot.wait_for("reaction_add", timeout=300, check=check_reaction)
                            if str(reaction.emoji) == "✅":
                                await message.clear_reactions()
                                embed.set_footer(text=Embed.Empty)
                                embed.description = Embed.Empty
                                await message.edit(embed=embed)
                                set_roles = True
                                break
                            elif str(reaction.emoji) == "❌":
                                raise TimeoutError
                            else:
                                await message.remove_reaction(reaction, user)
                        except TimeoutError:
                            await message.edit(content="Message Expired", embed=None)
                            await message.clear_reactions()
                            break
                    if set_roles:
                        roles_embed = Embed(title="Setting Roles", colour=Colour.green())
                        roles_assigned = 0
                        roles_msg = await ctx.send(embed=roles_embed)
                        for role in roles_dict:
                            users_string = f"{role.mention}\n"
                            for member in roles_dict[role]:
                                users_string += f"{member.mention}\n"
                                await member.add_roles(role, reason=f"role added by {ctx.author.name} with setroles"
                                                                    f" command")
                                roles_assigned += 1
                                if roles_assigned % 5 == 0:
                                    roles_embed.description = f"Progress: {roles_assigned}/{total_roles_count}"
                                    await roles_msg.edit(embed=roles_embed)
                            roles_embed.add_field(name=f"{role.name} ({len(roles_dict[role])})", value=users_string)
                            await roles_msg.edit(embed=roles_embed)
                        roles_embed.title = "Roles Set"
                        roles_embed.description = f"Progress: Done"
                        await roles_msg.edit(embed=roles_embed)
                        await message.delete()
                    return
                else:
                    await error_embed(ctx, "You didn't input anything, cancelled setroles command")
                    return
            elif response.content.lower() in ["no", "cancel", "n", "stop"]:
                await info_message.delete()
                await response.delete()
                await ctx.send(embed=Embed(title="Cancelled", description="You cancelled the setroles command",
                                           colour=Colour.dark_purple()))
                return
            else:
                members = response.mentions
                if len(members) > 0:
                    if len(response.role_mentions) == 1:
                        role = response.role_mentions[0]
                        server = ctx.guild
                        bot_member = server.get_member(self.bot.user.id)

                        if bot_member.top_role.position <= role.position:
                            await error_embed(ctx, "This role is too high to be set by the bot. Please enter a "
                                                   "different role.")
                        elif ctx.author.top_role.position <= role.position:
                            await error_embed(ctx, "You cannot give others this role")
                        else:
                            roles_dict[role] = members
                    else:
                        await error_embed(ctx, "You can only mention one role at a time")
                else:
                    await error_embed(ctx, "You did not mention any members")
            await info_message.delete()

    @cog_slash(guild_ids=SLASH_COMMANDS_GUILDS,
               options=[mc.create_option(name="event_id",
                                         description="The message ID of the event announcement",
                                         option_type=3, required=True),
                        mc.create_option(name="minutes",
                                         description="The amount of minutes to postpone by",
                                         option_type=4, required=True),
                        mc.create_option(name="hours",
                                         description="The amount of hours to postpone by",
                                         option_type=4, required=False),
                        mc.create_option(name="days",
                                         description="The amount of days to postpone by",
                                         option_type=4, required=False)
                        ])
    async def postpone(self, ctx, event_id, minutes, hours=0, days=0):
        """Postpones an event"""
        if not has_permissions(ctx, MOD_ROLE):
            await ctx.send("You do not have sufficient permissions to perform this command", hidden=True)
            return False
        try:
            event_id = int(event_id)
        except ValueError:
            await error_embed(ctx, "Please enter an integer for the event ID. This is the message ID of the event "
                                   "announcement.")
            return
        event = Event.from_event_id(event_id)
        if not event.get_is_active():
            return error_embed(ctx, "This event is not active")
        postpone_amount = timedelta(minutes=minutes, hours=hours, days=days)
        event_time = datetime.fromisoformat(event.get_event_time_est())
        signup_deadline = datetime.fromisoformat(event.get_signup_deadline())
        new_event_time = event_time + postpone_amount
        new_signup_deadline = signup_deadline + postpone_amount
        now = datetime.now(timezone(TIMEZONE))
        if datetime.now(timezone(TIMEZONE)) >= new_event_time + timedelta(minutes=5):
            await error_embed(ctx, "You must postpone the event to a time at least 5 minutes away from now")
            return
        if new_signup_deadline < now + timedelta(minutes=1):
            await response_embed(ctx, "Updating Signup Deadline", "Due to the late postpone, the signup deadline will "
                                                                  "now equal the event time.")
            new_signup_deadline = new_event_time
        announcement_channel = self.bot.get_channel(event.announcement_channel)
        announcement_message = await announcement_channel.fetch_message(event.event_id)
        event.set_event_time_est(datetime.isoformat(new_event_time))
        event.set_signup_deadline(datetime.isoformat(new_signup_deadline))
        event.set_is_active(True)
        event.set_is_signup_active(True)
        event.update()
        embed = announcement_message.embeds[0]
        embed.description = f"**Time:**\n{get_embed_time_string(new_event_time)}\n\n**Signup Deadline:**" \
                            f"\n{get_embed_time_string(new_signup_deadline)}\n\n{event.description}\n\nReact with ✅ to play" \
                            f"\nReact with 🔇 if you cannot speak\nReact with 🛗 if you are able to sub"
        embed.title += " (POSTPONED)" if "(POSTPONED)" not in embed.title else ""
        signup_role = ctx.guild.get_role(event.signup_role)
        await announcement_message.edit(embed=embed)
        await announcement_channel.send(f"{signup_role.mention} **{event.title}** has been **postponed** to"
                                        f" **{get_embed_time_string(new_event_time)} (EST)**")
        await success_embed(ctx, f"**{event.title}** has been **postponed** to **{get_embed_time_string(new_event_time)}"
                                 f" (EST)**")

    @cog_slash(guild_ids=SLASH_COMMANDS_GUILDS, options=[])
    async def removeevents(self, ctx):
        """Removes all events that are currently inactive"""
        if not has_permissions(ctx, MOD_ROLE):
            await ctx.send("You do not have sufficient permissions to perform this command", hidden=True)
            return False
        events = Event.fetch_events_list()
        info_embed = Embed(title="Deleted Events", description="Here is a list of **deleted events** and their details",
                           colour=Colour.dark_purple())
        for event in events:
            if not event.get_is_active():
                info_embed.description += f"\n**{event.title}** `{event.time_est}`\n> `{event.event_id}`"
                event.delete()
        info_embed.description += "\n\n**Currently active events (/currentevents):**"
        for event in Event.fetch_active_events_list():
            info_embed.description += f"\n**{event.title}** `{event.time_est}`\n> `{event.event_id}`"
        await ctx.send(embed=info_embed)

    @cog_slash(guild_ids=SLASH_COMMANDS_GUILDS, options=[])
    async def currentevents(self, ctx):
        """Gets a list of all active events"""
        if not has_permissions(ctx, MOD_ROLE):
            await ctx.send("You do not have sufficient permissions to perform this command", hidden=True)
            return False
        info_embed = Embed(title="Current Events", description="Here is a list of **events** and their details",
                           colour=Colour.dark_purple())
        for event in Event.fetch_events_list():
            announcement_url = f"https://discord.com/channels/{event.guild_id}/{event.announcement_channel}/" \
                               f"{event.event_id}"
            info_embed.description += f"\n[**{event.title}**]({announcement_url}) `{event.time_est}`\n> `{event.event_id}`\n" \
                                      f"> Active: **{str(event.is_active) + (' 🟢' if event.is_active else ' 🔴')}**"
        await ctx.send(embed=info_embed)

    @cog_slash(guild_ids=SLASH_COMMANDS_GUILDS,
                    options=[
                        mc.create_option(name="mode", description="Whether to set or change elo",
                                         option_type=3, required=True,
                                         choices=[mc.create_choice(name="change", value="change"),
                                                  mc.create_choice(name="set", value="set")]),
                        mc.create_option(name="amount", description="Positive or negative number",
                                         option_type=4, required=True),
                        mc.create_option(name="role", description="The role to allocate elo to",
                                         option_type=8, required=False),
                        mc.create_option(name="user", description="The user to allocate elo to",
                                         option_type=6, required=False),
                        mc.create_option(name="send_channel", description="A channel to send the update embed to",
                                         option_type=7, required=False),
                    ])
    async def elo(self, ctx, mode, amount, role=None, user=None, send_channel=None):
        """
        Allows PUG staff to allocate ELO following a match
        """
        if not has_permissions(ctx, MOD_ROLE):
            await ctx.send("You do not have sufficient permissions to perform this command", hidden=True)
            return False
        input_members = []
        changes_str = ""
        unregistered_members = ""
        server = ctx.guild
        if role:
            if role.members:
                input_members += role.members
            else:
                await error_embed(ctx, "The specified role has no members")
                return
        if user:
            input_members.append(server.get_member(user.id))

        for member in input_members:
            try:
                player = Player.from_discord_id(member.id)
            except PlayerDoesNotExistError:
                unregistered_members += f"{member.mention}\n"
            else:
                prev_elo = player.get_elo()
                if mode == "set":
                    if player.set_elo(amount):
                        changes_str += f"{member.mention} `{prev_elo}` → `{player.get_elo()}`\n"
                    else:
                        await error_embed(ctx, "Could not set ELO to that value")
                        return
                elif mode == "change":
                    player.change_elo(amount)
                    changes_str += f"{member.mention} `{prev_elo} → {player.get_elo()}`\n"
        summary = Embed(title="Summary of ELO changes", color=Colour.dark_purple())
        if changes_str:
            summary.add_field(name="ELO changes:", value=changes_str)
        else:
            summary.description = "No changes were made to ELO"
        if unregistered_members:
            summary.add_field(name="Unregistered members:", inline=False,
                              value=f"The following players need to register to receive ELO:\n{unregistered_members}")
        await ctx.send(embed=summary)
        if send_channel:
            await send_channel.send(embed=summary)
