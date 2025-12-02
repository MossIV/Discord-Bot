import asyncio
import random
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

import logging
from discord.errors import NotFound as DiscordNotFound

queue = []

# Per-guild async queues and player tasks
guild_queues = {}
player_tasks = {}
# Prevent races when multiple /play commands attempt to connect the bot to a voice channel at the same time
connect_locks = {}

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


async def _safe_defer(interaction: discord.Interaction):
    """Attempt to call interaction.response.defer() without crashing when the interaction is invalid.
    Returns whether a defer was successfully called.
    """
    try:
        await interaction.response.defer()
        return True
    except DiscordNotFound:
        # Interaction likely expired or is unknown — log, and we will fallback to channel messages.
        logging.warning('Interaction expired or unknown while trying to defer')
        return False
    except Exception:
        logging.exception('Error deferring interaction')
        return False


async def _safe_send(interaction: discord.Interaction, content: str, *, ephemeral: bool = False):
    """Attempt to send a message for an interaction using response/send or fallback to channel send.
    This returns the created message or None on failure.
    """
    try:
        # If the interaction hasn't been responded to, use the initial response API
        if not interaction.response.is_done():
            return await interaction.response.send_message(content, ephemeral=ephemeral)
        # Otherwise, try sending a followup
        return await interaction.followup.send(content, ephemeral=ephemeral)
    except DiscordNotFound:
        logging.warning('Interaction expired or unknown while sending message; falling back to channel send')
        try:
            # Fallback: send to the channel if available
            if interaction.channel is not None:
                return await interaction.channel.send(content)
        except Exception:
            logging.exception('Failed to fallback send message to channel')
        return None
    except Exception:
        logging.exception('Error sending message for interaction')
        return None

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
                # Validate item and url
                if not isinstance(item, dict) or item.get('url') is None:
                    logging.warning(f"Skipping invalid queue item for guild {guild.id}: {item}")
                    continue

                try:
                    source = discord.FFmpegPCMAudio(item['url'], before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5')
                except Exception:
                    logging.exception('Failed to create audio source for item')
                    continue
                vc.play(source)

                # Wait for playback to finish without blocking the loop
                while vc.is_playing() or vc.is_paused():
                    await asyncio.sleep(1)

            except Exception as e:
                logging.exception('Error during playback')
            finally:
                q.task_done()

    player_tasks[guild.id] = asyncio.create_task(player_loop())


async def _ensure_connected_once(voice_channel: discord.VoiceChannel):
    """Connect to the voice channel once even if multiple callers try concurrently.
    Uses a per-guild asyncio.Lock to avoid race conditions.
    """
    guild_id = voice_channel.guild.id
    if guild_id not in connect_locks:
        connect_locks[guild_id] = asyncio.Lock()

    async with connect_locks[guild_id]:
        # Check again inside lock whether we are connected
        if voice_channel.guild.voice_client is None:
            await voice_channel.connect()
            await startup(voice_channel.guild.voice_client)
    
    
    
    
    
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



tree = app_commands.CommandTree(client)

@tree.command(name="meme", description="Sends a random meme")
async def meme(interaction: discord.Interaction):
    await _safe_send(interaction, get_meme())

@tree.command(name="ping", description="Replies with pong!")
async def ping(interaction: discord.Interaction):
    await _safe_send(interaction, "pong!")
    
@tree.command(name="dadjoke", description="Sends a random dad joke")
async def dadjoke(interaction: discord.Interaction):
    await _safe_send(interaction, get_dad())
    
@tree.command(name="yayornay", description="Sends a random yes or no with gif")
async def yayornay(interaction: discord.Interaction):
    answerArray = get_yeah_nah()
    await _safe_send(interaction, answerArray[0])
    # Follow-up media/reply
    try:
        await interaction.followup.send(answerArray[1])
    except Exception:
        # If follow-up fails (interaction expired), just fallback to channel
        logging.exception('Failed to send follow-up in yayornay, falling back to channel message')
        if interaction.channel is not None:
            await interaction.channel.send(answerArray[1])

@tree.command(name="leave", description="Disconnects the bot from the voice channel")
async def leave(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client is not None:
        await voice_client.disconnect()
        # cleanup background player task and queue for this guild
        if interaction.guild.id in player_tasks:
            task = player_tasks.pop(interaction.guild.id)
            if task and not task.done():
                task.cancel()
        if interaction.guild.id in guild_queues:
            _ = guild_queues.pop(interaction.guild.id)
        await _safe_send(interaction, f"Disconnected from the voice channel, {interaction.user.name} Onii Sama.")
    else:
        await _safe_send(interaction, "I am not connected to any voice channel, are you dumb?")

@tree.command(name="skip", description="Skips the current audio track")
async def skip(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client is None or not voice_client.is_playing():
        await _safe_send(interaction, "No audio is currently playing.")
        return

    voice_client.stop()
    await _safe_send(interaction, f"Does this mean you want me to play the next track, {interaction.user.name} Onii Sama?")
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
    await _safe_send(interaction, queue_message)


@tree.command(name="playdebug", description="Shows debug info for the guild's audio queue and player task")
async def playdebug(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    q = guild_queues.get(guild_id)
    task = player_tasks.get(guild_id)
    task_status = 'none'
    if task is None:
        task_status = 'no task'
    else:
        task_status = 'running' if not task.done() else 'done'

    if q is None:
        await _safe_send(interaction, f'No queue for this guild. Player task: {task_status}')
        return

    # Report a few details without draining the queue
    items = []
    temp_q = asyncio.Queue()
    while not q.empty():
        item = await q.get()
        items.append(item.get('title', 'Unknown'))
        await temp_q.put(item)
        q.task_done()

    # Restore
    while not temp_q.empty():
        i = await temp_q.get()
        await q.put(i)
        temp_q.task_done()

    msg = f'Player task: {task_status}\nQueue size: {q.qsize()}\nItems: ' + (', '.join(items) if items else '(empty)')
    await _safe_send(interaction, msg)

@tree.command(name="play", description="Plays audio from a YouTube URL in your current voice channel")
async def play(interaction: discord.Interaction, url: str):
    # Defer if possible to avoid interaction timeouts; fall back to channel messages if interaction is expired
    await _safe_defer(interaction)
    user = interaction.user
    # await join_channel(user)
    currentChannel = user.voice
    if currentChannel is not None:
        voice_channel = currentChannel.channel
        if interaction.guild.voice_client is None:
            # Use lock-protected connect to avoid races from multiple concurrent /play commands
            await _ensure_connected_once(voice_channel)
    voice_client = interaction.guild.voice_client
    if voice_client is None:
        await _safe_send(interaction, "Bot is not connected to a voice channel.")
        return
    
    
    
     
    # Extract info using yt_dlp in a thread so we don't block the event loop
    try:
        info = await _run_yt_dlp_info(url)
    except Exception:
        logging.exception('Failed to extract info')
        await _safe_send(interaction, f'Failed to retrieve info for: {url}')
        return

    # Ensure guild queue exists and enqueue the track
    # Basic validation: make sure info is a dict and has a playable 'url'
    if not isinstance(info, dict) or info.get('url') is None:
        # Try fallback re-extract using the original URL or a 'webpage_url' field
        fallback_url = None
        if isinstance(info, dict) and info.get('webpage_url'):
            fallback_url = info.get('webpage_url')
        else:
            fallback_url = url

        try:
            re_info = await _run_yt_dlp_info(fallback_url)
            if isinstance(re_info, dict) and re_info.get('url'):
                info = re_info
            else:
                logging.warning(f"Could not extract playable url for provided link: {url}")
                await _safe_send(interaction, 'Could not extract a playable audio URL from the provided link.')
                return
        except Exception:
            logging.exception('Failed to re-extract playable info for URL')
            await _safe_send(interaction, 'Could not extract a playable audio URL from the provided link.')
            return

    q = await _ensure_guild_queue(interaction.guild.id)
    await q.put(info)

    # Start background player task for this guild if not running
    await start_player_task_if_needed(interaction.guild, voice_client)

    # Respond to user
    title = info.get('title') or url
    await _safe_send(interaction, f'My Onii Sama {user.name} wants {title}, its not like I wanted to play it or anything\n{url}')
        
if DISCORD_TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment variable is not set")
client.run(DISCORD_TOKEN)