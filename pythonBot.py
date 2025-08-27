import discord
import os
from dotenv import load_dotenv
import requests
import json

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

print(DISCORD_TOKEN)

class MyClient(discord.Client):
    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))

    async def on_message(self, message):
        if message.author == self.user:
            return

        if message.content.startswith('$hello'):
            await message.channel.send('Hello World!')
            
    def get_meme():
        response = requests.get('https://meme-api.com/gimme')
        json_data = json.loads(response.text)
        return json_data['url']

intents = discord.Intents.default()
intents.message_content = True

client = MyClient(intents=intents)
client.run(DISCORD_TOKEN)