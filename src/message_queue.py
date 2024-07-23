import os, json
from logger import Logger

logger = Logger.__call__.get_logger()

# get past user info
class user_queue():
    def __init__(self):
        if os.path.isfile("./user_info.json"):
            with open("./user_info.json") as file:
                self.user_info = json.loads(file)
        else:
            self.user_info = {"indo_about": {}, "message_queue": {"example_id": ["example_message"]}}

    def pop_message_from_queue(self, user_id: int) -> str:
        if str(user_id) in self.user_info['message_queue']:
            queue = self.user_info['message_queue'][str(user_id)]
            self.user_info['message_queue'][str(user_id)] = []
            try:
                with open("./user_info.json") as file:
                    json.dump(self.user_info, file)
            except:
                logger.debug('will try next time ¯\_(ツ)_/¯')
            return '\n'.join(queue)
        return ''

    def add_message_to_queue(self, user_id: int, message: str) -> bool:
        if not str(user_id) in self.user_info['message_queue']:
            self.user_info['message_queue'][str(user_id)] = []    
        self.user_info['message_queue'][str(user_id)].append(message)
        try:
            with open("./user_info.json") as file:
                json.dump(self.user_info, file)
        except:
            logger.debug('will try next time ¯\_(ツ)_/¯')
        return True
