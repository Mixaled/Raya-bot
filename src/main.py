from telethon.sync import TelegramClient, events
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
from datetime import datetime
from prompt import general_prompt


from queues import request_queue, user_queue


from chaty import completion_local

# get logger and settings
logger = Logger().get_logger()
with open("settings.json", "r") as file:
    settings = json.load(file)
queue = user_queue()
requests = request_queue()

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


async def reply_template(client, answer, sender_username, stickers, reply_func):
    prob_roll = random.randrange(settings["prob_to_send_skicker"]["from"])  

    if prob_roll <= settings["prob_to_send_skicker"]["first"]:
        await asyncio.sleep(random.randrange(1, 3))
        await client.send_file(sender_username, stickers.documents[random.randrange(len(stickers.documents)-1)])
        if settings["local"] != 1:
            #await show_typing(client, sender_username)
            #print("We wait")
            await asyncio.sleep(int(len(answer) / settings['sleep_time_divider']))
        tmp_ret = await reply_func(answer)
        if tmp_ret:
            await hide_typing(client, sender_username)    
    else:
        if settings["local"] != 1:
            #print("We wait")
            #await show_typing(client, sender_username)
            await asyncio.sleep(int(len(answer) / settings['sleep_time_divider']))
        tmp_ret = await reply_func(answer)
        if tmp_ret:
            await hide_typing(client, sender_username)    
        if prob_roll <= settings["prob_to_send_skicker"]["last"]:
            await client.send_file(sender_username, stickers.documents[random.randrange(len(stickers.documents)-1)])


async def simple_reply(client, event, answer, sender_username, stickers):
    await reply_template(client, answer, sender_username, stickers, event.reply)

async def simple_respond(client,event, answer, sender_username, stickers):
    await reply_template(client, answer, sender_username, stickers, event.respond)

async def split2_respond(client, event, answer, sender_username, stickers):
    prob_roll = random.randrange(settings["prob_to_send_skicker"]["from"])  
    # Check if message needs to be split
    if prob_roll <= settings["prob_to_send_skicker"]["first"]:
        await client.send_file(sender_username, stickers.documents[random.randrange(len(stickers.documents)-1)])
    if len(answer) > 10:
        # Find the closest space to the middle of the string
        middle = len(answer) // 2
        index_split = middle

        # Search backward for the nearest space to split on
        for i in range(middle, 0, -1):
            if answer[i] == " ":
                index_split = i
                break
        
        # Split the message at the identified index
        first_part = answer[:index_split].strip()  # First half
        second_part = answer[index_split:].strip()  # Second half

        # Send the second part first
        await event.respond(first_part )
        await show_typing(client, sender_username)
        await asyncio.sleep(random.randrange(2, 4))  # Simulate typing delay
        await event.respond(second_part)
        await hide_typing(client, sender_username)
        if prob_roll <= settings["prob_to_send_skicker"]["last"]:
            await client.send_file(sender_username, stickers.documents[random.randrange(len(stickers.documents)-1)])
    else:

        await event.respond(answer)


async def simple_respond(client,event, answer, sender_username, stickers):
    await reply_template(client, answer, sender_username, stickers, event.respond)
async def mark_as_read(client, event):
    await client(ReadHistoryRequest(
            peer=event.message.chat_id,
            max_id=event.message.id
        ))
    
async def wait_bot(last_message_time, user_id):
    while last_message_time is not None and (datetime.now() - last_message_time).total_seconds() < settings["prompt_sleep_time"]:
        print("Total return")
        await asyncio.sleep(2)  # Properly await the sleep to delay execution
        compare_message_time = await queue.get_last_message_time(user_id)
        if last_message_time != compare_message_time:
            return -1
    print("Time condition passed, continuing...")  # For debugging purposes
    return 0


with TelegramClient(session_name, api_id, api_hash, device_model=settings["device_model"], system_version=settings["system_version"]) as client:
    client.send_message('me', f'Bot started at {datetime.now()}')
    async def answer_to_user(event, user_id, sender_username, stickers, queue: user_queue, message_text):
        if random.randrange(0, 10) <= 3:
            await mark_as_read(client, event)
        last_message_time = await queue.get_last_message_time(user_id)
        #print("last message time: ", last_message_time)
        #print("now time: ", datetime.now())
        #print("last message time: ",(datetime.now() - last_message_time).total_seconds() )

        #if last_message_time == None:
        #    print("Last message time is noone ")
        #    pass
        #elif (datetime.now() - last_message_time).total_seconds() < settings["prompt_sleep_time"]:
        #    print("Total return ")
        #    return None
        res = await wait_bot(last_message_time, user_id)
        if res == -1:
            return None
        jailbreak = await requests.check_jailbreak(user_id, sender_username)
        #await event.respond(jailbreak)
        print(jailbreak)
        logger.info("[JAILBREAK INFO]: "+ str(jailbreak))
        


        await asyncio.sleep(int(len(message_text) / settings['to_read_divider']))


        if len(event.message.message) >= 1:
            answer = await requests.generate_responce(user_id, sender_username, jailbreak)
            print("Answer: ", answer)
            #answer = "I do not like minors I just wanna some cupcake"
            # probably overkill
            if answer is None:
                return None
            event_happen = random_weights([simple_reply, simple_respond, split2_respond], [50, 50, 50])
            if event_happen:
                await mark_as_read(client,event)
                await show_typing(client, sender_username)
                await event_happen(client, event, answer, sender_username, stickers)
            else:
                logger.warning("Some None occurs")

    @client.on(events.NewMessage)
    async def handler(event):
        if event.is_private:
            sender = await event.get_sender()
            sender_username = sender.username or sender.first_name or "Unknown"
            if sender_username not in ban_list:
                message_text = event.message.message
                user_id = event.message.chat_id
                logger.info(f"Received message from {sender_username}: {message_text}")

                # bad that it's loading every time
                sticker_sets = await client(GetAllStickersRequest(0))
                sticker_set = sticker_sets.sets[0]
                stickers = await client(GetStickerSetRequest(
                    stickerset=InputStickerSetID(
                        id=sticker_set.id, access_hash=sticker_set.access_hash
                    ),
                    hash=0
                ))
                if settings["local"] == 1: # local rofls
                    print("local")
                    #initial_messages = [
                    #    {"role": "system", "content": general_prompt},
                    #    {"role": "user", "content": message_text}
                    #]
                    #
                    #await mark_as_read(client,event)
                    #await show_typing(client, sender_username)
                    #resp = completion_local(initial_messages)
                    #event_happen = random_weights([simple_reply, simple_respond], [50, 50])
                    #if event_happen:
                    #    await event_happen(client, event, resp, sender_username, stickers)
                    #await queue.add_message_to_queue(user_id, message_text)
                    if False:
                        # ignore cooldown
                        if settings["ignore_with_cooldown"]:
                            await asyncio.sleep(random.randrange(settings["ignore_time_range"]["start"], settings["ignore_time_range"]["end"]))
                            #print("I am here text:", message_text)
                            await answer_to_user(event, user_id, sender_username, stickers, queue, "")
                    else:
                        #await queue.add_message_to_queue(user_id, message_text)
                        print("MEssage text: ", message_text)
                        await answer_to_user(event, user_id, sender_username, stickers, queue, message_text)

                else:
                    print("non local")
                    await queue.add_message_to_queue(user_id, message_text)
                    if random.randrange(settings["prob_to_ignore"]["from"]) < settings["prob_to_ignore"]["prob"]:
                        
                        # ignore cooldown
                        if settings["ignore_with_cooldown"]:
                            await asyncio.sleep(random.randrange(settings["ignore_time_range"]["start"], settings["ignore_time_range"]["end"]))
                            #print("I am here text:", message_text)
                            await answer_to_user(event, user_id, sender_username, stickers, queue, "")
                    else:
                        #await queue.add_message_to_queue(user_id, message_text)
                        print("MEssage text:", message_text)
                        await answer_to_user(event, user_id, sender_username, stickers, queue, message_text)

    logger.info("Client is running...")

    
    client.run_until_disconnected()