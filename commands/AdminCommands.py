from discord.ext.commands import Cog, has_role
from discord import File, Embed, Colour
from utils.utils import get_json_data, error_embed, success_embed, response_embed, has_permissions, create_list_pages
from utils.image_util import compress
from database.Player import Player
import utils.config
import os
import sys
import platform
import subprocess
from json import dump, load
from shutil import copyfile
from pytz import timezone
from datetime import datetime

# Slash commands support
from discord_slash.cog_ext import cog_slash, manage_commands
from utils.config import *

# Web Server
from hypercorn.asyncio import serve
from hypercorn.config import Config
from asyncio import Event
from webserver.app import app
from logging import info


class AdminCommands(Cog, name="Admin Commands"):
    """
    These commands can be used by admins
    """

    def __init__(self, bot, slash, token):
        self.bot = bot
        self.slash = slash
        self.token = token
        self.web_task = None
        self.shutdown_event = Event()

    @Cog.listener()
    async def on_ready(self):
        config = Config()
        config.bind = [f"{WEB_SERVER_HOSTNAME}:{WEB_SERVER_PORT}"]
        self.web_task = self.bot.loop.create_task(serve(app, config=config, shutdown_trigger=self.shutdown_event.wait))

    @cog_slash(name="removecommands", description="Removes all slash commands from the bot",
               guild_ids=SLASH_COMMANDS_GUILDS)
    async def removecommands(self, ctx):
        if not has_permissions(ctx, ADMIN_ROLE):
            await ctx.send("You do not have sufficient permissions to perform this command", hidden=True)
            return False
        message = await response_embed(ctx, "Removing commands", "Please wait, this process can take a while")
        await manage_commands.remove_all_commands(self.bot.user.id, self.token, guild_ids=SLASH_COMMANDS_GUILDS)
        await message.delete()
        await success_embed(ctx, "Removed all commands from this bot")

    @cog_slash(name="restart", description="Restarts the bot",
               guild_ids=SLASH_COMMANDS_GUILDS,
               options=[
               manage_commands.create_option(name="pull_changes",
                                             option_type=5,
                                             description="if true, pull the latest changes from github",
                                             required=False),
               manage_commands.create_option(name="remove_commands",
                                             option_type=5,
                                             description="if true, remove commands before restart",
                                             required=False)])
    async def restart(self, ctx, pull_changes=False, remove_commands=False):
        if not has_permissions(ctx, ADMIN_ROLE):
            await ctx.send("You do not have sufficient permissions to perform this command", hidden=True)
            return False
        if (ctx.author.id != BOT_OWNER_ID) and pull_changes:
                await ctx.send("You must be the bot owner to use this option", hidden=True)
                return False
        msg = await ctx.send("`Bot is restarting`")
        if remove_commands:
            await msg.edit(content=msg.content + "\n`Removing commands - please wait, this process can take a while`")
            await manage_commands.remove_all_commands(self.bot.user.id, self.token, guild_ids=SLASH_COMMANDS_GUILDS)
            await msg.edit(content=msg.content + "\n`Removed all commands from the bot`")
        if pull_changes:
            await msg.edit(content=msg.content + "\n`Pulling latest changes`")
            output = subprocess.check_output("git pull", shell=True)
            await response_embed(ctx, "Update Summary", output.decode("utf8"))
        info("Triggering web server shutdown event")
        self.shutdown_event.set()
        info("Waiting for web server to shut down")
        await msg.edit(content=msg.content + "\n`Waiting for web server to shut down`")
        await self.web_task
        info("Web server shutdown complete")
        await msg.edit(content=msg.content + "\n`Web server shutdown complete. Bot restarting. Goodbye!`")
        info("Closing the bot")
        await self.bot.close()
        info("Bot has finished closing")

        # Checks for operating system
        operating_system = platform.system()
        if operating_system == "Windows":
            os.execv(sys.executable, ['python'] + sys.argv)
        elif operating_system == "Linux":
            os.execv(sys.executable, ['python3'] + sys.argv)
        else:
            await error_embed(ctx, "Bot is not running on Windows or Linux, failed to restart")
        quit()

    @cog_slash(guild_ids=SLASH_COMMANDS_GUILDS)
    async def debug(self, ctx):
        if not has_permissions(ctx, ADMIN_ROLE):
            await ctx.send("You do not have sufficient permissions to perform this command", hidden=True)
            return False
        if utils.config.debug:
            utils.config.debug = False
            await success_embed(ctx, "Toggled debug mode **off**")
        else:
            utils.config.debug = True
            await success_embed(ctx, "Toggled debug mode **on**")

    @cog_slash(guild_ids=SLASH_COMMANDS_GUILDS, options=[manage_commands.create_option(name="operation", description="add/dell",
                                      required=True, option_type=3, choices=[
                manage_commands.create_choice(name="add", value="add"),
                manage_commands.create_choice(name="del", value="del")
                                                        ]
                                      ),
                manage_commands.create_option(name="map_id", description="ID of map",
                                      required=True, option_type=4)
    ])
    async def editmaps(self, ctx, operation="", map_id: int = 0):
        if not has_permissions(ctx, ADMIN_ROLE):
            await ctx.send("You do not have sufficient permissions to perform this command", hidden=True)
            return False
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        map_id = int(map_id)

        if operation == "add":
            with open("utils/maps.json", "r+") as file:
                data = load(file)
                for k, v in data.items():
                    if int(v) == map_id:
                        return await error_embed(ctx, "Map already exists")

            embed = Embed(title="Adding map to database", description="Enter the name of the map", color=Colour.dark_purple())
            embed.set_footer(text="Type \"cancel\" to cancel")
            message = await ctx.send(embed=embed)
            response = await self.bot.wait_for("message", check=check)
            if not response.content:
                return await error_embed(ctx, "Not a string")
            if response.content.lower() == "cancel":
                return await ctx.send(embed=Embed(description="❌ Adding map cancelled", color=Colour.dark_red()))
                
            name = response.content
            embed = Embed(title="Adding map to database", description="Would you like to add an image?", color=Colour.dark_purple())
            embed.set_footer(text="Type \"y/yes\" to add map with an image\nType \"n/no\" to add map without an image\nType \"cancel\" to cancel map adding")
            message = await ctx.send(embed=embed)

            response = await self.bot.wait_for("message", check=check)
            if response.content.lower() in ["done", "finished", "yes", "y"]: #add map if y
                embed = Embed(title="Adding map to database", description="This can be a direct upload, or a direct link to an image (not supported yet)", color=Colour.dark_purple())
                message = await ctx.send(embed=embed)
                response = await self.bot.wait_for("message", check=check) #Send image here
                if not response.attachments:
                    return await error_embed(ctx, "No image attached")
                if not response.attachments[0].content_type.startswith("image"):
                    return await error_embed(ctx, "File uploaded is not image")
                attachment = response.attachments[0]
                embed = Embed(title="Confirm addition (y/n)",
                              description=f"Are you sure you want to add {name} ({map_id})?",
                              color=Colour.dark_purple())
                embed.set_image(url=attachment.url)

                message = await ctx.send(embed=embed)
                response = await self.bot.wait_for("message", check=check)
                is_correct = response.content.lower() == "y" or response.content.lower() == "yes"
                if not is_correct:
                    return await ctx.send(embed=Embed(description="❌ Adding map cancelled", color=Colour.dark_red()))
                await attachment.save(f"assets/map_screenshots/{map_id}.jpg")
                compress(f"assets/map_screenshots/{map_id}.jpg")
                await response_embed(ctx, "✅ Map added", "")
            elif response.content.lower() in ["no", "n"]:
                await response_embed(ctx, "✅ Map added", "")
            elif response.content.lower() == "cancel":
                return await ctx.send(embed=Embed(description="❌ Adding map cancelled", color=Colour.dark_red()))
            else:
                return await ctx.send(embed=Embed(description="❌ Adding map cancelled, please type yes, no or cancel next time", color=Colour.dark_red()))
            new_data = {name: map_id}
            data = None
            with open("utils/maps.json", "r+") as file:
                data = load(file)
                data.update(new_data)

            with open("utils/maps.json", "w") as file:
                dump(data, file, sort_keys=True, indent=4)



        elif operation == "del":
            name = None
            with open("utils/maps.json", "r+") as file:
                data = load(file)
 
                for k, v in data.items():
                    if int(v) == map_id:
                        name = k
                        data.pop(k)
                        break
                if name is None:
                    return await error_embed(ctx, "Map not found")
                try:
                    file = File(f"assets/map_screenshots/{map_id}.jpg", filename=f"{map_id}.png")
                    embed = Embed(file=file, title="Confirm deletion (y/n)", description=f"Are you sure you want to delete **{name}** ({map_id})?", color=Colour.dark_purple())
                    embed.set_image(url=f"attachment://{map_id}.png")
                    message = await ctx.send(file=file, embed=embed)
                except FileNotFoundError:
                    embed = Embed(title="Confirm deletion (y/n)",
                                  description=f"Are you sure you want to delete **{name}** ({map_id})?",
                                  color=Colour.dark_purple())
                    message = await ctx.send(embed=embed)
                response = await self.bot.wait_for("message", check=check)
                
                is_correct = response.content.lower() == "y" or response.content.lower() == "yes"
                if not is_correct:
                    return await ctx.send(embed=Embed(description="❌ Deleting map cancelled", color=Colour.dark_red()))
                
                with open("utils/maps.json", "w") as file:
                    dump(data,file, sort_keys=True, indent=4)
                if os.path.exists(f"assets/map_screenshots/{map_id}.jpg"):
                    os.remove(f"assets/map_screenshots/{map_id}.jpg")
                return await response_embed(ctx, "✅ Map deleted", "")

    @cog_slash(guild_ids=SLASH_COMMANDS_GUILDS, options=[])
    async def prune_missing_players(self, ctx):
        """Removes registered players from the database who aren't in the server"""
        if not has_permissions(ctx, ADMIN_ROLE) and ctx.guild not in SLASH_COMMANDS_GUILDS:
            await ctx.send("You do not have sufficient permissions to perform this command", hidden=True)
            return False
        await ctx.defer()
        tz = timezone('US/Eastern')
        time = datetime.now(tz).strftime("%Y%m%d-%H%M%S")
        backup_filename = f"backups/database-{time}.db"
        copyfile("database/database.db", backup_filename)
        await success_embed(ctx, f"Created backup file: `{backup_filename}`")
        players = Player.fetch_players_list()
        guild_member_ids = [member.id for member in ctx.guild.members]
        deleted_player_names = []
        for player in players:
            if player.discord_id not in guild_member_ids:
                deleted_player_names.append(player.minecraft_username)
                player.delete()
        if deleted_player_names:
            await success_embed(ctx, f"Removed players `{', '.join(deleted_player_names)}` from database.")
        else:
            await error_embed(ctx, "No players to prune.")

    @cog_slash(guild_ids=SLASH_COMMANDS_GUILDS, options=[])
    async def backup(self, ctx):
        """Creates backup of database"""
        if not has_permissions(ctx, ADMIN_ROLE):
            await ctx.send("You do not have sufficient permissions to perform this command", hidden=True)
            return False
        tz = timezone('US/Eastern')
        time = datetime.now(tz).strftime("%Y%m%d-%H%M%S")
        backup_filename = f"backups/database-{time}.db"
        copyfile("database/database.db", backup_filename)
        await success_embed(ctx, f"Created backup file: `{backup_filename}`")

    @cog_slash(guild_ids=SLASH_COMMANDS_GUILDS, options=[])
    async def missingmaps(self, ctx):
        if not has_permissions(ctx, ADMIN_ROLE):
            await ctx.send("You do not have sufficient permissions to perform this command", hidden=True)
            return False
        maps = get_json_data("utils/maps.json")
        missing = []
        for ctfmap in maps:
            if not os.path.exists(f"assets/map_screenshots/{maps[ctfmap]}.jpg"):
                missing.append(f"{ctfmap} ({maps[ctfmap]})")
        await create_list_pages(self.bot, ctx, "Missing Screenshots", missing)