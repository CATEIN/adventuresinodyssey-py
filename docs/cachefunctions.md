# Cache functions

The cache functions download an entire catalog (every episode, every album) and return it as one flat Python `list`. They take care of pagination for you and work on every client.

They're called "cache" functions because you'll usually call them once at startup and keep the result, rather than calling them for every lookup. Each one takes a few seconds.

```python
from adventuresinodyssey import AIOClient

client = AIOClient()

episodes = client.cache_episodes()
print(len(episodes), "episodes")   # ~1000+

# Look up episodes by number
by_number = {ep["short_name"].split(":")[0]: ep for ep in episodes}
print(by_number["#125"]["name"])   # All's Well With Boswell
```

If you want to keep the data between runs, save it to a file:

```python
import json

with open("episodes.json", "w", encoding="utf-8") as f:
    json.dump(episodes, f)
```

## cache_episodes

```python
cache_episodes(grouping_type="Album", include_bonus=False)
```

Returns every **audio** item in every grouping of `grouping_type`. Each item is a `contentList` entry (see [grouping fields](groupings.md#grouping-fields)) with one extra key, `album_id`: the ID of the grouping it came from.

| Argument | Default | Description |
| --- | --- | --- |
| `grouping_type` | `"Album"` | Which [grouping type](groupings.md#grouping-types) to collect episodes from. |
| `include_bonus` | `False` | Include items whose name starts with `"BONUS"`. |

Non-audio items (videos, articles) are skipped. The items have basic fields only, so call `fetch_content(ep["id"])` when you need the description, characters, etc.

## cache_albums

```python
cache_albums(grouping_type="Album", include_club_exclusive=True)
```

Returns every grouping of `grouping_type` (each with its `contentList`).

| Argument | Default | Description |
| --- | --- | --- |
| `grouping_type` | `"Album"` | Any [grouping type](groupings.md#grouping-types), or `"Themes"` to get one grouping per theme instead (see [below](#cache_content_groupings)). |
| `include_club_exclusive` | `True` | If `False`, leave out albums only available to Club members: those named "Club Season" or "The Officer Harley Collection", and albums #81 and up. |

## cache_audiobooks

```python
cache_audiobooks()
```

Returns every audiobook, in the Club's order. Items have the same fields as [`fetch_radio()`](browsing.md#radio-schedule) results.

## cache_content_groupings

```python
cache_content_groupings(generate_themes=False)
```

Returns every grouping of **every** type (albums, collections, series, seasons, life lessons...) in one list. Check each item's `type` to tell them apart.

| Argument | Default | Description |
| --- | --- | --- |
| `generate_themes` | `False` | Also add one grouping per theme (`type` `"Theme"`), containing every episode tagged with it. |

Theme generation makes about 10 extra requests to look up episode tags, so it takes a few seconds longer. `cache_albums(grouping_type="Themes")` returns *only* the generated themes, built from albums.
