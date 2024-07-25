import os, json
from logger import Logger, SingletonType
import sqlite3
import aiosqlite, asyncio
from chaty import response
from asyncio import sleep
from typing import Callable
from datetime import datetime

logger = Logger().get_logger()

with open("./settings.json", "r") as file:
    settings = json.load(file)


def async_to_sync(awaitable: Callable):
    """
    func to run async functions from sync code
    """
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(awaitable)

# simple class to sequre sql connection to be closed
class sql_connection():     
    def __init__(self, db_name=settings['user_db_name']):
        async_to_sync(self.connect(db_name=settings['user_db_name']))
    
    async def connect(self, db_name=settings['user_db_name']):
        self.sql = aiosqlite.Connection
        if not os.path.isfile(db_name):
            self.sql = await aiosqlite.connect(db_name)
            await self.sql.executescript(f"""CREATE TABLE user_data (
                        messageId INTEGER PRIMARY KEY AUTO_INCREMENT,
                        userId INTEGER NOT NULL,
                        userMessage TEXT NOT NULL,
                        messageTimestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE user_timers (
                        userId INTEGER PRIMARY KEY,
                        userTimer INTEGER DEFAULT {settings["prompt_sleep_time"]}
                    );
                    CREATE TABLE chats_history (
                        messageId INTEGER PRIMARY KEY AUTO_INCREMENT,
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
        async_to_sync(self.connect_sql(db_name=settings['user_db_name']))

    # init can't be async, so we need to connect each class
    async def connect_sql(self, db_name=settings['user_db_name']):
        self.sql = sql_connection(db_name=settings['user_db_name'])

    async def count(self, user_id: int) -> int:
        lines = await self.sql.sql.execute_fetchall(f"SELECT userId FROM user_data WHERE userId={user_id}")
        return len(lines)

    async def pop_message_from_queue(self, user_id: int) -> str:
        messages = await self.sql.sql.execute_fetchall(f"SELECT userMessage from user_data WHERE userId={user_id}")
        await self.sql.sql.execute(f"DELETE FROM user_data WHERE userId={user_id}")
        await self.sql.sql.commit()
        return '\n'.join([x[0] for x in messages])

    async def add_message_to_queue(self, user_id: int, message: str) -> bool:
        await self.sql.sql.execute("INSERT INTO user_data (userId, userMessage) VALUES(?, ?)", (user_id, message))
        await self.sql.sql.execute("INSERT OR REPLACE INTO user_timers(userId, userTimer) VALUES(?, ?);", (user_id, 10))
        await self.sql.sql.commit()
        return True

    async def get_last_message_time(self, user_id: int) -> datetime:
        timestamp = await self.sql.sql.execute_fetchall(f"SELECT userId, MAX(messageTimestamp) as lastTime FROM user_data WHERE userId={user_id} GROUP BY userId")
        return datetime.strftime(timestamp, '%Y-%m-%d %H:%M:%S')

class request_queue(metaclass=SingletonType):
    def __init__(self, queue: user_queue = user_queue(), db_name=settings['user_db_name']):
        async_to_sync(self.connect(queue, db_name))

    # init can't be async, so we need to connect each class
    async def connect(self, queue: user_queue = user_queue(), db_name=settings['user_db_name']):
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
    
    async def put_messages_to_history(self, user_id: int, user_name: str, user_message: str="", model_message: str="") -> bool:
        if user_message != "":
            await self.sql.sql.execute("INSERT INTO chats_history(userId, senderName, messageText) VALUES(?, ?, ?)", (user_id, user_name, user_message))
        if model_message != "":  
            await self.sql.sql.execute("INSERT INTO chats_history(userId, senderName, messageText) VALUES(?, ?, ?)", (user_id, "assistant", model_message))
        await self.sql.sql.commit()
        
    async def get_timer(self, user_id: int) -> int:
        timer = await self.sql.sql.execute_fetchall(f"SELECT userTimer FROM user_timers WHERE userId = {user_id}")
        return timer[0][0]
    
    async def set_value_timer(self, user_id: int, timer_value) -> bool:
        await self.sql.sql.execute("INSERT OR REPLACE INTO user_timers(userId, userTimer) VALUES(?, ?);", (user_id, timer_value))
        await self.sql.sql.commit()
        return True

    async def generate_responce(self, user_id: int, user_name: str) -> str | None:
        """
        always use this method to generate responce for user,
        never call model itself!!
        """
        # await quick messages
        while(self.get_timer(user_id) != 0):
            self.set_value_timer(user_id, 0)
            await sleep(settings["prompt_sleep_time"])
        # return None if message is already processing
        if await self.user_queue.pop_message_from_queue(user_id) is None:
            return None
        # get new message
        user_message = await self.user_queue.pop_message_from_queue(user_id)
        # add new user message to context
        self.put_messages_to_history(user_id, user_name, user_message=user_message)
        answer = response(user_name, self.get_chat_history(user_id))
        # add new model message to context
        await self.put_messages_to_history(user_id, user_name, model_message=answer)
        return answer

