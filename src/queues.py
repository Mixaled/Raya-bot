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

# simple class to sequre sql connection to be closed
class sql_connection():        
    # init can't be async, so we need to connect each class
    async def connect(self, db_name=settings['user_db_name']):
        self.sql = aiosqlite.Connection
        if not os.path.isfile(db_name):
            self.sql = await aiosqlite.connect(db_name)
            await self.sql.executescript("""CREATE TABLE user_data (
                        userId INTEGER NOT NULL,
                        userMessage TEXT NOT NULL
                    );
                    CREATE TABLE user_timers (
                        userId INTEGER PRIMARY KEY,
                        userTimer INTEGER DEFAULT 10
                    );"""
            )  
            await self.sql.commit()
            logger.debug("commited")
        self.sql = await aiosqlite.connect(db_name)
        logger.info("sql connection opened")

    
    async def get_timer(self, user_id: int) -> int:
        timer = await self.sql.execute_fetchall("SELECT userTimer from user_timers WHERE userId = VALUES(?)", (user_id))
        return timer[0]
    
    async def set_value_timer(self, user_id: int, timer_value) -> bool:
        await self.sql.execute("INSERT OR REPLACE INTO user_timers(userId, userTimer) VALUES(?, ?);", (user_id, timer_value))
        await self.sql.commit()
        return True

    async def __del__(self):
        await self.sql.close()
        logger.info("sql connection closed")    


class user_queue(metaclass=SingletonType):
    # init can't be async, so we need to connect each class
    async def connect_sql(self):
        self.sql = sql_connection()
        await self.sql.connect()

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
    # init can't be async, so we need to connect each class
    async def connect(self, global_chats:list = [],queue: user_queue = user_queue()):
        self.user_queue = queue
        await self.user_queue.connect_sql()
        self.sql = sql_connection()
        await self.sql.connect()
        self.chat_bot = ChatInteraction(global_chats)

    async def generate_request(self, user_id: int, user_name: str):
        while(self.user_queue.get_timer(user_id) != 0):
            # get responce from model
            self.sql.set_value_timer(user_id, 0)
            sleep(settings["prompt_sleep_time"])
        answer, global_chats = self.chat_bot.response(user_name, self.user_queue.pop_message_from_queue(user_id))


def async_to_sync(awaitable: Callable):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(awaitable)