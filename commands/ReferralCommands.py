from discord import Embed, Colour, User, user
from discord.ext.commands import Cog
from discord_slash.cog_ext import cog_slash
from discord_slash.utils import manage_commands as mc
from discord.utils import get
from utils.config import *
from utils.utils import *
from utils.event_util import get_embed_time_string
from discord.errors import Forbidden
from discord.ext import tasks

from database.referrals import *
from datetime import datetime
from logging import info

"""
Used this article as a guide for tracking invites:
https://medium.com/@tonite/finding-the-invite-code-a-user-used-to-join-your-discord-server-using-discord-py-5e3734b8f21f
"""

# TODO: issue prizes to those who refer players


class ReferralCommands(Cog, name="Referral Commands"):
    def __init__(self, bot):
        self.bot = bot
        self.invite_cache = {}

    @Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            self.bot_channel = self.bot.get_channel(BOT_OUTPUT_CHANNEL)
            self.invite_cache[guild.id] = await guild.invites()

    @Cog.listener()
    async def on_member_join(self, member):
        invites_before_join = self.invite_cache[member.guild.id]
        invites_after_join = await member.guild.invites()
        for invite in invites_before_join:
            if invite.uses < self.find_invite_by_code(invites_after_join, invite.code).uses:
                self.invite_cache[member.guild.id] = invites_after_join
                admin_role = get(member.guild.roles, name=ADMIN_ROLE)
                inviter_member = get(member.guild.members, id=invite.inviter.id)
                if has_user_left(member.id, member.guild.id):
                    info(f"Member '{member.name}' joined but a referral was not logged because the user was previously in the server")
                    return
                if not inviter_member:
                    info(f"Member '{member.name}' joined but a referral was not logged because the referrer is not in the server")
                    return
                if inviter_member.top_role.position >= admin_role.position:
                    info(f"Member '{member.name}' joined but a referral was not logged because the referrer is an admin+")
                    return
                if log_referral(invite.code, member.id, invite.inviter.id):
                    info(f"Logged new referral of member '{member.name}' who was referred by '{invite.inviter.name}'")
                    await self.bot_channel.send(
                        f"Logged new referral of member {member.mention} who was referred by {invite.inviter.mention}"
                    )
                else:
                    info(f"{member.name} joined the server, but was already referred")
                    await self.bot_channel.send(
                        f"{member.mention} joined using invite code {invite.code} created by {invite.inviter.name}. "
                        f"No referral logged - they have been referred before."
                    )

    @Cog.listener()
    async def on_member_remove(self, member):
        self.invite_cache[member.guild.id] = await member.guild.invites()
        log_user_leave(member.id, member.guild.id)

    
    @staticmethod
    def find_invite_by_code(invite_list, code):
        for invite in invite_list:
            if invite.code == code:
                return invite

    @cog_slash(guild_ids=SLASH_COMMANDS_GUILDS, options=[
        mc.create_option(
            name="has_played",
            description="Filter out referrals where the user has not participated in one event",
            option_type=5,
            required=False
        )
    ], description="Referrals leaderboard")
    async def referrals(self, ctx, has_played=False):
        if has_played: 
            all_referrals = get_inviters_list_has_played()  # Returns list of inviter IDs
        else:
            all_referrals = get_inviters_list()
        count = {}
        for user_id in all_referrals:  # Count the number of referrals for each user
            try:
                count[user_id] += 1
            except KeyError:
                count[user_id] = 1  # This count entry does not exist yet so we add it
        results = []
        for user_id in count.keys():
            member = ctx.guild.get_member(user_id)
            if not member:
                info(f"[REFERRALS LEADERBOARD] member id {user_id} not found, skipping")
                continue  # If the user is not in the server then don't include them in the leaderboard
            results.append((member, count[user_id]))
        results = list(sorted(results, key=lambda result: result[1], reverse=True))
        str_items = []
        counter = 1
        for result in results:
            str_items.append(
                f"**#{counter}** {result[0].mention} - **{result[1]}**"
            )
            counter += 1
        await create_list_pages(
            self.bot, 
            ctx, 
            "Referrals Leaderboard " + ("(Played)" if has_played else ""),
            info=str_items
        )

    @cog_slash(guild_ids=SLASH_COMMANDS_GUILDS, options=[
        mc.create_option(
            name="user",
            description="The user to view the referrals for",
            option_type=6,
            required=False
        )
    ], description="View referrals of yourself or another player")
    async def viewreferrals(self, ctx, user=False):
        if not user:
            user = ctx.author
        referrals = get_filtered_referrals("inviter_id", user.id)
        list_items = []
        for referral in referrals:
            referred_member = ctx.guild.get_member(referral[2])
            if not referred_member:
                continue
            date_string = get_embed_time_string(datetime.fromisoformat(referral[4]))
            list_items.append(
                f"**Referral ID:** {referral[0]}\n"
                f"**Invite code:** {referral[1]}\n"
                f"**Invited member:** {referred_member}\n"
                f"**Date:** {date_string}\n"
                f"**Signed for an event:** {'Yes' if referral[5] else 'No'}\n"
            )
        await create_list_pages(
            self.bot, 
            ctx, 
            f"Referrals - {user.name}",
            info=list_items
        )