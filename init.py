from bot import bot, bot_token
from webserver.app import app
from hypercorn.asyncio import serve
from hypercorn.config import Config

config = Config()
config.bind = ["localhost:5000"]


# bot.loop.create_task(app.run_task())
bot.loop.create_task(serve(app, config=config))
bot.run(bot_token)


