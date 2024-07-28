import requests
import time
import json

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

if __name__ == "__main__":
    initial_messages = [
        {"role": "system", "content": "You are Raya a girl in the internet chat with some strangers"},
        {"role": "user", "content": "Hello lol"}
    ]
    print(completion_local(initial_messages))
