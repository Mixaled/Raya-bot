from telethon.sync import TelegramClient, events
from chaty import *
import asyncio
import random
from telethon.tl.functions.messages import GetAllStickersRequest
from telethon.tl.functions.messages import GetStickerSetRequest
from telethon import functions, types
from telethon.tl.types import InputStickerSetID
from telethon.tl.functions.messages import ReadHistoryRequest
from keys import session_name, api_id, api_hash
from logger import Logger
from keys import ban_list
import json
from message_queue import user_queue
from datetime import datetime

# get logger and settings
logger = Logger().get_logger()
with open("settings.json", "r") as file:
    settings = json.load(file)
queue = user_queue()


def random_weights(values, weights): 
    total = sum(weights)
    rand = random.uniform(0, total)
    cursor = 0

    for value, weight in zip(values, weights):
        cursor += weight
        if cursor >= rand:
            return value
    return None

def sanitize_message(message):
    return message.encode('ascii', 'ignore').decode('ascii')


async def show_typing(client, sender_username):
        await client(functions.messages.SetTypingRequest(
            peer=sender_username,
            action=types.SendMessageTypingAction()
        ))

async def hide_typing(client, sender_username):
        await client(functions.messages.SetTypingRequest(
            peer=sender_username,
            action=types.SendMessageCancelAction()
        ))  


async def reply_template(client, answer, sender_username, stickers, type_of):
    prob_roll = random.randrange(settings["prob_to_send_skicker"]["from"])
    #print("Prob roll:", prob_roll)
    #print("Set roll:", settings["prob_to_send_skicker"]["first"])
    
    if prob_roll <= settings["prob_to_send_skicker"]["first"]:
        #print("Sticker send")
        await asyncio.sleep(random.randrange(1, 3))
        await client.send_file(sender_username, stickers.documents[random.randrange(len(stickers.documents)-1)])
        await show_typing(client, sender_username)
        await asyncio.sleep(int(len(answer) / settings['sleep_time_divider']))
        await type_of(answer)
        await hide_typing(client, sender_username)    
    else:
        
        await show_typing(client, sender_username)
        await asyncio.sleep(int(len(answer) / settings['sleep_time_divider']))
        await type_of(answer)
        await hide_typing(client, sender_username) 
        if prob_roll <= settings["prob_to_send_skicker"]["last"]:
            #print("Sticker send")
            await client.send_file(sender_username, stickers.documents[random.randrange(len(stickers.documents)-1)])


async def simple_reply(client, event, answer, sender_username, stickers):
    await reply_template(client, answer, sender_username, stickers, event.reply)

async def simple_respond(client,event, answer, sender_username, stickers):
    await reply_template(client, answer, sender_username, stickers, event.respond)


async def mark_as_read(client, event):
    await client(ReadHistoryRequest(
            peer=event.message.chat_id,
            max_id=event.message.id
        ))




with TelegramClient(session_name, api_id, api_hash, device_model=settings["device_model"], system_version=settings["system_version"]) as client:
    client.send_message('me', 'Hi')
    global_chats = {}

    async def answer_to_user(event, user_id, sender_username, stickers, queue, message_text):
        global global_chats
        message_text = queue.pop_message_from_queue(user_id) + '\n' + message_text
        await mark_as_read(client, event)
        await asyncio.sleep(int(len(message_text) / settings['to_read_divider']))
        if len(event.message.message) >= 1 and sender_username not in ban_list:
            bot = ChatInteraction(sender_username, global_chats)
            answer, global_chats = bot.response(message_text)
            logger.info(f"Answer: {answer}")
            event_happen = random_weights([simple_reply, simple_respond], [50, 50])
            if event_happen:
                await event_happen(client, event, answer['content'], sender_username, stickers)
            else:
                print("Some None occurs")

    @client.on(events.NewMessage)
    async def handler(event):
        global global_chats
        if event.is_private:
            sender = await event.get_sender()
            sender_username = sender.username or sender.first_name or "Unknown"
            message_text = event.message.message
            user_id = event.message.chat_id
            logger.info(f"Received message from {sender_username}: {message_text}")

            sticker_sets = await client(GetAllStickersRequest(0))
            sticker_set = sticker_sets.sets[0]
            stickers = await client(GetStickerSetRequest(
                stickerset=InputStickerSetID(
                    id=sticker_set.id, access_hash=sticker_set.access_hash
                ),
                hash=0
            ))

            #if random.randrange(settings["prob_to_ignore"]["from"]) < settings["prob_to_ignore"]["prob"]:
            if random.randrange(settings["prob_to_ignore"]["from"]) < settings["prob_to_ignore"]["prob"]:
                print("the user is ignored and goes into cooldown")
                queue.add_message_to_queue(user_id, message_text)
                # ignore cooldown
                asyncio.sleep(random.randrange(settings["ignore_range"]["start"], settings["ignore_range"]["end"]))
                await answer_to_user(event, user_id, sender_username, stickers, queue,message_text)
            else:
                await answer_to_user(event, user_id, sender_username, stickers, queue,message_text)

                    # sometimes send sticker before message
                    #prob_roll = random.randrange(settings["prob_to_send_skicker"]["from"])
                    #if prob_roll <= settings["prob_to_send_skicker"]["first"]:
                    #    await client.send_file(sender_username, stickers.documents[random.randrange(len(stickers.documents)-1)])
                    ## pretend that typing
                    #await asyncio.sleep(int(len(answer) / settings['sleep_time_divider']))
                    ## reply to message
                    #await event.respond(answer)
                    ## sometimes send sticker after message
                    #if prob_roll >= settings["prob_to_send_skicker"]["from"] - settings["prob_to_send_skicker"]["last"]:
                    #    await client.send_file(sender_username, stickers.documents[random.randrange(len(stickers.documents)-1)])

    logger.info("Client is running...")
    client.run_until_disconnected()