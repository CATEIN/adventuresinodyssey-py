# Playlists and bookmarks

Everything on this page needs a [`ClubClient`](clubclient.md). Playlists and bookmarks belong to the logged-in [profile](clubclient.md#choosing-a-profile).

Playlists are [content groupings](groupings.md) of type `"Playlist"`, so they have the same shape as albums: the playlist is at `["contentGroupings"][0]` and its items are in `contentList`.

## Your playlists

```python
playlists = client.fetch_playlists(page_number=1, page_size=25)

for playlist in playlists["contentGroupings"]:
    print(playlist["name"], playlist["id"], len(playlist["contentList"]), "items")
```

## Creating a playlist

```python
result = client.create_playlist(
    name="Road Trip",
    content_ids=["a354W0000046U7kQAE", "a354W0000046U6IQAU"],
    image_url="",          # optional cover image URL
)

playlist_id = result["contentGroupings"][0]["id"]
print("https://app.adventuresinodyssey.com/playlists/" + playlist_id)
```

`create_playlist()` returns the API response (a dict), not just the ID.

If you need full control, pass the whole request body as `playlist_json`, and the other arguments are ignored:

```python
client.create_playlist(playlist_json={
    "contentGroupings": [
        {"name": "Road Trip", "imageURL": "", "contentList": [{"id": "a354W0000046U7kQAE"}]}
    ]
})
```

## Updating a playlist

`update_playlist()` takes the **whole playlist response** (not just the ID), changes it, and saves it. Get it from `fetch_content_group()`:

```python
playlist = client.fetch_content_group(playlist_id)

client.update_playlist(playlist, add_ids="a354W0000046U92QAE")                # add one
client.update_playlist(playlist, add_ids=["id1", "id2"])                      # add several
client.update_playlist(playlist, remove_ids="a354W0000046U6IQAU")             # remove
client.update_playlist(playlist, name="Road Trip 2026")                       # rename
client.update_playlist(playlist, content_ids=["id1", "id2", "id3"])           # replace everything
```

| Argument | Description |
| --- | --- |
| `playlist` | The response from `fetch_content_group()`. It's modified in place. (For an item from `fetch_playlists()`, wrap it: `{"contentGroupings": [item]}`.) |
| `name` | New name. |
| `image_url` | New cover image URL. |
| `add_ids` | ID or list of IDs to add to the end. Items already in the playlist are skipped. |
| `remove_ids` | ID or list of IDs to remove. |
| `content_ids` | List of IDs that replaces the whole list. If given, `add_ids` and `remove_ids` are ignored. |

You can combine arguments, e.g. `update_playlist(playlist, name="New name", add_ids="...")`.

## Deleting a playlist

```python
client.delete_playlist(playlist_id)
```

## Bookmarks

```python
client.bookmark("a354W0000046U7kQAE")

bookmarks = client.fetch_bookmarks()
for item in bookmarks["results"]:
    print(item["short_name"])
```

`fetch_bookmarks()` returns content in the same format as [`fetch_radio()`](browsing.md#radio-schedule): a `results` list.
