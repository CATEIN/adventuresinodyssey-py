# Groupings

A *content grouping* (or *content group*) is a list of content: an album, a series, a collection, a playlist, and so on. Every grouping has a `type`, a `name` and a `contentList` of content items.

## Listing groupings by type

`fetch_content_groupings()` returns one page of groupings of a single type:

```python
from adventuresinodyssey import AIOClient  # or ClubClient

client = AIOClient()

page = client.fetch_content_groupings(grouping_type="Album", page_number=1, page_size=5)

for album in page["contentGroupings"]:
    print(album["name"], "-", len(album["contentList"]), "items")

print("Total albums:", page["metadata"]["totalRecordCount"])
```

| Argument | Default | Description |
| --- | --- | --- |
| `grouping_type` | `"Album"` | One of the types below. |
| `page_number` | `1` | Page to fetch, starting at 1. |
| `page_size` | `25` | Groupings per page. |
| `order_by` | `None` | Sent to the API as `orderBy`. |
| `payload` | `None` | A complete request body to send instead. Overrides all the other arguments. |

### Grouping types

| `grouping_type` | What it is | Example |
| --- | --- | --- |
| `"Album"` | Numbered albums | `#73: 28 Hours` |
| `"Episode Home"` | Episodes in blocks of 50 | `Episodes 1 to 50` |
| `"Season"` | Season groupings | `Season 10` |
| `"Series"` | Multi-album story arcs | `The Blackgaard Chronicles` |
| `"Collection"` | Curated collections, soundtracks | `Odyssey Studio Insiders` |
| `"Podcast Year"` | Podcasts by year | `2006` |
| `"Bonus Video Home"` | Video collections | `Adventures in Odyssey Impact Stories` |
| `"Life Lesson"` | Episodes grouped by lesson | `Adaptability` |
| `"Book Series"` | Book series | `The Imagination Station` |
| `"Curriculum"` | Study guides | `New to Odyssey? - Adventures in Odyssey Jumpstart!` |
| `"Playlist"` | User playlists. Use [`fetch_playlists()`](playlists.md) instead. | |

To get every grouping of a type without paging, use [`cache_albums()`](cachefunctions.md#cache_albums).

### Grouping fields

| Field | Description |
| --- | --- |
| `id` | Grouping ID. |
| `name` | e.g. `"#73: 28 Hours"`. |
| `type` | The grouping type. |
| `description`, `full_description` | Text. |
| `imageURL` | Cover image. |
| `contentList` | The items. Each has `id`, `name`, `short_name`, `type`, `subtype`, `media_length`, `download_url` and more, but **not** `tags`. Call `fetch_content()` for full details. |
| `album_number`, `album_copyright_year` | Albums only. |
| `total_runtime` | Total length in milliseconds (only filled in by `fetch_content_group()`). |

## A single group

`fetch_content_group()` fetches one grouping by ID. The result is still wrapped in a list:

```python
group = client.fetch_content_group("a314W000000CVR1QAO")  # #73: 28 Hours
album = group["contentGroupings"][0]

print(album["name"])
for item in album["contentList"]:
    print(" ", item["short_name"])
```

## Themes

Themes (called *topics* by the API) are organized in two levels, for example *Building Character → Compassion*.

```python
themes = client.fetch_themes(page_size=25)

for theme in themes["topics"]:
    print(theme["name"])
    for sub in theme["subtopics"]:
        print("  ", sub["name"], sub["id"])
```

Fetch one theme (usually a sub-theme) to get content tagged with it:

```python
compassion = client.fetch_theme("a3H4W000004OhrbUAC")["topics"][0]

print(compassion["parent_name"], "->", compassion["name"])
for item in compassion["recommendations"]:
    print("  ", item["short_name"])
```

The `topic_id` in a content page's `tags` is a theme ID you can pass to `fetch_theme()`.

## Badges

Badges (also called *adventures*) are `ClubClient` only.

```python
badges = client.fetch_badges(page_number=1, page_size=5)

for badge in badges["badges"]:
    print(badge["name"], badge["id"])

badge = client.fetch_badge(badges["badges"][0]["id"])["badges"][0]
for requirement in badge["requirements"]:
    print("  ", requirement["name"])
```
