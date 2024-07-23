import os
from logger import Logger, SingletonType
import sqlite3

logger = Logger().get_logger()

with open("settings.json", "r") as file:
    settings = json.load(file)

# simple class to sequre sql connection to be closed
class sql_connection():
    def __init__(self, db_name=settings['user_db_name']):
        if not os.path.isfile(db_name):
            self.connection = sqlite3.connect()
            self.sql = self.connection.cursor()
            self.sql.execute("""CREATE TABLE user_data (
                        userId INTEGER PRIMARY KEY,
                        userMessage TEXT NOT NULL,
                    };
                    CREATE TABLE user_timers (
                        userId INTEGER PRIMARY KEY,
                        userTimer INTEGER DEFAULT 10,
                    };"""
            )  
        else:
            self.connection = sqlite3.connect(db_name)
            self.cursor = self.connection.cursor()
        logger.info("sql connection opened")

    def __del__(self):
        self.connection.close()
        logger.info("sql connection closed")
    


class user_queue(metaclass=SingletonType):
    def __init__(self):
        self.sql = sql_connection()

    def count(self, user_id: int) -> int:
        self.sql.sql.execute("SELECT userId FROM user_data WHERE userId = VALUES(?)", (user_id))
        return len(self.sql.sql.fetchall())

    def pop_message_from_queue(self, user_id: int) -> str:
        self.sql.sql.execute("SELECT userMessage from user_data WHERE userId = VALUES(?)", (user_id))
        messages = self.sql.sql.fetchall()
        self.sql.sql.execute("DELETE FROM user_data WHERE userId")
        return '\n'.join(messages)

    def add_message_to_queue(self, user_id: int, message: str) -> bool:
        self.sql.sql.execute("INSERT INTO user_data (userId, userMessage) VALUES(?, ?)", (user_id, message))
        self.sql.sql.execute("INSERT OR REPLACE INTO user_timers(userId, userTimer) VALUES(?, ?);", (user_id, 10))
        self.sql.connection.commit()
        return True


class request_queue(metaclass=SingletonType):
    def __init__(self, queue: user_queue = user_queue()):
        self.user_queue = queue
        self.sql = sql_connection()

    async def generate_request(self, user_id):
        pass
    # короче, 
    # пока селект таймер по юзеру не равен нулю
        # попаем все сообщения от пользователя, 
        # выставляем таймер в 0
        # ждем 10 секунд 
    # генерируем реквест на получившемся тексте, возвращаем

