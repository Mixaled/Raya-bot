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

logger = Logger().get_logger()


with open("./settings.json", "r", encoding="utf-8") as file:
    settings = json.load(file)

# isn't used
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
    logger.debug(response)

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
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")

def completion_local(messages):
    url = "http://127.0.0.1:8080/completion"
    headers = {
        "Content-Type": "application/json"
    }
    
    # Construct the prompt from the messages
    prompt = ""
    for message in messages:
        role = message['role'].capitalize()
        content = message['content']
        prompt += f"{role}: {content}\n"
    prompt += "Llama:"

    data = {
        "stream": True,
        "n_predict": 300,
        "temperature": 0.7,
        "stop": ["</s>", "Raya:", "User:"],
        "repeat_last_n": 256,
        "repeat_penalty": 1.18,
        "penalize_nl": False,
        "top_k": 40,
        "top_p": 0.95,
        "min_p": 0.05,
        "tfs_z": 1,
        "typical_p": 1,
        "presence_penalty": 0,
        "frequency_penalty": 0,
        "mirostat": 0,
        "mirostat_tau": 5,
        "mirostat_eta": 0.1,
        "grammar": "",
        "n_probs": 0,
        "min_keep": 0,
        "image_data": [],
        "cache_prompt": True,
        "api_key": "",
        "slot_id": -1,
        "prompt": prompt
    }

    response = requests.post(url, data=json.dumps(data), headers=headers)
    print(response)
    
    if response.status_code in [200, 201]:
        try:
            completion_text = ""
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith('data: '):
                        data = json.loads(decoded_line[6:])
                        content = data.get('content', '')
                        stop = data.get('stop', False)
                        #print(content, end='', flush=True)
                        completion_text += content
                        if stop:
                            break
            #print("\ncompletion_text:", completion_text)
            messages.append({'role': 'assistant', 'content': completion_text})
            return completion_text
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise Exception(f"Unexpected response structure: {response.text}") from e
    elif response.status_code in [500, 429]:
        raise Exception(f"Error: {response.status_code}, {response.text}")
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")

# isn't used
def replace_weird_symbols(text):
    symbols_to_remove = '@#^()_~[]{}|\\<>/'
    for symbol in symbols_to_remove:
        text = text.replace(symbol, ' ')

    return text

def response(user_name: str, user_chat: list):
    if user_chat == []:
        logger.error(f"passed empty user chat for {user_name}")
    if len(user_chat) > settings["context_size"]:
        user_chat = user_chat[-settings["context_size"]:]
    comp = completion(user_chat)
    logger.info(f"COMP: {comp}")
    response = comp[-1]
    
    return response


# isn't used
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