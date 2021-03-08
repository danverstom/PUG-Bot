from discord import Embed, Colour
from discord.channel import TextChannel
from discord.ext import tasks
from discord.ext.commands import Cog, has_role
from discord_slash.cog_ext import cog_slash
from discord_slash.utils import manage_commands as mc

from utils.config import SLASH_COMMANDS_GUILDS, MOD_ROLE, SIGNUPS_TRACKER_INTERVAL_SECONDS
from utils.event_util import get_event_time, check_if_cancel, announce_event
from utils.utils import response_embed, error_embed
from database.Event import Event
from database.Signup import Signup, SignupDoesNotExistError

from datetime import datetime, timedelta
from pytz import timezone


class EventCommands(Cog, name="Event Commands"):
    """
    This category contains event commands that can be used by pug mods+
    """

    def __init__(self, bot):
        self.bot = bot

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
                                         description="Amount of time (in minutes) before the event for signup deadline",
                                         option_type=4, required=False)],
               guild_ids=SLASH_COMMANDS_GUILDS)
    @has_role(MOD_ROLE)
    async def event(self, ctx, title, announcement_channel, mention_role, signup_channel, signup_role, event_time,
                    event_date="", signup_deadline=20):
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
                            f"{announcement_channel.mention}\n**Mention Role:**: {mention_role}\n" \
                            f"**Signups List Channel:** {signup_channel.mention}\n**Signup Role:** {signup_role.mention}"
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

        Event.add_event(event_message_ids[0], title, description, event_time_package[0][0].isoformat(),
                        datetime.now(timezone('EST')).isoformat(), ctx.author.id, ctx.guild.id, announcement_channel.id,
                        signup_channel.id, event_message_ids[1], event_time_package[1][0].isoformat())

    @tasks.loop(seconds=SIGNUPS_TRACKER_INTERVAL_SECONDS)
    async def check_signups(self):
        for event in Event.fetch_events_list():
            can_play_users = []
            can_play_true = []
            can_play_false = []
            is_muted_users = []
            is_muted_true = []
            is_muted_false = []
            can_sub_users = []
            can_sub_true = []
            can_sub_false = []

            current_signups = Signup.fetch_signups_list(event.event_id)
            current_can_play = [user.user_id for user in current_signups if user.can_play]
            current_is_muted = [user.user_id for user in current_signups if user.is_muted]
            current_can_sub = [user.user_id for user in current_signups if user.can_sub]
            announcement_channel = self.bot.get_channel(event.announcement_channel)
            announcement_message = await announcement_channel.fetch_message(event.event_id)
            reactions = announcement_message.reactions

            # Get reactions and changes from last check
            for reaction in reactions:
                if reaction.emoji == "✅":
                    can_play_users = [user for user in await reaction.users().flatten() if user.id != self.bot.user.id]
                    can_play_users_id = [user.id for user in can_play_users]
                    can_play_true = [user for user in can_play_users_id if user not in current_can_play]
                    can_play_false = [user for user in current_can_play if user not in can_play_users_id]
                elif reaction.emoji == "🔇":
                    is_muted_users = [user for user in await reaction.users().flatten() if user.id != self.bot.user.id]
                    is_muted_users_id = [user.id for user in is_muted_users]
                    is_muted_true = [user for user in is_muted_users_id if user not in current_is_muted]
                    is_muted_false = [user for user in current_is_muted if user not in is_muted_users_id]
                elif reaction.emoji == "🛗":
                    can_sub_users = [user for user in await reaction.users().flatten() if user.id != self.bot.user.id]
                    can_sub_users_id = [user.id for user in can_sub_users]
                    can_sub_true = [user for user in can_sub_users_id if user not in current_can_sub]
                    can_sub_false = [user for user in current_can_sub if user not in can_sub_users_id]

            # Update database according to changes
            for user in can_play_true:
                try:
                    signups = Signup.from_user_event(user, event.event_id)
                    signups.set_can_play(True)
                except SignupDoesNotExistError:
                    Signup.add_signup(user, event.event_id, can_play=True)
            for user in is_muted_true:
                try:
                    signups = Signup.from_user_event(user, event.event_id)
                    signups.set_is_muted(True)
                except SignupDoesNotExistError:
                    Signup.add_signup(user, event.event_id, is_muted=True)
            for user in can_sub_true:
                try:
                    signups = Signup.from_user_event(user, event.event_id)
                    signups.set_can_sub(True)
                except SignupDoesNotExistError:
                    Signup.add_signup(user, event.event_id, can_sub=True)
            for user in can_play_false:
                signups = Signup.from_user_event(user, event.event_id)
                signups.set_can_play(False)
                if signups.is_unsigned():
                    signups.delete()
            for user in is_muted_false:
                signups = Signup.from_user_event(user, event.event_id)
                signups.set_is_muted(False)
                if signups.is_unsigned():
                    signups.delete()
            for user in can_sub_false:
                signups = Signup.from_user_event(user, event.event_id)
                signups.set_can_sub(False)
                if signups.is_unsigned():
                    signups.delete()

            # Update signup message
            signup_channel = self.bot.get_channel(event.signup_channel)
            signup_message = await signup_channel.fetch_message(event.signup_message)
            embed = signup_message.embeds[0]
            if can_play_users:
                value = [f"{index+1}: {user.mention}" for index, user in enumerate(can_play_users)]
                embed.set_field_at(index=0, name=f"✅ Players: {len(can_play_users)}", value="\n".join(value),
                                   inline=False)
            else:
                embed.set_field_at(index=0, name="✅ Players: 0", value="No one :(", inline=False)
            if is_muted_users:
                value = [f"{index+1}: {user.mention}" for index, user in enumerate(is_muted_users)]
                embed.set_field_at(index=1, name=f"🔇 Mutes: {len(is_muted_users)}", value="\n".join(value),
                                   inline=False)
            else:
                embed.set_field_at(index=1, name="🔇 Mutes: 0", value="No one :)", inline=False)
            if can_sub_users:
                value = [f"{index+1}: {user.mention}" for index, user in enumerate(can_sub_users)]
                embed.set_field_at(index=2, name=f"🛗 Subs: {len(can_sub_users)}", value="\n".join(value), inline=False)
            else:
                embed.set_field_at(index=2, name="🛗 Subs: 0", value="No one :(", inline=False)

            await signup_message.edit(embed=embed)
