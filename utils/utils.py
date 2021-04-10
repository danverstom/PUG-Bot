from discord import Embed, Colour
from discord.utils import get
from math import ceil
from asyncio import TimeoutError
from json import load, dump
import aiohttp


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
                            elements_per_page: int = 10, thumbnails=None, can_be_reversed=False):
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
    embed.set_footer(text=f"Page {current_page}/{num_pages}\n✅ to save results\n❌ to close this panel")

    if thumbnails:
        if len(thumbnails) == 1:
            embed.set_thumbnail(url=thumbnails[0])
        else:
            embed.set_thumbnail(url=thumbnails[current_page - 1])


    message = await ctx.send(embed=embed)

    await message.add_reaction("◀")
    await message.add_reaction("▶")
    if can_be_reversed:
        await message.add_reaction("🔃")
    await message.add_reaction("✅")
    await message.add_reaction("❌")

    def check(r, u):
        return r.message.id == message.id and u == ctx.author and str(r.emoji) in ["◀", "▶", "✅", "❌", "🔃"]

    while True:
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=60, check=check)
            if str(reaction.emoji) == "▶" and current_page != num_pages:
                current_page += 1
                embed = Embed(title=title, description=contents[current_page - 1],
                              colour=Colour.dark_purple())

                if thumbnails:
                    if len(thumbnails) == 1:
                        embed.set_thumbnail(url=thumbnails[0])
                    else:
                        embed.set_thumbnail(url=thumbnails[current_page - 1])

                embed.set_footer(text=f"Page {current_page}/{num_pages}\n✅ to save results\n❌ to close this panel")
                await message.edit(embed=embed)
                await message.remove_reaction(reaction, user)

            elif str(reaction.emoji) == "◀" and current_page > 1:
                current_page -= 1
                embed = Embed(title=title, description=contents[current_page - 1],
                              colour=Colour.dark_purple())

                if thumbnails:
                    if len(thumbnails) == 1:
                        embed.set_thumbnail(url=thumbnails[0])
                    else:
                        embed.set_thumbnail(url=thumbnails[current_page - 1])

                embed.set_footer(text=f"Page {current_page}/{num_pages}\n✅ to save results\n❌ to close this panel")
                await message.edit(embed=embed)
                await message.remove_reaction(reaction, user)
            elif str(reaction.emoji) == "✅":
                await message.clear_reactions()
                embed.title = embed.title + " (Saved)"
                embed.set_footer(text=f"Page {current_page}/{num_pages} (Saved)")
                await message.edit(embed=embed)
                break
            elif str(reaction.emoji) == "🔃" and can_be_reversed:
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

                embed.set_footer(text=f"Page {current_page}/{num_pages}\n✅ to save results\n❌ to close this panel")
                await message.edit(embed=embed)
                await message.remove_reaction(reaction, user)
            elif str(reaction.emoji) == "❌":
                await message.edit(content="Message Expired", embed=None)
                await message.clear_reactions()
                break
            else:
                await message.remove_reaction(reaction, user)
        except TimeoutError:
            await message.clear_reactions()
            embed.title = embed.title + " (Saved)"
            embed.set_footer(text=f"Page {current_page}/{num_pages} (Saved)")
            await message.edit(embed=embed)
            break
