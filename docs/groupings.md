# Content Groupings
Content Groups can be fetched by type using `fetch_content_groupings()`. Types include:
* Episode Home
* Album
* Series
* Collection
* Podcast Year
* Bonus Video Home
* Life Lesson
* Book Series
* Playlist (ClubClient only)

```python
from adventuresinodyssey import AIOClient # or ClubClient
client = AIOClient()
groups = client.fetch_content_groupings(page_number=1, page_size=5, grouping_type="Collection")
for group in groups["contentGroupings"]:
    print(group["name"])
```
User created playlists can be fetched with `fetch_playlists()`

# Badges
`ClubClient` can fetch a list of badges and indivudual badges using `fetch_badges()` and `fetch_badge()`
```python
from adventuresinodyssey import ClubClient
from dotenv import load_dotenv
import os

load_dotenv()

client = ClubClient(
    email=os.getenv("AIO_EMAIL"),
    password=os.getenv("AIO_PASSWORD"),
    profile_username=os.getenv("AIO_PROFILE_USERNAME"),
    pin=os.getenv("AIO_PIN"),
)

badges = client.fetch_badges(page_number=1,page_size=5)
for badge in badges["badges"]:
    print(badge["name"])

last_badge = badges["badges"][-1]
badge_data = client.fetch_badge(last_badge["id"])
for content in badge_data["badges"][0]["requirements"]:
    print(content["name"])
```
