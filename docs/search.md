# Search

Search works on `AIOClient` and `ClubClient`.

## Simple search

`search(query)` searches content (episodes, videos, etc.) and returns the first 10 results:

```python
from adventuresinodyssey import AIOClient

client = AIOClient()

results = client.search("boswell")

for item in results["resultObjects"][0]["results"]:
    print(item["name"], item["id"])
```

## Searching other things

Pass an object name as the second argument to search something else:

```python
results = client.search("whit", "character")
```

| Object name | Searches | Result fields |
| --- | --- | --- |
| `"content"` | Episodes, videos, articles... | `id`, `name`, `subtype`, `episode_number`, `thumbnail_small` |
| `"content_grouping"` | Albums, collections, series... | `id`, `name`, `type`, `image_url` |
| `"character"` | Characters | `id`, `name`, `thumbnail_small` |
| `"author"` | Cast and crew | `id`, `name`, `profile_image_url` |
| `"topic"` | Themes | `id`, `name` |
| `"badge"` | Badges | `id`, `name`, `icon`, `type` |

Names aren't case-sensitive, and the API's own names (`"Content__c"`, `"Content_Grouping__c"`...) work too.

To search several types at once, or to page through results, pass a list of dictionaries:

```python
results = client.search("whit", [
    {"objectName": "character", "pageSize": 5},
    {"objectName": "content", "pageSize": 20, "pageNumber": 2},
])

for group in results["resultObjects"]:
    print(f"== {group['objectLabel']} (more: {group['metadata']['hasMoreResults']})")
    for item in group["results"]:
        print("  ", item["name"])
```

`pageNumber` defaults to 1 and `pageSize` to 10.

## Search everything

`search_all(query)` searches all six types at once, returning up to 9 results of each:

```python
results = client.search_all("eugene")

for group in results["resultObjects"]:
    print(group["objectLabel"], len(group["results"]))
```

## Response format

```text
{
    "searchTerm": "boswell",
    "resultObjects": [
        {
            "objectName": "Content__c",
            "objectLabel": "Content",
            "metadata": {"pageNumber": 1, "pageSize": 10, "hasMoreResults": None, ...},
            "results": [
                {
                    "id": "a354W0000046U7kQAE",
                    "name": "All's Well With Boswell",
                    "episode_number": "125",
                    "subtype": "Episode",
                    "thumbnail_small": "https://..."
                }
            ]
        }
    ]
}
```

There's one entry in `resultObjects` per type searched. Results only include a few fields. Use the `id` with `fetch_content()`, `fetch_character()`, etc. for the full details.
