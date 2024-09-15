"""
module with queues to communicate with model and user messages
"""

import os
import json
from typing import Callable
from datetime import datetime
import asyncio, nest_asyncio
import aiosqlite

from logger import Logger, SingletonType
from chaty import response, jailbreak_test_local, jailbreak_response_local, completion_local
from prompt import general_prompt

logger = Logger().get_logger()

with open("./settings.json", "r", encoding="utf-8") as file:
    settings = json.load(file)

def simple_async_to_sync(awaitable: Callable):
    """
    func to run async functions from sync code
    """
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(awaitable)

def async_to_sync(future, as_task=True):
    """
    A better implementation of `asyncio.run`.

    :param future: A future or task or call of an async method.
    :param as_task: Forces the future to be scheduled as task (needed for e.g. aiohttp).
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:  # no event loop running:
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(loop.create_task(future))
    else:
        nest_asyncio.apply(loop)
        return loop.run_until_complete(loop.create_task(future))


class sql_connection():
    """simple class to sequre sql connection to be closed"""     
    def __init__(self, db_name=settings['user_db_name']):
        self.sql = aiosqlite.Connection
        async_to_sync(self.connect(db_name))
    
    async def connect(self, db_name=settings['user_db_name']):
        if not os.path.isfile(db_name):
            self.sql = await aiosqlite.connect(db_name)
            await self.sql.executescript(f"""CREATE TABLE user_data (
                        messageId INTEGER PRIMARY KEY,
                        userId INTEGER NOT NULL,
                        userMessage TEXT NOT NULL,
                        messageTimestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        holding bool default false
                    );
                    CREATE TABLE user_timers (
                        userId INTEGER PRIMARY KEY,
                        userTimer INTEGER DEFAULT {settings["prompt_sleep_time"]}
                    );
                    CREATE TABLE chats_history (
                        messageId INTEGER PRIMARY KEY,
                        userId INTEGER NOT NULL,
                        senderName VARCHAR(255) NOT NULL,
                        messageText TEXT NOT NULL,
                        messageTimestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
            )  
            await self.sql.commit()
            logger.debug("commited")
        self.sql = await aiosqlite.connect(db_name)
        logger.info("sql connection opened")

    async def __del__(self):
        await self.sql.close()
        logger.info("sql connection closed")    


class user_queue(metaclass=SingletonType): # TOTHINK: shell it be singleton? not shure
    def __init__(self, db_name=settings['user_db_name']): 
        async_to_sync(self.connect_sql(db_name))

    # init can't be async, so we need to connect each class
    async def connect_sql(self, db_name=settings['user_db_name']):
        """connect sql method"""
        self.sql = sql_connection(db_name)

    async def count(self, user_id: int) -> int:
        lines = await self.sql.sql.execute_fetchall(f"SELECT userId FROM user_data WHERE userId={user_id}")
        return len(lines)

    async def pop_message_from_queue(self, user_id: int) -> str:
        messages = await self.sql.sql.execute_fetchall(f"SELECT userMessage from user_data WHERE userId={user_id}")
        await self.sql.sql.execute(f"DELETE FROM user_data WHERE userId={user_id}")
        await self.sql.sql.commit()
        return '\n'.join([x[0] for x in messages])
    
    async def see_message_from_queue(self, user_id: int) -> str:
        messages = await self.sql.sql.execute_fetchall(f"SELECT userMessage from user_data WHERE userId={user_id}")
        return '\n'.join([x[0] for x in messages])
    


    async def add_message_to_queue(self, user_id: int, message: str) -> bool:
        await self.sql.sql.execute("INSERT INTO user_data (userId, userMessage, messageTimestamp, holding) VALUES(?, ?, ?, ?)", (user_id, message, datetime.now(), True))
        await self.sql.sql.execute("INSERT OR REPLACE INTO user_timers(userId, userTimer) VALUES(?, ?);", (user_id, 10))
        await self.sql.sql.commit()
        return True

    async def get_last_message_time(self, user_id: int) -> datetime:
        timestamp = await self.sql.sql.execute_fetchall(f"SELECT userId, MAX(messageTimestamp) as lastTime FROM user_data WHERE userId={user_id} GROUP BY userId")
        #timestamp = await self.sql.sql.execute_fetchall(f"SELECT userId, userTimer as lastTime FROM user_timers WHERE userId={user_id} GROUP BY userId")
        logger.info("Time: ", timestamp)
        if len(timestamp) == 0:
            return None
        return datetime.strptime(timestamp[0][1], '%Y-%m-%d %H:%M:%S.%f')
    

class request_queue(metaclass=SingletonType):
    """queue to add new user messages to messages pull to answer"""
    def __init__(self, db_name=settings['user_db_name']):
        async_to_sync(self.connect(db_name))

    async def connect(self, db_name=settings['user_db_name']):
        """init can't be async, so we need to connect each class"""
        self.user_queue = user_queue(db_name)
        self.sql = sql_connection(db_name)
        
    async def get_chat_history(self, user_id) -> list:
        all_messages = await self.sql.sql.execute_fetchall(f"SELECT senderName, messageText FROM chats_history WHERE userId = {user_id} ORDER BY messageTimestamp")
        messages = []
        for line in all_messages:
            messages.append({
                "role": line[0], "content": line[1]
            })
        return messages
    
    async def check_holding(self, user_id: int) -> str:
        query = "SELECT holding FROM user_data WHERE userId = ?"
        messages = await self.sql.sql.execute_fetchall(query, (user_id,))
        return '\n'.join([str(x[0]) for x in messages])
    
    async def unhold(self, user_id: int) -> None:
        query = "update user_data SET holding = false WHERE userId = ?"
        await self.sql.sql.execute(query, (user_id,))
        await self.sql.sql.commit()

    async def check_jailbreak(self, user_id: int, user_name: str):
        user_message = await self.user_queue.see_message_from_queue(user_id)
        res = jailbreak_test_local(user_message)
        if "1" in res:
            return 1
        elif "2" in res:
            return 2
        elif "3" in res:
            return 3
        elif "0" in res:
            return 0
        else:
            logger.error("Wierd message: ", user_message + " respond: " + res)
            return 0
        


    async def get_len_history(self, user_id) -> list:
        alo = await self.get_chat_history(user_id)
        return len(alo)
    
    async def put_messages_to_history(self, user_id: int, user_name: str, user_message: str="", model_message: str="") -> bool:
        if user_message != "":
            if await self.get_len_history(user_id) == 0: # apparently, it's not good to check count every time
                logger.debug(f"Creating new inst: userId={user_id}, senderName='system', messageText={general_prompt}")
                await self.sql.sql.execute(f'INSERT INTO chats_history(userId, senderName, messageText) VALUES({user_id}, "system", "{general_prompt}")')
            logger.debug(f"Inserting into chats_history: userId={user_id}, senderName='user', messageText={user_message}")
            await self.sql.sql.execute(f'INSERT INTO chats_history(userId, senderName, messageText) VALUES({user_id}, "user", "{user_message}")')
        if model_message != "":  
            logger.debug(f"Inserting into chats_history: userId={user_id}, senderName='assistant', messageText={model_message}")
            await self.sql.sql.execute(f'INSERT INTO chats_history(userId, senderName, messageText) VALUES({user_id}, "assistant", "{model_message}")')
        await self.sql.sql.commit()
        
    async def get_timer(self, user_id: int) -> int:
        timer = await self.sql.sql.execute_fetchall(f"SELECT userTimer FROM user_timers WHERE userId = {user_id}")
        
        if len(timer) == 0:
            return [(0,)]
        return timer[0][0]
    
    async def set_value_timer(self, user_id: int, timer_value) -> bool:
        await self.sql.sql.execute("INSERT OR REPLACE INTO user_timers(userId, userTimer) VALUES(?, ?);", (user_id, timer_value))
        await self.sql.sql.commit()
        return True
    


    async def generate_responce(self, user_id: int, user_name: str, jailbreak_status: int) -> str:
        """
        always use this method to generate responce for user,
        never call model itself!!
        """
        # await quick messages
        #while(await self.get_timer(user_id) != 0):
        #    await self.set_value_timer(user_id, 0)
        #    await asyncio.sleep(settings["prompt_sleep_time"])
        if jailbreak_status == 1:
            user_message = await self.user_queue.pop_message_from_queue(user_id)
            answer = jailbreak_response_local(user_message)
            return answer
        else:
            user_message = await self.user_queue.pop_message_from_queue(user_id)
            initial_messages = [
                        {"role": "system", "content": general_prompt},
                        {"role": "user", "content": user_message}
                    ]
        resp = completion_local(initial_messages)
        return resp