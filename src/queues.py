import os, json
from logger import Logger, SingletonType
import sqlite3
import aiosqlite, asyncio
from chaty import ChatInteraction
from asyncio import sleep
from typing import Callable

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
                        userId INTEGER NOT NULL,
                        userMessage TEXT NOT NULL
                    );
                    CREATE TABLE user_timers (
                        userId INTEGER PRIMARY KEY,
                        userTimer INTEGER DEFAULT {settings["prompt_sleep_time"]}
                    );"""
            )  
            await self.sql.commit()
            logger.debug("commited")
        self.sql = await aiosqlite.connect(db_name)
        logger.info("sql connection opened")

    async def __del__(self):
        await self.sql.close()
        logger.info("sql connection closed")    


class user_queue(metaclass=SingletonType):
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


class request_queue(metaclass=SingletonType):
    def __init__(self, global_chats:list = [],queue: user_queue = user_queue(), db_name=settings['user_db_name']):
        async_to_sync(self.connect(global_chats, queue, db_name))
        
    # init can't be async, so we need to connect each class
    async def connect(self, global_chats:list = [],queue: user_queue = user_queue(), db_name=settings['user_db_name']):
        self.user_queue = user_queue(db_name)
        self.sql = sql_connection(db_name)
        self.chat_bot = ChatInteraction(global_chats)
        
    async def get_timer(self, user_id: int) -> int:
        timer = await self.sql.sql.execute_fetchall(f"SELECT userTimer from user_timers WHERE userId = {user_id}")
        return timer[0][0]
    
    async def set_value_timer(self, user_id: int, timer_value) -> bool:
        await self.sql.sql.execute("INSERT OR REPLACE INTO user_timers(userId, userTimer) VALUES(?, ?);", (user_id, timer_value))
        await self.sql.commit()
        return True

    async def generate_request(self, user_id: int, user_name: str) -> str | None:
        """
        always use this method to generate responce for user,
        never call model itself!!
        """
        while(self.get_timer(user_id) != 0):
            # get responce from model
            self.set_value_timer(user_id, 0)
            await sleep(settings["prompt_sleep_time"])
        user_messages = self.user_queue.pop_message_from_queue(user_id)
        if user_messages is None:
            return None
        answer, global_chats = self.chat_bot.response(user_name, user_messages)
        return answer

