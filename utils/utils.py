from discord import Embed, Colour


async def error_embed(ctx, description):
    embed = Embed(title="Error ❌", description=description, color=Colour.dark_red())
    await ctx.send(embed=embed)


async def success_embed(ctx, description):
    embed = Embed(title="Success ✅", description=description, color=Colour.green())
    await ctx.send(embed=embed)


async def response_embed(ctx, title, description):
    embed = Embed(title=title, description=description, color=Colour.dark_purple())
    await ctx.send(embed=embed)
