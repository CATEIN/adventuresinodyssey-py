import schedule
import time
from adventuresinodyssey import AIOClient
import mpv

def play_episode():
    client = AIOClient()
    player = mpv.MPV(ytdl=False, video="no")
    player.http_header_fields = ["Sec-Fetch-Dest: audio"]

    radio_episode = client.fetch_radio(page_size=1)# Get newest radio episode
    episode = client.fetch_content(radio_episode["results"][0]["id"], page_type="radio")# Get the episode id to fetch its audio.
    url = episode["download_url"]

    print("Now playing " + episode["short_name"])
    player.play(url)
    player.wait_for_playback()

# Run on first use
play_episode()

# Run every day at 8:00 PM
schedule.every().day.at("20:00").do(play_episode)

print("Scheduler running… waiting for 8:00 PM.")

while True:
    schedule.run_pending()
    time.sleep(1)

