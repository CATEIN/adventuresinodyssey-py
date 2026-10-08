# Browsing

Methods for the parts of the Club you'd browse rather than look up by ID. All of these work on `AIOClient` and `ClubClient`.

## Radio schedule

`fetch_radio()` returns radio episodes that have aired recently or are coming up next:

```python
from adventuresinodyssey import AIOClient

client = AIOClient()

aired = client.fetch_radio(page_type="aired", page_size=5)        # newest first
upcoming = client.fetch_radio(page_type="upcoming", page_size=5)  # soonest first

for episode in aired["results"]:
    print(episode["relative_air_day"], "-", episode["short_name"])
    # Aired Today - #373: For Whom the Wedding Bells Toll, Part 2 of 3
```

| Argument | Default | Description |
| --- | --- | --- |
| `page_type` | `"aired"` | `"aired"` or `"upcoming"`. Anything else raises `ValueError`. |
| `page_number` | `1` | |
| `page_size` | `5` | |

Each result has `id`, `short_name`, `relative_air_day` (e.g. `"Airing Tomorrow"`), `recent_air_date`, `description` and most other content fields.

Episodes that have aired can be fetched with `fetch_content(id, page_type="radio")` to get their radio page, even without logging in.

## New content

The most recently published content of any type:

```python
new = client.fetch_new_content(page_size=10)

for item in new["results"]:
    print(item["last_published_date"][:10], item["type"], "-", item["short_name"])
```

`fetch_radio()` and `fetch_new_content()` both return `results`, `total_count` and `total_pages`.

## Characters

```python
page = client.fetch_characters(page_size=200)  # default page size is 200

for character in page["characters"]:
    print(character["nickname"], character["id"])
```

The list only has names and thumbnails. `fetch_character()` has everything else:

```python
whit = client.fetch_character("a2t4W000005cKTMQA2")["characters"][0]

print(whit["name"])           # John Avery Whittaker
print(whit["voiced_by"])      # Andre Stojka
print(whit["appearances"])    # number of episodes
print(whit["character_bio"])

for item in whit["get_to_know_in"]:   # also: featured_in, series_with
    print("  ", item["short_name"])
```

## Cast and crew

The API calls cast and crew *authors*.

```python
page = client.fetch_cast_and_crew(page_size=25)

for person in page["authors"]:
    print(person["name"], person["id"])

phil = client.fetch_author("a2m4W000006CVw2QAG")["authors"][0]
print(phil["name"], "-", phil["publishedPieces"], "pieces")
print(phil["bio"])  # HTML
```

## Home page

```python
home = client.fetch_home_playlists()
for group in home["playlists"]:
    print(group["name"])

carousel = client.fetch_carousel()
for slide in carousel["carousel"]:
    print(slide["imageUrl"], "->", slide["hyperlink"])
```

`fetch_home_playlists()` returns the groupings featured on the home page, and `fetch_carousel()` returns the banner slides at the top.
