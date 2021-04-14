from bot import bot, bot_token
from webserver.app import app
from hypercorn.asyncio import serve
from hypercorn.config import Config
from asyncio import Future

config = Config()
config.bind = ["localhost:8080"]


# bot.loop.create_task(app.run_task())
bot.loop.create_task(serve(app, config=config, shutdown_trigger=lambda: Future()))
bot.run(bot_token)


