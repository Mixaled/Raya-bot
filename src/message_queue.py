import os, json
from logger import Logger

logger = Logger().get_logger()

# get past user info
class user_queue():
    def __init__(self):
        if os.path.isfile("./user_info.json"):
            with open("./user_info.json", "r", encoding='utf-8') as file:
                self.user_info = json.load(file)
        else:
            self.user_info = {"indo_about": {}, "message_queue": {"example_id": ["example_message"]}}

    def pop_message_from_queue(self, user_id: int) -> str:
        user_id_str = str(user_id)
        if user_id_str in self.user_info['message_queue']:
            queue = self.user_info['message_queue'][user_id_str]
            self.user_info['message_queue'][user_id_str] = []
            try:
                with open("./user_info.json", "w", encoding='utf-8') as file:
                    json.dump(self.user_info, file, ensure_ascii=False, indent=4)
            except Exception as e:
                logger.debug(f'Error writing to file: {e}')
                logger.debug('will try next time ¯\\_(ツ)_/¯')
            return '\n'.join(queue)
        return ''

    def add_message_to_queue(self, user_id: int, message: str) -> bool:
        user_id_str = str(user_id)
        if user_id_str not in self.user_info['message_queue']:
            self.user_info['message_queue'][user_id_str] = []
        self.user_info['message_queue'][user_id_str].append(message)
        try:
            with open("./user_info.json", "w", encoding='utf-8') as file:
                json.dump(self.user_info, file, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.debug(f'Error writing to file: {e}')
            logger.debug('will try next time ¯\\_(ツ)_/¯')
        return True
