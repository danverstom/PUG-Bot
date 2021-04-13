from bot import bot, bot_token
from webserver.app import app

bot.loop.create_task(app.run_task())
bot.run(bot_token)


