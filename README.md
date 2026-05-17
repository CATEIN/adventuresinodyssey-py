[![PyPI version](https://img.shields.io/pypi/v/adventuresinodyssey?label=PyPI)](https://pypi.org/project/adventuresinodyssey/)
[![Docs](https://img.shields.io/badge/Docs-unfinished-blue)](docs/docs.md)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Examples](https://img.shields.io/badge/Examples-view%20now-yellow)](examples/examples.md)
# adventuresinodyssey
Unofficial python API clients for the Adventures in Odyssey Club and website.

```bash
pip install adventuresinodyssey
```
> [!NOTE]
> This project is intended for personal use. The authenticated client (`ClubClient`) requires a valid Adventures in Odyssey Club subscription and is not intended for downloading, redistributing, or pirating content. Please respect Focus on the Family's terms of service.

I recomend using [mpv](https://github.com/mpv-player/mpv) for streaming episodes.
```bash
pip install mpv
```

## Quick examples

Fetch a random episode:
```python
import random
from adventuresinodyssey import AIOClient

client = AIOClient()
link_base = "https://app.adventuresinodyssey.com/content/"

print("Caching episodes...")
all_episodes = client.cache_episodes()

if not all_episodes:
    print("Error: Failed to cache episodes.")
    exit()

# Pick a random episode
episode = random.choice(all_episodes)

print(f"Random episode: {episode.get('short_name')}")
print(f"Link: {link_base}{episode.get('id')}")
```

Create a playlist of soundtracks:
```python
from dotenv import load_dotenv
import os
from adventuresinodyssey import ClubClient
load_dotenv()

client = ClubClient(
    email=os.getenv("AIO_EMAIL"),
    password=os.getenv("AIO_PASSWORD"),
    viewer_id=os.getenv("AIO_VIEWER_ID"),
    pin=os.getenv("AIO_PIN")
)

soundtracks = []
content_groups = client.fetch_content_groupings(grouping_type="Collection")

for content_group in content_groups["contentGroupings"]:
    if "Season" in content_group["name"]: # filter only season soundtracks
        for episode in content_group["contentList"]:
            print(episode["short_name"])
            soundtracks.append(episode["id"])

created_playlist = client.create_playlist(name="Soundtracks", content_ids=soundtracks)

print("Playlist created! Link: https://app.adventuresinodyssey.com/playlists/" + created_playlist['contentGroupings'][0]["id"])
```

## Acknowledgements
Thanks to [Droopcat](https://github.com/DroopCat) for figuring out the Clubs authentication flow
