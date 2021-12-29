from discord import Embed, Colour
from discord.utils import get
from math import ceil
from asyncio import TimeoutError
from json import load, dump
import aiohttp
from random import choice
from discord_slash.utils import manage_components
from discord_slash.model import ButtonStyle
from discord_slash.context import ComponentContext


def get_failure_gif() -> str:
    failure_gifs = [
        "https://c.tenor.com/ciNDyf6AgH0AAAAd/disappointed-disappointed-fan.gif",
        "https://c.tenor.com/gW49QSTtYBUAAAAC/facepalm-seriously.gif",
        "https://c.tenor.com/ZFc20z8DItkAAAAd/facepalm-really.gif",
        "https://c.tenor.com/ibwfTRYbgocAAAAC/facepalm.gif",
        "https://c.tenor.com/nkYPXkAUs3oAAAAC/the-office-rainn-wilson.gif"

    ]
    gif = choice(failure_gifs)
    return gif


async def request_async_json(url, content_type):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            if r.status == 200:
                json = await r.json(content_type=content_type)
                return r, json
            else:
                return False

def has_permissions(ctx, required_role_name):
    server = ctx.bot.get_guild(ctx.guild_id)
    required_role = get(server.roles, name=required_role_name)
    if ctx.author.top_role.position >= required_role.position:
        return True
    else:
        return False


def save_json_file(file, content):
    with open(file, "w") as file:
        dump(content, file)


def get_json_data(file):
    with open(file, "r") as file:
        data = load(file)
    return data


async def error_embed(ctx, description):
    embed = Embed(title="Error ❌", description=description, color=Colour.dark_red())
    message = await ctx.send(embed=embed)
    return message


async def success_embed(ctx, description):
    embed = Embed(title="Success ✅", description=description, color=Colour.green())
    message = await ctx.send(embed=embed)
    return message


async def response_embed(ctx, title, description):
    embed = Embed(title=title, description=description, color=Colour.dark_purple())
    message = await ctx.send(embed=embed)
    return message


async def create_list_pages(bot, ctx, title: str, info: list, if_empty: str = "Empty List", sep: str = "\n",
                            elements_per_page: int = 10, thumbnails=None, can_be_reversed=False, random_item=False):
    if not info:
        await ctx.send(embed=Embed(title=title, description=if_empty, colour=Colour.dark_red()))
        return

    contents = []
    num_pages = ceil(len(info) / elements_per_page)
    page = ""
    current_page = 1
    for index, value in enumerate(info):
        page = page + str(value + sep)
        if not (index + 1) % elements_per_page:
            contents.append(page)
            page = ""
    contents.append(page)

    embed = Embed(title=title, description=contents[current_page - 1], colour=Colour.dark_purple())
    embed.set_footer(text=f"Page {current_page}/{num_pages}")

    if thumbnails:
        if len(thumbnails) == 1:
            embed.set_thumbnail(url=thumbnails[0])
        else:
            embed.set_thumbnail(url=thumbnails[current_page - 1])

    buttons = []

    if num_pages != 1:
        buttons.append(manage_components.create_button(ButtonStyle.primary, emoji="◀"))
        buttons.append(manage_components.create_button(ButtonStyle.primary, emoji="▶"))
    if can_be_reversed:
        buttons.append(manage_components.create_button(ButtonStyle.secondary, label="Reverse"))
    if random_item:
        buttons.append(manage_components.create_button(ButtonStyle.secondary, label="Shuffle"))

    buttons.append(manage_components.create_button(ButtonStyle.danger, label="Close"))

    action_row = manage_components.create_actionrow(*buttons)

    message = await ctx.send(embed=embed, components=[
        action_row
    ])
    

    while True:
        try:
            button_context: ComponentContext = await manage_components.wait_for_component(bot, timeout=120, components=action_row)
            if button_context.author.id != ctx.author.id:
                await button_context.send("These buttons belong to someone else - try using the command yourself", hidden=True)
                continue
        except TimeoutError:
            embed.set_footer(text=f"Page {current_page}/{num_pages} (Timed Out)")
            await message.edit(embed=embed, components=None)
            break
        if "emoji" in button_context.component.keys():
            if button_context.component["emoji"]["name"] == "▶":
                if  current_page != num_pages:
                    current_page += 1
                    embed = Embed(title=title, description=contents[current_page - 1],
                                colour=Colour.dark_purple())
                elif current_page == num_pages and num_pages != 1:  # Jump from last page to first page
                    current_page = 1
                    embed = Embed(title=title, description=contents[current_page - 1],
                                colour=Colour.dark_purple())
            elif button_context.component["emoji"]["name"] == "◀":
                if current_page == 1 and num_pages != 1:  # Jump from first page to last page
                    current_page = num_pages
                    embed = Embed(title=title, description=contents[current_page - 1],
                                colour=Colour.dark_purple())
                elif current_page > 1:
                    current_page -= 1
                    embed = Embed(title=title, description=contents[current_page - 1],
                                colour=Colour.dark_purple())
            if thumbnails:
                    if len(thumbnails) == 1:
                        embed.set_thumbnail(url=thumbnails[0])
                    else:
                        embed.set_thumbnail(url=thumbnails[current_page - 1])
            embed.set_footer(text=f"Page {current_page}/{num_pages}")
            await button_context.edit_origin(embed=embed)
        elif "label" in button_context.component.keys():
            if button_context.component["label"] == "Reverse" and can_be_reversed:
                info.reverse()
                contents = []
                num_pages = ceil(len(info) / elements_per_page)
                page = ""
                for index, value in enumerate(info):
                    page = page + str(value + sep)
                    if not (index + 1) % elements_per_page:
                        contents.append(page)
                        page = ""
                contents.append(page)

                current_page = 1
                embed = Embed(title=title, description=contents[current_page - 1],
                            colour=Colour.dark_purple())

                if thumbnails:
                    if len(thumbnails) == 1:
                        embed.set_thumbnail(url=thumbnails[0])
                    else:
                        embed.set_thumbnail(url=thumbnails[current_page - 1])

                embed.set_footer(text=f"Page {current_page}/{num_pages}")
                await button_context.edit_origin(embed=embed)
            elif button_context.component["label"] == "Shuffle" and random_item:
                embed = Embed(title=title, description=choice(info),
                            colour=Colour.dark_purple())
                await button_context.edit_origin(embed=embed)
            elif button_context.component["label"] == "Close":
                await message.edit(content="Closing message..", embed=None, components=None)
                await button_context.edit_origin(content="List Pages Closed")
                # This requires 2 requests, one to actually clear the embed and components and another to show to discord the interaction succeeded
                # Hopefully a change is made to the slash lib so it supports removing the embed/components
                break
        
