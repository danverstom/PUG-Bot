from discord import Embed, Colour
from utils.config import ELEMENTS_PER_PAGE
from math import ceil
from asyncio import sleep as async_sleep, TimeoutError


async def error_embed(ctx, description):
    embed = Embed(title="Error ❌", description=description, color=Colour.dark_red())
    await ctx.send(embed=embed)


async def success_embed(ctx, description):
    embed = Embed(title="Success ✅", description=description, color=Colour.green())
    await ctx.send(embed=embed)


async def response_embed(ctx, title, description):
    embed = Embed(title=title, description=description, color=Colour.dark_purple())
    await ctx.send(embed=embed)


async def create_list_pages(bot, ctx, title, info, if_empty="Empty List"):
    if not info:
        await ctx.send(embed=Embed(title=title, description=if_empty, colour=Colour.dark_red()))
        return
    
    contents = []
    num_pages = ceil(len(info) / ELEMENTS_PER_PAGE)
    page = ""
    current_page = 1
    for index, value in enumerate(info):
        page = page + str(value + "\n")
        if not (index + 1) % ELEMENTS_PER_PAGE:
            contents.append(page)
            page = ""
    contents.append(page)

    embed = Embed(title=title, description=contents[current_page - 1], colour=Colour.dark_purple())
    embed.set_footer(text=f"Page {current_page}/{num_pages}")
    message = await ctx.send(embed=embed)

    await message.add_reaction("◀")
    await message.add_reaction("▶")

    def check(reaction, user):
        return reaction.message.id == message.id and user == ctx.author and str(reaction.emoji) in ["◀", "▶"]

    while True:
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=60, check=check)

            if str(reaction.emoji) == "▶" and current_page != num_pages:
                current_page += 1
                embed = Embed(title="Map List", description=contents[current_page - 1],
                              colour=Colour.dark_purple())
                embed.set_footer(text=f"Page {current_page}/{num_pages}")
                await message.edit(embed=embed)
                await message.remove_reaction(reaction, user)

            elif str(reaction.emoji) == "◀" and current_page > 1:
                current_page -= 1
                embed = Embed(title="Map List", description=contents[current_page - 1],
                              colour=Colour.dark_purple())
                embed.set_footer(text=f"Page {current_page}/{num_pages}")
                await message.edit(embed=embed)
                await message.remove_reaction(reaction, user)

            else:
                await message.remove_reaction(reaction, user)
        except TimeoutError:
            await message.edit(content="Message Expired", embed=None)
            await message.clear_reactions()
            break
