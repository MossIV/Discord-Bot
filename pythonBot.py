import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
import requests
import json
import yt_dlp

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

async def join_channel(user):
    currentChannel = user.voice
    if currentChannel is not None:
        await currentChannel.channel.connect()

class MyClient(discord.Client):
    async def on_ready(self):
        await tree.sync()
        print('Tree synced')
        print('Logged on as {0}!'.format(self.user))

    async def on_message(self, message):
        if message.author == self.user:
            return
            
        if message.content.startswith('$join'):
            user = message.author
            currentChannel = user.voice
            if currentChannel is not None:
                await join_channel(user)
            else:
                await message.channel.send(user.name+" is not in a voice channel!")
                
        if message.content.startswith('$leave'):
            for voiceChannel in self.voice_clients:
                if getattr(voiceChannel, 'guild', None) == message.guild:
                    await voiceChannel.disconnect(force=True)
                    await message.channel.send("Disconnected from voice channel at the request of my master "+message.author.name)
                           
intents = discord.Intents.default()
intents.message_content = True

client = MyClient(intents=intents)



tree = app_commands.CommandTree(client)

@tree.command(name="meme", description="Sends a random meme")
async def meme(interaction: discord.Interaction):
    await interaction.response.send_message(get_meme())

@tree.command(name="ping", description="Replies with pong!")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("pong!")
    
@tree.command(name="dadjoke", description="Sends a random dad joke")
async def dadjoke(interaction: discord.Interaction):
    await interaction.response.send_message(get_dad())
    
@tree.command(name="yayornay", description="Sends a random yes or no with gif")
async def yayornay(interaction: discord.Interaction):
    answerArray = get_yeah_nah()
    await interaction.response.send_message(answerArray[0])
    await interaction.followup.send(answerArray[1])
    
if DISCORD_TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment variable is not set")
client.run(DISCORD_TOKEN)