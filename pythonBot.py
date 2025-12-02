import asyncio
import random
import discord
import os
from dotenv import load_dotenv
import requests
import json
import yt_dlp

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

import logging

queue = []

# Per-guild async queues and player tasks
guild_queues = {}
player_tasks = {}

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

def add_to_queue(audio_url, audio_duration):
    queue.insert(0,[audio_url, audio_duration])
    return


def get_from_queue():
    if len(queue) > 0:
        return queue[len(queue)-1]
    else:
        return None
    

def pop_queue():
    if len(queue) > 0:
        queue.pop()
    return

async def _ensure_guild_queue(guild_id: int):
    if guild_id not in guild_queues:
        guild_queues[guild_id] = asyncio.Queue()
    return guild_queues[guild_id]

async def _run_yt_dlp_info(url: str):
    # Run blocking yt_dlp.extract_info in a thread to avoid blocking the event loop
    def extract():
        ydl_opts = {
            'format': 'm4a/bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
            }],
            'extractor-args': "youtube:player_client=default",
            'noplaylist': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {'url': info['url'], 'duration': info.get('duration', 0), 'title': info.get('title')}

    return await asyncio.to_thread(extract)

async def startup(vc: discord.VoiceClient):
    startupVoices = ["./joining voicelines/1.m4a","./joining voicelines/2.m4a","./joining voicelines/3.m4a"]
    choice = random.choice(startupVoices)
    vc.play(discord.FFmpegPCMAudio(choice))
    return

async def start_player_task_if_needed(guild: discord.Guild, voice_client: discord.VoiceClient):
    # Start a background player loop per guild if not already running
    if guild.id in player_tasks and not player_tasks[guild.id].done():
        return

    async def player_loop():
        q = await _ensure_guild_queue(guild.id)
        while True:
            try:
                item = await q.get()
            except asyncio.CancelledError:
                break

            try:
                vc = guild.voice_client
                if vc is None:
                    logging.warning(f"No voice client for guild {guild.id}, skipping playback")
                    continue

                source = discord.FFmpegPCMAudio(item['url'], before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5')
                vc.play(source)

                # Wait for playback to finish without blocking the loop
                while vc.is_playing() or vc.is_paused():
                    await asyncio.sleep(1)

            except Exception as e:
                logging.exception('Error during playback')
            finally:
                q.task_done()

    player_tasks[guild.id] = asyncio.create_task(player_loop())
    
    
    
    
    
class MyClient(discord.Client):
    async def on_ready(self):
        await tree.sync()
        print('Tree synced')
        print('Logged on as {0}!'.format(self.user))

    async def on_message(self, message):
        if message.author == self.user:
            return
                
                    
                    
                    
                           
intents = discord.Intents.default()
intents.message_content = True

client = MyClient(intents=intents)



tree = discord.app_commands.CommandTree(client)

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

@tree.command(name="leave", description="Disconnects the bot from the voice channel")
async def leave(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client is not None:
        await voice_client.disconnect()
        await interaction.response.send_message(f"Disconnected from the voice channel, {interaction.user.name} Onii Sama.")
    else:
        await interaction.response.send_message("I am not connected to any voice channel, are you dumb?")

@tree.command(name="skip", description="Skips the current audio track")
async def skip(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client is None or not voice_client.is_playing():
        await interaction.response.send_message("No audio is currently playing.")
        return

    voice_client.stop()
    await interaction.response.send_message(f"Does this mean you want me to play the next track, {interaction.user.name} Onii Sama?")
    return

@tree.command(name="queue", description="Shows the current audio queue")
async def show_queue(interaction: discord.Interaction):
    q = await _ensure_guild_queue(interaction.guild.id)
    if q.empty():
        await interaction.response.send_message("The audio queue is currently empty.")
        return

    queue_list = []
    temp_queue = asyncio.Queue()

    while not q.empty():
        item = await q.get()
        queue_list.append(item.get('title', 'Unknown Title'))
        await temp_queue.put(item)
        q.task_done()
        
    # Restore the original queue
    while not temp_queue.empty():
        item = await temp_queue.get()
        await q.put(item)
        temp_queue.task_done()

    queue_message = "Current Audio Queue waiting:\n" + "\n".join(f"{idx + 1}. {title}" for idx, title in enumerate(queue_list))
    await interaction.response.send_message(queue_message)

@tree.command(name="pause", description="Pauses the current audio track")
async def pause(interaction: discord.Interaction):
    return

@tree.command(name="resume", description="Resumes the paused audio track")
async def resume(interaction: discord.Interaction):
    return

@tree.command(name="play", description="Plays audio from a YouTube URL in your current voice channel")
async def play(interaction: discord.Interaction, url: str):
    await interaction.response.defer()  # Acknowledge the command to avoid timeout
    user = interaction.user
    # await join_channel(user)
    currentChannel = user.voice
    if currentChannel is not None:
        voice_channel = currentChannel.channel
        if interaction.guild.voice_client is None:
            await voice_channel.connect()
            await startup(voice_channel.guild.voice_client)
    voice_client = interaction.guild.voice_client
    if voice_client is None:
        await interaction.followup.send("Bot is not connected to a voice channel.")
        return
    
    
    
     
    # Extract info using yt_dlp in a thread so we don't block the event loop
    try:
        info = await _run_yt_dlp_info(url)
    except Exception:
        logging.exception('Failed to extract info')
        await interaction.followup.send(f'Failed to retrieve info for: {url}')
        return

    # Ensure guild queue exists and enqueue the track
    q = await _ensure_guild_queue(interaction.guild.id)
    await q.put(info)

    # Start background player task for this guild if not running
    await start_player_task_if_needed(interaction.guild, voice_client)

    # Respond to user
    title = info.get('title') or url
    await interaction.followup.send(f'My Onii Sama {user.name} wants {title}, its not like I wanted to play it or anything\n{url}')
        
if DISCORD_TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment variable is not set")
client.run(DISCORD_TOKEN)