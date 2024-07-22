from telethon.sync import TelegramClient, events
from chaty import *
import asyncio
import random
from telethon.tl.functions.messages import GetAllStickersRequest
from telethon.tl.functions.messages import GetStickerSetRequest
from telethon.tl.types import InputStickerSetID
from keys import session_name, api_id, api_hash
from logger import Logger
from keys import ban_list
import json
from message_queue import user_queue
from datetime import datetime

# get logger and settings
logger = Logger.__call__().get_logger()
with open("settings.json") as file:
    settings = json.loads(file)
queue = message_queue()


with TelegramClient(session_name, api_id, api_hash, device_model='iPhone 13 Pro Max',system_version="4.16.30-vxhello") as client:
    client.send_message('me', 'Hi')
    global_chats = {}
    
    @client.on(events.NewMessage)
    async def handler(event):
        global global_chats
        if event.is_private:
            # get info about sender and message
            sender = await event.get_sender()
            sender_username = sender.username or sender.first_name or "Unknown"
            message_text = event.message.message
            user_id = event.message.user_id
            logger.info(f"Received message from {sender_username}: {message_text}")
            
            # load stickers
            sticker_sets = await client(GetAllStickersRequest(0))
            sticker_set = sticker_sets.sets[0]
            stickers = await client(GetStickerSetRequest(
                stickerset=InputStickerSetID(
                    id=sticker_set.id, access_hash=sticker_set.access_hash
                ),
                hash=0
            ))

            # ignore messages with random chance or when "sleeping"
            if random.randrange(settings["prob_to_ignore"]["from"]) > settings["prob_to_ignore"]["prob"] or datetime.now().hour > 23 or datetime.now().hour < 8:
                queue.add_message_to_queue(user_id, message_text)

            # TOASK: can i return in async funcs?
            # dont like SO much tabs
            else:
                # get all messages from user
                message_text = queue.pop_message_from_queue(user_id) + '\n' + message_text

                # pretend that reading
                await asyncio.sleep(int(len(message_text) / settings['to_read_divider']))

                # generate answer
                if len(event.message.message) >= 1 and sender_username not in ban_list:
                    bot = ChatInteraction(sender_username, global_chats)
                    answer, global_chats = bot.response(message_text)
                    answer = answer['content']
                    logger.info(f"Answer: {answer}")

                    # sometimes send sticker before message
                    prob_roll = random.randrange(settings["prob_to_send_skicker"]["from"])
                    if prob_roll <= settings["prob_to_send_skicker"]["first"]:
                        await client.send_file(sender_username, stickers.documents[random.randrange(len(stickers.documents)-1)])

                    # pretend that typing
                    await asyncio.sleep(int(len(answer) / settings['sleep_time_divider']))
                    # reply to message
                    await event.respond(answer)

                    # sometimes send sticker after message
                    if prob_roll >= settings["prob_to_send_skicker"]["from"] - settings["prob_to_send_skicker"]["last"]:
                        await client.send_file(sender_username, stickers.documents[random.randrange(len(stickers.documents)-1)])

    logger.info("Client is running...")
    client.run_until_disconnected()