import os
from logger import Logger, SingletonType
import sqlite3
import aiosqlite
from chaty import ChatInteraction
from asyncio import sleep

logger = Logger().get_logger()

with open("settings.json", "r") as file:
    settings = json.load(file)

# simple class to sequre sql connection to be closed
class sql_connection():
    async def __init__(self, db_name=settings['user_db_name']):
        self.sql = aiosqlite.Connection
        if not os.path.isfile(db_name):
            self.sql = await aiosqlite.connect(db_name)
            await self.sql.execute("""CREATE TABLE user_data (
                        userId INTEGER PRIMARY KEY,
                        userMessage TEXT NOT NULL,
                    };
                    CREATE TABLE user_timers (
                        userId INTEGER PRIMARY KEY,
                        userTimer INTEGER DEFAULT 10,
                    };"""
            )  
            await self.sql.commit()
        else:
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
    async def __init__(self):
        self.sql = await sql_connection()

    async def count(self, user_id: int) -> int:
        lines = await self.sql.sql.execute_fetchall("SELECT userId FROM user_data WHERE userId = VALUES(?)", (user_id))
        return len(lines)

    async def pop_message_from_queue(self, user_id: int) -> str:
        messages = await self.sql.sql.execute_fetchall("SELECT userMessage from user_data WHERE userId = VALUES(?)", (user_id))
        self.sql.sql.execute("DELETE FROM user_data WHERE userId")
        await self.sql.sql.commit()
        return '\n'.join(messages)

    async def add_message_to_queue(self, user_id: int, message: str) -> bool:
        await self.sql.sql.execute("INSERT INTO user_data (userId, userMessage) VALUES(?, ?)", (user_id, message))
        await self.sql.sql.execute("INSERT OR REPLACE INTO user_timers(userId, userTimer) VALUES(?, ?);", (user_id, 10))
        await self.sql.connection.commit()
        return True


class request_queue(metaclass=SingletonType):
    def __init__(self, global_chats:list = [],queue: user_queue = user_queue()):
        self.user_queue = queue
        self.sql = sql_connection()
        self.chat_bot = ChatInteraction(global_chats)
            #         bot = ChatInteraction(sender_username, global_chats)
            # answer, global_chats = bot.response(message_text)
            # logger.info(f"Answer: {answer}")

    async def generate_request(self, user_id: int, user_name: str):
        while(self.user_queue.get_timer(user_id) != 0):
            # get responce from model
            answer, global_chats = self.chat_bot.response(user_name, self.user_queue.pop_message_from_queue(user_id))
            self.sql.set_value_timer(user_id, 0)
            sleep(settings["prompt_sleep_time"])

    # короче, 
    # пока селект таймер по юзеру не равен нулю
        # попаем все сообщения от пользователя, 
        # выставляем таймер в 0
        # ждем 10 секунд 
    # генерируем реквест на получившемся тексте, возвращаем

