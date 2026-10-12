# Content

A *content page* is a single item on the Club: an episode, video, article, book, download, etc. Fetch one by ID with `fetch_content()`:

```python
from adventuresinodyssey import AIOClient  # or ClubClient

client = AIOClient()

content = client.fetch_content("a354W0000046U7kQAE")  # #125: All's Well With Boswell

print(content["short_name"])     # #125: All's Well With Boswell
print(content["type"])           # Audio
print(content["subtype"])        # Episode
print(content["album_name"])     # #08: Beyond Expectations
print(content["bible_verse"])    # Luke 16:10-12
```

The ID is the last part of the content URL: `https://app.adventuresinodyssey.com/content/a354W0000046U7kQAE`.

## Page types

`fetch_content(content_id, page_type=...)` can fetch three versions of a page. They have the same metadata but different media:

| `page_type` | Client | Media you get |
| --- | --- | --- |
| `"promo"` | Both (default on `AIOClient`) | A short (~30 second) sample |
| `"radio"` | Both | The radio version, for episodes in the current [radio rotation](browsing.md#radio-schedule) |
| `"full"` | `ClubClient` only (default there) | The full episode or video |

`AIOClient` raises `ValueError` if you ask for `"full"`.

## Content types

`content["type"]` is one of:

* `Audio`: episodes, audiobooks, podcasts, soundtracks (`subtype` tells you which, e.g. `"Episode"`, `"Audiobook"`, `"Podcast"`)
* `Video`
* `Article`
* `Book`
* `Download`

## Useful fields

The response is a large dictionary. These are the fields you'll use most. Some are `None` or missing depending on the type of content.

| Field | Example | Notes |
| --- | --- | --- |
| `id` | `"a354W0000046U7kQAE"` | |
| `name` | `"All's Well With Boswell"` | |
| `short_name` | `"#125: All's Well With Boswell"` | Name with the episode number. |
| `type`, `subtype` | `"Audio"`, `"Episode"` | See above. |
| `episode_number` | `"125"` | A string. Bonus episodes have numbers like `"124a"`. |
| `description` | `"When Robyn gets her first..."` | Plain text. |
| `album_name` | `"#08: Beyond Expectations"` | |
| `air_date` | `"1990-08-25T00:00:00.000Z"` | Original air date. |
| `recent_air_date`, `relative_air_day` | `"Aired Last 10/23/2025"` | Most recent radio airing. |
| `media_length` | `1382416` | Length in milliseconds. (`30` for promo pages.) |
| `author` | `"Phil Lollar"` | Main writer. `authors` has everyone, with roles. |
| `characters` | `[{"name": "Tom Riley", ...}]` | Characters in the episode. |
| `tags` | `[{"name": "Responsibility", "topic_id": ...}]` | Themes. `topic_id` works with `fetch_theme()`. |
| `bible_verse` | `"Luke 16:10-12"` | |
| `devotional` | `"<div class=...>"` | HTML. `has_devotional` says if there is one. |
| `thumbnail_small`, `thumbnail_medium`, `thumbnail_large` | URL | Cover images. |
| `rating_average`, `rating_count`, `views`, `bookmarks` | | Stats. |
| `previous_episode`, `next_episode` | content dict | Neighbors in the album. |
| `in_album` | list of content | Everything in the same album. |
| `recommendations` | list of content | "You might also like". |
| `progress` | `{"status": "New", "current_progress": 0}` | The profile's progress (ClubClient). |
| `enable_commenting` | `True` | Whether the page has [comments](comments.md). |
| `download_url`, `stream_url`, `signed_cookie` | URL | See [Media URLs](#media-urls). |

Run `print(json.dumps(content, indent=2))` to see everything.

## Media URLs

Content pages include the fields the Club's own player uses. Which version they point to (promo, radio or full) depends on the [page type](#page-types).

| Field | What it is |
| --- | --- |
| `download_url` | URL of the audio or video file. |
| `stream_url` | URL of the stream the player loads. |
| `signed_cookie` | The signature the player uses to access the media. |

These URLs are signed and expire after a while. This library gives you the metadata only. It doesn't play or download media.

## Saving listening progress

`ClubClient` can update the current profile's progress on an item, just like the website's player:

```python
episode_id = "a354W0000046U7kQAE"

client.update_content_status(episode_id, progress=300000, status="In Progress")  # at 5:00
client.update_content_status(episode_id, devotional_complete=True)
client.update_content_status(episode_id, status="Completed")
```

| Argument | Description |
| --- | --- |
| `content_id` | The content to update. |
| `progress` | Playback position in **milliseconds**, as an `int`. |
| `status` | `"New"`, `"In Progress"` or `"Completed"`. |
| `devotional_complete` | `True` to mark the devotional as done. |
| `timestamp` | When this progress happened: a `datetime` or an ISO 8601 string like `"2026-10-09T21:37:54.956Z"`. Defaults to now. Naive datetimes are treated as UTC. |

Only `content_id`, `timestamp` and the arguments you pass are sent. Saved progress shows up in `content["progress"]` the next time you fetch the page.

### The response

```python
{
    "status": "Success",
    "progress": {
        "status": "In Progress",
        "dismissed_help": False,
        "devotional_complete": False,
        "current_progress": 300000,
        "content_activity_time_stamp": "2026-10-09T21:37:54.956Z"
    },
    "error": None
}
```

### Skipped updates

The server uses `timestamp` to keep updates in order, and sometimes **skips** an update. When that happens the request still succeeds (no exception), but `"status"` is `"Error"`, `"error"` says why, and `"progress"` shows what's saved. The client also logs a warning.

| `error` | Why |
| --- | --- |
| `Skipped: A more recent "In Progress" update already exists.` | The `timestamp` is older than the last saved update, e.g. another device saved progress after this one. |
| `Skipped: Activity is already complete.` | The item is already `"Completed"`. After that, updates to its progress, status and devotional are skipped, so set `devotional_complete` **before** completing. |

```python
result = client.update_content_status(episode_id, progress=120000, status="In Progress")
if result["status"] != "Success":
    print("Not saved:", result["error"])
```

Leave `timestamp` at its default unless you're replaying progress that happened earlier, such as syncing a listening log. Older items may show the status `"Complete"` instead of `"Completed"`.

## Random episode

`ClubClient` only:

```python
episode = client.fetch_random()
print(episode["short_name"])
```
