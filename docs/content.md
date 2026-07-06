# Content
Content pages on the club can be fetched using the `fetch_content()` function, provided you supply a `content_id` and optionally a `page_type` (`full`, `radio`, `promo`). `page_type` defaults to `promo` on `AIOClient`, while `ClubClient` defaults to `full`.
Known content pages `type`'s are:
* Audio
* Video
* Article
* Book
* Download


Example:
```python
from adventuresinodyssey import AIOClient # or ClubClient
client = AIOClient() 

page_id = "a354W0000046U7kQAE" #125: All's Well With Boswell

content = client.fetch_content(page_id, page_type="promo")

print(content["type"]) # this should print Audio. Try changing it to one of the fields in the json below.
```
The response json will look something like this (Note that data may vary between different page types):

```json
{
    "views": 13636,
    "type": "Audio",
    "title_url": "all's-well-with-boswell",
    "thumbnail_small": "https://d23sy43gbewnpt.cloudfront.net/public/images/content/all's_well_with_boswell_(0-00-00-00)-sm.jpg",
    "thumbnail_medium": "https://d23sy43gbewnpt.cloudfront.net/public/images/content/all's_well_with_boswell_(0-00-00-00)-med.jpg",
    "thumbnail_large": "https://d23sy43gbewnpt.cloudfront.net/public/images/content/all's_well_with_boswell_(0-00-00-00).jpg",
    "tags": [
        {
            "topic_id": "a3H4W000004Ohw7UAC",
            "name": "Responsibility",
            "id": "a334W000000rJboQAE"
        }
    ],
    "subtype": "Episode",
    "stream_url": "https://media.adventuresinodyssey.com/private/audio/episode/...",
    "signed_cookie": "https://media.adventuresinodyssey.com/private/audio/episode/9781604821246/full/AppleHLS1/*...",
     "id": "a354W0000046U7kQAE",
    "has_devotional": true,
    "extras": [],
    "episode_number": "125",
    "download_url": "https://media.adventuresinodyssey.com/private/audio/episode/...",
    "devotional": "<div class=\"aioc-devotional\">\n<p>It’s the simplest job in the world: feed the goldfish...",
    "description": "When Robyn gets her first real babysitting job, it turns out to be more of an adventure than she could ever imagine!",
    "short_name": "#125: All's Well With Boswell",
    "relative_air_day": "Aired 10/23/2025",
    "recent_air_date": "2025-10-23T06:00:00.000Z",
    "rating_count": 1984,
    "rating_average": 4.0,
    "bible_verse": "Luke 16:10-12",
    "author": "Phil Lollar",
    "album_name": "#08: Beyond Expectations",
    "air_date": "1990-08-25T06:00:00.000Z",
    "authors": [
        {
            "role": "Writer",
            "recommended_by_author": null,
            "read_only": null,
            "publishedPieces": null,
            "profileImageUrl": null,
            "name": "Phil Lollar",
            "isHighlighted": null,
            "is_bookmarked": null,
            "id": "a2m4W000006CVw2QAG",
            "bio": null,
            "aioPriority": null
        }
    ],
    "characters": [
            {
                "voiced_by_id": null,
                "voiced_by": null,
                "thumbnail_small": "https://d23sy43gbewnpt.cloudfront.net/public/images/character/tom_2026_thumbnail-sm.png",
                "thumbnail_medium": "https://d23sy43gbewnpt.cloudfront.net/public/images/character/tom_2026_thumbnail-med.png",
                "thumbnail_large": "https://d23sy43gbewnpt.cloudfront.net/public/images/character/tom_2026_thumbnail.png",
                "thumbnail_alternative_text": null,
                "series_with": null,
                "photos": null,
                "nickname": "Tom",
                "name": "Tom Riley",
                "job": null,
                "id": "a2t4W000005cKSdQAM",
                "get_to_know_in": null,
                "first_name": null,
                "featured_in": null,
                "description": null,
                "character_bio": null,
                "appearances": null
            }
    ],
    "recommendations": [
        {
            "views": 12937,
            "type": "Audio",
            "title_url": "harley-takes-the-case,-part-1-of-2",
            "thumbnail_small_alternate": null,
            "thumbnail_small": "https://d23sy43gbewnpt.cloudfront.net/public/images/content/25_-_harley_takes_the_case_part_1_thumbnail-sm.jpg",
            "thumbnail_medium": "https://d23sy43gbewnpt.cloudfront.net/public/images/content/25_-_harley_takes_the_case_part_1_thumbnail-med.jpg",
            "tags": [
                {
                    "topic_id": "a3H4W000004Ohw7UAC",
                    "name": "Responsibility",
                    "id": "a334W000000rLt6QAE"
                }
            ],
            "subtype": "Episode",
            "store_path": null,
            "store_link_type": null,
            "store_link": null,
            "short_name": "#025: Harley Takes the Case, Part 1 of 2",
            "shares": 0,
            "share_origin": null,
            "share_hidden": false,
            "share_access": null,
            "relative_air_day": null,
            "recent_air_date": null,
            "rating_count": 788,
            "rating_average": 4.3,
            "promo_url": null,
            "progress": {
                "status": "New",
                "dismissed_help": null,
                "devotional_complete": null,
                "current_progress": 0,
                "content_activity_time_stamp": null
            },
            "name": "Harley Takes the Case, Part 1 of 2",
            "media_variant": "full",
            "media_length": 180000,
            "link_to_object": "Content__c",
            "link_to_id": "a354W0000046Tn2",
            "likes": 0,
            "last_viewed_date": null,
            "last_published_date": "1988-05-07T06:00:00.000Z",
            "is_liked": null,
            "is_bookmarked": false,
            "id": "a354W0000046Tn2QAE",
            "has_devotional": true,
            "episode_number": "025",
            "download_url": null,
            "devotional_theme": null,
            "devotional": "You might assume that criminals who spend weeks planning the perfect crime wo...",
            "description_for_item_in_content_grouping": null,
            "description": "Officer David Harley tries to find a missing boy named Steve Larson.",
            "content_link_override_is_external": false,
            "content_link_base_domain_override": null,
            "church_leader_guest": false,
            "brand": null,
            "bookmarks": 1633,
            "bc_rating_count": 0,
            "bc_rating_average": 0,
            "authors": [],
            "author_id": null,
            "author": null,
            "album_name": "The Officer Harley Collection",
            "air_date": "1988-05-07T06:00:00.000Z",
            "aioc_guest": true,
            "access_start": null,
            "access_end": null
        }
    ]
}
```
# Sending progress to the club
`ClubClient` can send the current state and progress of content with the `update_content_status()` function. `progress` is in milliseconds. `status` can be `New`, `In Progress` or `Completed`. Complete devotionals with `devotional_complete=True`
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

episode = "a354W0000046U7kQAE" #125: All's Well With Boswell

progress = client.update_content_status(content_id=episode, progress="300000", status="In Progress")
print(progress)
```

