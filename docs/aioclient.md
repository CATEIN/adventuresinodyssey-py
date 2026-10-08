# AIOClient

`AIOClient` reads public data, the same things the website shows to visitors who aren't logged in. It needs no account and no setup.

```python
from adventuresinodyssey import AIOClient

client = AIOClient()  # optional: AIOClient(timeout=30), in seconds, default 10

content = client.fetch_content("a354W0000046U7kQAE")
print(content["short_name"])   # #125: All's Well With Boswell
print(content["description"])
```

## What it can do

* [Content](content.md): metadata for any episode, video, article, etc. as a `"promo"` or `"radio"` page
* [Groupings](groupings.md): albums, series, collections, themes
* [Browsing](browsing.md): radio schedule, new releases, characters, cast and crew, home page
* [Search](search.md)
* [Cache functions](cachefunctions.md): every episode or album in one call
* [Low-level requests](docs.md#low-level-requests): `get()` and `post()`

See the [function reference](docs.md#function-reference) for the full list.

## What it can't do

These need a [`ClubClient`](clubclient.md):

* `fetch_content(..., page_type="full")`, which raises `ValueError` on `AIOClient`
* playlists, bookmarks, comments, badges, progress, `fetch_random()`

## Page types

Without logging in, `fetch_content()` can return the `"promo"` page (the default) or, for episodes in the current [radio rotation](browsing.md#radio-schedule), the `"radio"` page. See [Content → Page types](content.md#page-types).
