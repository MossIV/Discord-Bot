import asyncio
import random
import discord
import os
from dotenv import load_dotenv
import requests
import json
import yt_dlp
import re

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

import logging

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
            if '_type' in info:
                if info['_type'] == 'playlist':
                    info = info['entries'][0]
            return {'url': info['url'], 'duration': info.get('duration', 0), 'title': info.get('title')}

    return await asyncio.to_thread(extract)

async def startup(vc: discord.VoiceClient):
    startupVoices = ["./joining voicelines/1.m4a","./joining voicelines/2.m4a","./joining voicelines/3.m4a","./joining voicelines/special.m4a"]
    weights = [33,33,33,1]
    choice = random.choices(startupVoices, weights=weights, k=1)[0]
    vc.play(discord.FFmpegPCMAudio(choice))
    
    while vc.is_playing():
        await asyncio.sleep(0.5)
    return

async def start_player_task_if_needed(guild: discord.Guild, voice_client: discord.VoiceClient, text_channel: discord.TextChannel):
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
                await text_channel.send(f"Now Playing: {item['title']}")
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
        if interaction.user.name == "mossv":
            await interaction.response.send_message("I have retreated from the discussion chambers, My Creator")
        else:
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
    total_duration = 0
    
    while not q.empty():
        item = await q.get()
        total_duration += item.get('duration', 0)
        queue_list.append(item.get('title', 'Unknown Title'))
        await temp_queue.put(item)
        q.task_done()
        
    # Restore the original queue
    while not temp_queue.empty():
        item = await temp_queue.get()
        await q.put(item)
        temp_queue.task_done()

    if total_duration >= 3600:
        hours = total_duration // 3600
        minutes = (total_duration % 3600) // 60
        seconds = total_duration % 60
        duration_str = f"{hours}h {minutes}m {seconds}s in queue"
    elif total_duration >= 60:
        minutes = total_duration // 60
        seconds = total_duration % 60
        duration_str = f"{minutes}m {seconds}s in queue"
    else:
        duration_str = f"{total_duration}s in queue"
    
    queue_message = "Current Audio Queue waiting:\n" + "\n".join(f"{idx + 1}. {title}" for idx, title in enumerate(queue_list)) + f"\nTotal Duration: {duration_str}"
    await interaction.response.send_message(queue_message)

@tree.command(name="pause", description="Pauses the current audio track")
async def pause(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client is None or not voice_client.is_playing():
        await interaction.response.send_message("No audio is currently playing.")
        return

    voice_client.pause()
    await interaction.response.send_message(f"Audio paused, {interaction.user.name} Onii Sama.")
    return

@tree.command(name="resume", description="Resumes the paused audio track")
async def resume(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client is None or not voice_client.is_paused():
        await interaction.response.send_message("No audio is currently paused.")
        return
    
    voice_client.resume()
    await interaction.response.send_message(f"Audio resumed, {interaction.user.name} Onii Sama.")
    return

#TODO: implement search functionality.

# Milestone 4: Add Search-Specific Features (Optional Enhancements)
#   Description: Once basic search works, add niceties like multiple result options or search limits.
# Key Tasks:
#   Modify yt_dlp options to limit search results (e.g., 'default_search': 'ytsearch5' for top 5).
#   Optionally, add a new /search command that lists results (e.g., "1. Title - URL\n2. ...") and lets users choose via reactions or a follow-up command.
#   Integrate playlist support if yt_dlp finds one (e.g., enqueue all tracks from a search result).
# Effort: Medium-High (4-8 hours). Requires UI changes for selection.
# Testing: Test with popular queries and ensure enqueuing works for multiple tracks.

# Milestone 5: Full Integration and Edge Case Testing
#   Description: Ensure searching works across guilds, handles concurrent searches, and integrates with the queue/player system.
# Key Tasks:
#   Test per-guild queues with searches (e.g., multiple users searching simultaneously).
#   Handle edge cases: Very long queries, special characters, non-YouTube sources (if yt_dlp supports them), or rate limits.
#   Add rate limiting or caching if needed (e.g., avoid duplicate searches).
# Effort: Medium (2-4 hours). Focus on real-world scenarios.
# Testing: Run the bot in a test server, add multiple searches quickly, and monitor for heartbeat issues or crashes.

# Milestone 6: Documentation and Deployment
#   Description: Finalize and document the feature.
# Key Tasks:
#   Update readme.md with examples (e.g., "/play never gonna give you up").
#   Add comments in code for the search logic.
#   Deploy and monitor in production for any yt_dlp updates or API changes.
# Effort: Low (1 hour).
# Testing: Share with a small group and gather feedback.

@tree.command(name="play", description="Plays audio from a YouTube URL or search query, URLs can be stacked with spaces in between")
async def play(interaction: discord.Interaction, search_or_url: str):
    await interaction.response.defer()  # Acknowledge the command to avoid timeout
    user = interaction.user
    text_channel = interaction.channel
    
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
    
    q = await _ensure_guild_queue(interaction.guild.id)
    
    urls = re.findall(r'https?://\S+', search_or_url)
    title_of_urls = []
    # Extract info using yt_dlp in a thread so we don't block the event loop
    if urls:
        for url in urls:
            try:
                info = await _run_yt_dlp_info(url)
            except Exception:
                logging.exception('Failed to extract info')
                await interaction.followup.send(f'Failed to retrieve info for: {url}')
                return
            title_of_urls.append(info.get('title'))
            # Ensure guild queue exists and enqueue the track
            await q.put(info)
    else:
        # Treat search_or_url as a search query
        search_query = f"ytsearch:{search_or_url}"
        try:
            info = await _run_yt_dlp_info(search_query)
        except Exception:
            logging.exception('Failed to extract info for search query')
            await interaction.followup.send(f'Failed to retrieve info for search query: {search_or_url}')
            return

        # Ensure guild queue exists and enqueue the track
        await q.put(info)
        if info.get('id', '') == '':
            url = f"{user.name} Onii Sama, has asked me to search this up: {search_or_url}"
        else:
            url = f"https://www.youtube.com/watch?v={info.get('id', '')}" 

    # Start background player task for this guild if not running
    await start_player_task_if_needed(interaction.guild, voice_client, text_channel)

    # Respond to user
    title = info.get('title') or url
    if len(urls) > 1:
        await interaction.followup.send(f'My Onii Sama {user.name} wants me to play the following tracks, gosh Onii Sama, you\' re so annoying.\n\n' + '\n'.join(title_of_urls))
    else:
        await interaction.followup.send(f'My Onii Sama {user.name} wants {title}, its not like I wanted to play it or anything.\n{url}')
        
if DISCORD_TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment variable is not set")
client.run(DISCORD_TOKEN)