from discord import Embed, Colour
from discord.ext.commands import Cog, has_role
from discord_slash.cog_ext import cog_slash

from utils.config import SLASH_COMMANDS_GUILDS, MOD_ROLE


async def check_if_cancel(ctx, response):
    if response.content.lower() == "cancel":
        embed = Embed(description="✅ Event Creation Cancelled", color=Colour.green())
        await ctx.send(embed=embed)
        return True
    else:
        return False


def check_if_channel(ctx, response):
    return bool([channel for channel in ctx.guild.channels if channel.mention == response.content])


def check_if_role(ctx, response):
    if response.content.lower() == "everyone":
        return "@everyone"
    elif response.content.lower() == "none":
        return "None"
    else:
        roles = [role for role in ctx.guild.roles if role.name.lower() == response.content.lower()]
        if roles:
            return roles[0].mention
        else:
            return ""


class EventCommands(Cog, name="Event Commands"):
    """
    This category contains event commands that can be used by pug mods+
    """

    def __init__(self, bot):
        self.bot = bot

    @cog_slash(name="event", description="Creates an event.", guild_ids=SLASH_COMMANDS_GUILDS)
    @has_role(MOD_ROLE)
    async def event(self, ctx):
        def check(m):
            return m.author == ctx.author

        embed = Embed(title="Event Creation", color=Colour.dark_purple(), footer="Type \"cancel\" to cancel the event")
        embed.add_field(name="Title:", value="Enter the title of the event")
        message = await ctx.send(embed=embed)
        response = await self.bot.wait_for("message", check=check)
        if await check_if_cancel(ctx, response):
            return
        title = response.content
        await response.delete()

        embed.clear_fields()
        embed.description = f"Set title to \"{title}\""
        embed.set_footer(text="Type \"cancel\" to cancel the event")
        embed.add_field(name="Description:", value="Enter the description of the event")
        await message.delete()
        message = await ctx.send(embed=embed)
        response = await self.bot.wait_for("message", check=check)
        if await check_if_cancel(ctx, response):
            return
        description = response.content
        await response.delete()

        announcement_channel = ""
        embed.clear_fields()
        embed.description = f"Set description to:\n\"{description}\""
        embed.set_footer(text="Type \"cancel\" to cancel the event")
        embed.add_field(name="Announcement Channel:",
                        value="Enter the channel where announcement should be posted.\nWrite the full channel mention, with #")
        await message.delete()
        message = await ctx.send(embed=embed)
        while not announcement_channel:
            response = await self.bot.wait_for("message", check=check)
            if await check_if_cancel(ctx, response):
                return
            if check_if_channel(ctx, response):
                announcement_channel = response.content
            else:
                embed.description = f"❌ Invalid Channel: This is not a valid channel mention"
                await message.edit(embed=embed)
            await response.delete()

        mention_role = ""
        embed.clear_fields()
        embed.description = f"Set announcement channel to {announcement_channel}"
        embed.set_footer(text="Type \"cancel\" to cancel the event")
        embed.add_field(name="Mention Role:",
                        value="Enter the name of the role to mention for the event (everyone, None)")
        await message.delete()
        message = await ctx.send(embed=embed)
        while not mention_role:
            response = await self.bot.wait_for("message", check=check)
            if await check_if_cancel(ctx, response):
                return
            mention_role = check_if_role(ctx, response)
            if not mention_role:
                embed.description = f"❌ Invalid Role: This is not a valid role name"
                await message.edit(embed=embed)
            await response.delete()

        signup_channel = ""
        embed.clear_fields()
        embed.description = f"Set mention role to {mention_role}"
        embed.set_footer(text="Type \"cancel\" to cancel the event")
        embed.add_field(name="Signup Channel:",
                        value="Enter the channel where the signup list should be posted.\nWrite the full channel mention, with #")
        await message.delete()
        message = await ctx.send(embed=embed)
        while not signup_channel:
            response = await self.bot.wait_for("message", check=check)
            if await check_if_cancel(ctx, response):
                return
            if check_if_channel(ctx, response):
                signup_channel = response.content
            else:
                embed.description = f"❌ Invalid Channel: This is not a valid channel mention"
                await message.edit(embed=embed)
            await response.delete()

        signup_role = ""
        embed.clear_fields()
        embed.description = f"Set signup channel to {signup_channel}"
        embed.set_footer(text="Type \"cancel\" to cancel the event")
        embed.add_field(name="Signup Role:",
                        value="Enter the name of the role to mention for the event (Signed)")
        await message.delete()
        message = await ctx.send(embed=embed)
        while not signup_role:
            response = await self.bot.wait_for("message", check=check)
            if await check_if_cancel(ctx, response):
                return
            signup_role = check_if_role(ctx, response)
            if not signup_role:
                embed.description = f"❌ Invalid Role: This is not a valid role name"
                await message.edit(embed=embed)
            await response.delete()
