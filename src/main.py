from telethon.sync import TelegramClient, events
from chaty import *
import asyncio
import random
from telethon.tl.functions.messages import GetAllStickersRequest
from telethon.tl.functions.messages import GetStickerSetRequest
from telethon.tl.types import InputStickerSetID
from keys import session_name, api_id, api_hash



with TelegramClient(session_name, api_id, api_hash, device_model='iPhone 13 Pro Max',system_version="4.16.30-vxhello") as client:
    client.send_message('me', 'Hi')
    ban_list = ["Lunitarik", "Tywyrty", "suffereds0ul","leomatchbot"]
    global_chats = {}
    
    @client.on(events.NewMessage)
    async def handler(event):
        global global_chats
        if event.is_private:
            sender = await event.get_sender()
            sender_username = sender.username or sender.first_name or "Unknown"
            message_text = event.message.message
            print(f"Received message from {sender_username}: {message_text}")
            
            #if sender_username == "slepky":
            sticker_sets = await client(GetAllStickersRequest(0))

            sticker_set = sticker_sets.sets[0]

            stickers = await client(GetStickerSetRequest(
            stickerset=InputStickerSetID(
                id=sticker_set.id, access_hash=sticker_set.access_hash
            ),
            hash=0
            ))
            #await client.send_file('me', stickers.documents[0])

            if len(event.message.message) >= 1 and sender_username not in ban_list:
                print("I am here")
                bot = ChatInteraction(sender_username, global_chats)
                answer, global_chats = bot.response(message_text)
                answer = answer['content']
                print("Answer: ", answer)
                rand = random.randrange(30)
                if rand < 12:    
                    #TRY
                    #await time.sleep(int(len(answer)/5))
                    await asyncio.sleep(int(len(answer) / 4))
                    await event.reply(answer)
                    #res = create_voice(answer)
                    #with open('output.mp3', 'wb') as f:
                    #    for chunk in res.iter_content(chunk_size=CHUNK_SIZE):
                    #        if chunk:
                    #            f.write(chunk)
                    #await client.send_file(sender_username, 'output.mp3', voice_note=True) 
                    if rand <= 6:
                        await client.send_file(sender_username, stickers.documents[random.randrange(len(stickers.documents)-1)])
                else:
                    #TRY
                    #await time.sleep(int(len(answer)/5))
                    await asyncio.sleep(int(len(answer) / 4))
                    await event.respond(answer)
                    if rand >= 24:
                        await client.send_file(sender_username, stickers.documents[random.randrange(len(stickers.documents)-1)])
    print("Client is running...")
    client.run_until_disconnected()