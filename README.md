[![PyPI version](https://img.shields.io/pypi/v/adventuresinodyssey?label=PyPI)](https://pypi.org/project/adventuresinodyssey/)
[![Docs](https://img.shields.io/badge/Docs-read-blue)](https://github.com/CATEIN/adventuresinodyssey-py/blob/main/docs/docs.md)
[![License](https://img.shields.io/badge/License-MIT-green)](https://github.com/CATEIN/adventuresinodyssey-py/blob/main/LICENSE)
[![Examples](https://img.shields.io/badge/Examples-view%20now-yellow)](https://github.com/CATEIN/adventuresinodyssey-py/blob/main/examples/examples.md)

# adventuresinodyssey

Unofficial Python clients for the [Adventures in Odyssey Club](https://app.adventuresinodyssey.com/) API.

Look up episodes, albums, characters, cast and crew, themes, the radio schedule and search results. With a Club account you can also manage playlists, bookmarks, comments and listening progress.

> [!NOTE]
> This project is intended for personal use. `ClubClient` requires a valid Adventures in Odyssey Club subscription and is not intended for downloading, redistributing or pirating content. Please respect Focus on the Family's terms of service.

## Installation

```bash
pip install adventuresinodyssey
```

If you plan to log in with `ClubClient` or `AsyncClubClient`, also install the browser Playwright uses for login (one-time setup):

```bash
playwright install chromium
```

Requires Python 3.8+.

## Which client do I need?

| Client | Login? | Use it for |
| --- | :---: | --- |
| `AIOClient` | No | Anything the public site shows: metadata, promos, radio episodes, search, characters, albums |
| `ClubClient` | Yes | Everything in `AIOClient`, plus full episodes, playlists, bookmarks, comments, badges and progress |
| `AsyncAIOClient` | No | `AIOClient` for `asyncio` code |
| `AsyncClubClient` | Yes | `ClubClient` for `asyncio` code |

## Quick start

### No account needed

```python
import random
from adventuresinodyssey import AIOClient

client = AIOClient()

episodes = client.cache_episodes()          # every episode, across all albums
episode = random.choice(episodes)

print(episode["short_name"])                # e.g. "#125: All's Well With Boswell"
print("https://app.adventuresinodyssey.com/content/" + episode["id"])
```

### With a Club account

Keep your credentials out of your code. Put them in a `.env` file next to your script (and add it to `.gitignore`):

```bash
AIO_EMAIL=you@example.com
AIO_PASSWORD=your_password
AIO_VIEWER_ID=a3J...   # optional, see the ClubClient docs
AIO_PIN=1234           # optional, only if the profile has a PIN
```

Then load them with [`python-dotenv`](https://pypi.org/project/python-dotenv/) (`pip install python-dotenv`):

```python
import os
from dotenv import load_dotenv
from adventuresinodyssey import ClubClient

load_dotenv()

client = ClubClient(
    email=os.getenv("AIO_EMAIL"),
    password=os.getenv("AIO_PASSWORD"),
    viewer_id=os.getenv("AIO_VIEWER_ID"),
    pin=os.getenv("AIO_PIN"),
)

# Make a playlist out of every season soundtrack
soundtracks = []
collections = client.fetch_content_groupings(grouping_type="Collection", page_size=100)

for group in collections["contentGroupings"]:
    if "Season" in group["name"]:
        soundtracks += [item["id"] for item in group["contentList"]]

playlist = client.create_playlist(name="Soundtracks", content_ids=soundtracks)
playlist_id = playlist["contentGroupings"][0]["id"]
print("https://app.adventuresinodyssey.com/playlists/" + playlist_id)
```

You don't need to call `login()`. The client logs in on the first request and saves the session to `club_session.json`, so later runs skip the browser login. **Treat `club_session.json` like a password: don't commit or share it.**

### Async

```python
import asyncio
from adventuresinodyssey import AsyncAIOClient

async def main():
    async with AsyncAIOClient() as client:
        radio = await client.fetch_radio(page_size=3)
        for episode in radio["results"]:
            print(episode["relative_air_day"], "-", episode["short_name"])

asyncio.run(main())
```

## Documentation

* [Overview and concepts](https://github.com/CATEIN/adventuresinodyssey-py/blob/main/docs/docs.md): start here
* [Function reference](https://github.com/CATEIN/adventuresinodyssey-py/blob/main/docs/docs.md#function-reference): every method, and which client has it
* [Example programs](https://github.com/CATEIN/adventuresinodyssey-py/blob/main/examples/examples.md)

For streaming episodes, I recommend [mpv](https://github.com/mpv-player/mpv) (`pip install mpv` for the Python bindings).

## Acknowledgements

Thanks to [Droopcat](https://github.com/DroopCat) for figuring out the Club's authentication flow.
