from database.Player import Player
from utils.utils import request_async_json
import logging
from aiohttp import ClientSession
from asyncio import sleep as async_sleep


async def get_lifetime_stats(username):
    get_player_id_url = "https://by48xt0cuf.execute-api.us-east-1.amazonaws.com/default/request-player?name={}"
    stats_from_id_url = "https://by48xt0cuf.execute-api.us-east-1.amazonaws.com/default/request-player?id={}"
    new_player_request_url = "https://qe824lieck.execute-api.us-east-1.amazonaws.com/default/new-player?id={}"
    response = await request_async_json(get_player_id_url.format(username), 'text/plain')
    if response:
        json = response[1]
        logging.info(json)
        if str(json).startswith("No player found"):
            return False
        if json["uuid"]:
            player_id = json["id"]
        else:
            return False
    else:
        return False
    stats_response = await request_async_json(stats_from_id_url.format(player_id), 'text/plain')
    if not stats_response:
        logging.info("Request failed")
        return False
    json_response = stats_response[1]
    if json_response["data"]:
        data = json_response["data"]
    else:
        logging.info(f"Player data for `{username}` is not loaded yet")
        async with ClientSession() as session:
            async with session.get(new_player_request_url.format(player_id)) as r:
                if r.status == 200:
                    text = await r.text()
                    if text == "Success":
                        await async_sleep(10)
                        stats_response = await request_async_json(stats_from_id_url.format(player_id), 'text/plain')
                        json_response = stats_response[1]
                        data = json_response["data"]
                        if not data:
                            logging.info("No data was found")
                            return False
                        else:
                            logging.info("Data loaded")
                    else:
                        logging.info(text)
                        return False
                else:
                    logging.info("Request to load new player data failed")
                    return False
    return data
