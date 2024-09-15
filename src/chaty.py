__version__ = "1.0.0"

import requests
import json
import time
import re
from keys import api_gpt, eleven_labs, voice_id
from logger import Logger
with open("./settings.json", "r", encoding="utf-8") as file:
    settings = json.load(file)

MODELS_LIST = settings["MODELS_LIST"]

logger = Logger().get_logger()


# isn't used
def split_sentences(response):
    if len(response) < settings["response_split_threshold"]:
        split_into_sentences = []
        split_into_sentences = re.split(r',', response)
    else:
        split_into_sentences = []
        split_into_sentences = re.split(r'\.\s|\n\n', response)
    return split_into_sentences



def completion(messages, api_key=api_gpt, proxy=''):
    url = settings['urls']['openai']
    if proxy is not None and proxy != '': url = proxy
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "model": settings["models"]["openai"],
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

        return completion_text
    elif response.status_code == 500 or response.status_code == 429:
        raise Exception(f"Error: {response.status_code}, {response.text}")
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")

def completion_local(messages):
    url = settings['urls']['local']
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer no-key" 
    }

    
    # Construct the prompt from the messages
    #prompt = ""
    #for message in messages:
    #    role = message['role'].capitalize()
    #    content = message['content']
    #    prompt += f"{role}: {content}\n"
    #prompt += "Raya:"

    #data = {
    #    "stream": True,
    #    "n_predict": 300,
    #    "temperature": 0.7,
    #    "stop": ["</s>", "Raya:", "User:"],
    #    "repeat_last_n": 256,
    #    "repeat_penalty": 1.18,
    #    "penalize_nl": False,
    #    "top_k": 40,
    #    "top_p": 0.95,
    #    "min_p": 0.05,
    #    "tfs_z": 1,
    #    "typical_p": 1,
    #    "presence_penalty": 0,
    #    "frequency_penalty": 0,
    #    "mirostat": 0,
    #    "mirostat_tau": 5,
    #    "mirostat_eta": 0.1,
    #    "grammar": "",
    #    "n_probs": 0,
    #    "min_keep": 0,
    #    "image_data": [],
    #    "cache_prompt": True,
    #    "api_key": "",
    #    "slot_id": -1,
    #    "prompt": prompt
    #}
    data = {
        "model": settings["models"]["local"],
        "messages": messages
    }
    response = requests.post(url, data=json.dumps(data), headers=headers)
    response_data = json.loads(response.text)
    
    
    if response.status_code in [200, 201]:
        content = response_data["choices"][0]["message"]["content"]
        #logger(content)
        #try:
        #    completion_text = ""
        #    for line in response.iter_lines():
        #        if line:
        #            decoded_line = line.decode('utf-8')
        #            if decoded_line.startswith('data: '):
        #                data = json.loads(decoded_line[6:])
        #                content = data.get('content', '')
        #                stop = data.get('stop', False)
        #                completion_text += content
        #                if stop:
        #                    break
        #    messages.append({'role': 'assistant', 'content': completion_text})
        #    return completion_text
        #except (KeyError, IndexError, json.JSONDecodeError) as e:
        #    raise Exception(f"Unexpected response structure: {response.text}") from e
        return content
    elif response.status_code in [500, 429]:
        raise Exception(f"Error: {response.status_code}, {response.text}")
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")

def jailbreak_test_local(message):
    url = settings['urls']['local']
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer no-key" 
    }
    initial_messages = [
                        {"role": "system", "content":  settings["prompts"]["jailbreak"][settings["lang"]] },
                        {"role": "user", "content":  f"text: '" + message + "' is it 1 or 0?"}
                    ]
    data = {
        "model": "gpt-3.5-turbo",
        "messages": initial_messages
    }
    response = requests.post(url, data=json.dumps(data), headers=headers)
    response_data = json.loads(response.text)
    if response.status_code in [200, 201]:
        content = response_data["choices"][0]["message"]["content"]
        return content
    elif response.status_code in [500, 429]:
        raise Exception(f"Error: {response.status_code}, {response.text}")
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")
    
def jailbreak_response_local(message):
    url = settings['urls']['local']
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer no-key" 
    }
    initial_messages = [
                        {"role": "system", "content":  settings["prompts"]["jailbreak"][settings["lang"]] },
                    ]
    data = {
        "model": settings["models"]["local"],
        "messages": initial_messages
    }
    response = requests.post(url, data=json.dumps(data), headers=headers)
    response_data = json.loads(response.text)
    if response.status_code in [200, 201]:
        content = response_data["choices"][0]["message"]["content"]
        return content
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
    response = comp
    
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