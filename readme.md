Packages used
yt-dlp
discord.py
PyNaCl
ffmpeg from yt-dlp

Behavior
 - By default the bot will ignore playlist and YouTube mix URLs (generated "mix" lists). If you provide a playlist or mix to the `/play` command, it will respond asking for a single video URL.
 - You can pass `play_first=True` to the `/play` command to play the first video from a playlist or mix.

Notes
 - Mix URLs are recognized by the `list` query parameter beginning with `RD` (the YouTube "recommended mix" prefix). The bot will ignore these by default; set `play_first=True` to play the first track.
 - If the first playlist/mix entry doesn't contain a direct stream URL, the bot will try to extract the entry's webpage URL to get a playable stream. If that fails, the bot will inform you.