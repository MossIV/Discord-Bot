import discord
import os
from dotenv import load_dotenv
import requests
import json

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

def get_meme():
    response = requests.get('https://meme-api.com/gimme')
    json_data = json.loads(response.text)
    print(json_data)
    return json_data['url']

def get_dad():
    URL = "https://icanhazdadjoke.com/"
    headers = {
        "Accept": "application/json",  # get JSON instead of HTML
        "User-Agent": "Discord Python Bot"  # identify your app
    }

    response = requests.get(URL, headers=headers)
    json_data = response.json()
    return json_data['joke']
    
def get_yeah_nah():
    URL="https://yesno.wtf/api"
    response = requests.get(URL)
    json_data = response.json()
    response_json = [json_data['answer'],json_data['image']]
    return response_json

class MyClient(discord.Client):
    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))

    async def on_message(self, message):
        if message.author == self.user:
            return

        if message.content.startswith('$meme'):
            await message.channel.send(get_meme())

        if message.content.startswith('$dad'):
            await message.channel.send(get_dad())

        if message.content.startswith('$yayornay'):
            answer_array = get_yeah_nah()
            await message.channel.send(answer_array[0])
            await message.channel.send(answer_array[1])

intents = discord.Intents.default()
intents.message_content = True

client = MyClient(intents=intents)
client.run(DISCORD_TOKEN)