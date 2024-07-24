__version__ = "1.0.0"

import requests
import json
import time
import re
from keys import api_gpt, eleven_labs, voice_id
from logger import Logger
from prompt import general_prompt

MODEL = "openai/gpt-4o-mini-2024-07-18"

MODELS_LIST = ["cognitivecomputations/dolphin-llama-3-70b", "meta-llama/llama-3-8b-instruct", "openai/gpt-4o-mini-2024-07-18"]

logger = Logger.__call__().get_logger()


def split_sentences(response):
    if len(response) < 150 :
        split_into_sentences = []
        split_into_sentences = re.split(r',', response)
    else:
        split_into_sentences = []
        split_into_sentences = re.split(r'\.\s|\n\n', response)
    return split_into_sentences

def completion(messages, api_key=api_gpt, proxy=''):
    url = "https://openrouter.ai/api/v1/chat/completions"
    if proxy is not None and proxy != '': url = proxy
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": 30
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    print(response)

    if response.status_code == 200 or response.status_code == 201:
        time.sleep(1)
        try:
            completion_text = response.json()['choices'][0]['message']['content']
            logger.info(f"completion_text: {completion_text}")
        except (KeyError, IndexError):
            raise Exception(f"Unexpected response structure: {response.text}")

        return messages
    elif response.status_code == 500 or response.status_code == 429:
        raise Exception(f"Error: {response.status_code}, {response.text}")
        # completion(messages, api_key)
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")
    #end


def replace_weird_symbols(text):
    symbols_to_remove = '@#^()_~[]{}|\\<>/'
    for symbol in symbols_to_remove:
        text = text.replace(symbol, ' ')

    return text

class ChatInteraction:
    def __init__(self, global_chats: list):
        self.global_chats = global_chats

    def response(self, user_name: str, global_chats: list, user_input: str):
        if self.user_name not in self.global_chats:
            global_chats[user_name] = [
                {
                    "role": "system", 
                    "content": general_prompt
                },
        ]
        # add memory about dialog
        # cause of re-initialisation it wasn't here, 
        # even though idea was right
        self.global_chats[self.user_name].append({"role": "user", "content": user_input})
        self.global_chats[self.user_name].append({"role": "user", "content": user_input})
        comp = completion(self.global_chats[self.user_name])
        logger.info(f"COMP: {self.global_chats[self.user_name]}")
        response = comp[-1]
        self.global_chats[self.user_name].append({'role': 'assistant', 'content': response})
        
        return response, self.global_chats


#await client.send_file(chat, file, voice_note=True)  
CHUNK_SIZE = 1024
def create_voice(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {
      "Accept": "audio/mpeg",
      "Content-Type": "application/json",
      "xi-api-key": eleven_labs
    }

    data = {
      "text": text,
      "voice_settings": {
        "stability": 0.5,
        "similarity_boost": 0.5
      }
    }

    response = requests.post(url, json=data, headers=headers)
    return response