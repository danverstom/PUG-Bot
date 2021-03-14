from discord import Embed, Colour
import re
from discord.channel import TextChannel
from discord.ext import tasks
from discord.ext.commands import Cog
from discord_slash.cog_ext import cog_slash
from discord_slash.utils import manage_commands as mc

from utils.config import SLASH_COMMANDS_GUILDS, MOD_ROLE, SIGNUPS_TRACKER_INTERVAL_SECONDS
from utils.event_util import get_event_time, check_if_cancel, announce_event, reaction_changes, save_signups
from utils.utils import response_embed, error_embed, success_embed, has_permissions
from database.Event import Event
from database.Signup import Signup
from asyncio import TimeoutError

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
        for event_id in self.events.keys():
            self.signups[event_id] = Signup.fetch_signups_list(event_id)

    def cog_unload(self):
        self.check_signups.cancel()

    @Cog.listener()
    async def on_ready(self):
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
                                    datetime.now(timezone('EST')).isoformat(), ctx.author.id, ctx.guild.id,
                                    announcement_channel.id, signup_channel.id, event_message_ids[1], signup_role.id,
                                    event_time_package[1][0].isoformat())
        self.events[event_message_ids[0]] = new_event
        self.signups[event_message_ids[0]] = []

    @tasks.loop(seconds=SIGNUPS_TRACKER_INTERVAL_SECONDS)
    async def check_signups(self):
        for event in self.events.values():
            if datetime.now(timezone('EST')) >= datetime.fromisoformat(event.time_est) + timedelta(days=1):
                event.set_is_active(False)
            elif not event.is_signups_active:
                continue
            elif datetime.now(timezone('EST')) >= datetime.fromisoformat(event.signup_deadline):
                event.set_is_signup_active(False)
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
                save_signups(self.signups[event.event_id], signups)
                self.signups[event.event_id] = signups
                can_play = [user for user in signups if user.can_play]
                can_sub = [user for user in signups if user.can_sub]
                signup_role = self.bot.get_guild(event.guild_id).get_role(event.signup_role)
                [await self.bot.get_user(user).add_roles(signup_role) for user in can_play]
                embed = signup_message.embeds[0]
                if can_play:
                    value = [f"{index + 1}: <@{user.user_id}> {'🔇' if user.is_muted else ''}"
                             for index, user in enumerate(can_play)]
                    embed.set_field_at(index=0, name=f"✅ Players: {len(can_play)}", value="\n".join(value),
                                       inline=False)
                else:
                    embed.set_field_at(index=0, name=f"✅ Players: 0", value="No one :(", inline=False)
                if can_sub:
                    value = [f"{index + 1}: <@{user.user_id}> {'🔇' if user.is_muted else ''}"
                             for index, user in enumerate(can_sub)]
                    embed.set_field_at(index=1, name=f"🛗 Subs: {len(can_sub)}", value="\n".join(value), inline=False)
                else:
                    embed.set_field_at(index=1, name=f"🛗 Subs: 0", value="No one :(", inline=False)
                await signup_message.edit(embed=embed)

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
                                         description="Gets a list of discord tags",
                                         option_type=3, required=True)],
               guild_ids=SLASH_COMMANDS_GUILDS)
    async def getsignups(self, ctx, event_id):
        if not has_permissions(ctx, MOD_ROLE):
            await ctx.send("You do not have sufficient permissions to perform this command", hidden=True)
            return False
        try:
            event_id = int(event_id)
        except ValueError:
            await error_embed(ctx, "Please enter an integer")
            return
        signups = self.signups.setdefault(event_id)
        if not signups:
            signups = Signup.fetch_signups_list(event_id)
        if signups:
            tag_str = ""
            for signup in signups:
                user = self.bot.get_user(signup.user_id)
                tag_str += f"@{user} \n"
            await ctx.send(f"```{tag_str}```")
        else:
            await error_embed(ctx, "Could not find the event you are searching for. Use the message ID of the event "
                                   "announcement.")

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
                        server = ctx.message.guild
                        bot_member = server.get_member(self.bot.user.id)

                        if bot_member.top_role.position <= role.position:
                            await error_embed(ctx, "This role is too high to be set by the bot. Please enter a "
                                                   "different role.")
                        else:
                            roles_dict[role] = members
                    else:
                        await error_embed(ctx, "You can only mention one role at a time")
                else:
                    await error_embed(ctx, "You did not mention any members")
            await info_message.delete()
