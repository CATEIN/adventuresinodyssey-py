# Comments

Comments can be viewed on [Content](https://github.com/CATEIN/adventuresinodyssey-py/blob/main/docs/content.md#content) and [Content Groups](https://github.com/CATEIN/adventuresinodyssey-py/blob/main/docs/groupings.md#content-group).
Comments can be posted if `enable_commenting` is true. Available for [ClubClient](https://github.com/CATEIN/adventuresinodyssey-py/blob/main/docs/clubclient.md) only.

# Get Comments

Comments can be fetched by `related_id` with `fetch_comments()`:

```python
import os
from dotenv import load_dotenv
from adventuresinodyssey import ClubClient

load_dotenv()
# Enables ANSI colors on older Windows terminals
os.system("")

client = ClubClient(
    email=os.getenv("AIO_EMAIL"),
    password=os.getenv("AIO_PASSWORD"),
    viewer_id=os.getenv("AIO_VIEWER_ID"),
    pin=os.getenv("AIO_PIN"),
)

corner_booth_id = "a35Up000000Qn9xIAC"
BOLD = "\033[1m"
RESET = "\033[0m"

comments = client.fetch_comments(
    related_id=corner_booth_id, page_number=2, page_size=10
)

for comment in comments["comments"]:
    print(f"\n● {BOLD}{comment['userName']}{RESET}")
    print(f"  {comment['message']}")

    for reply in comment.get("comments", []):
        print(f"  └── {BOLD}{reply['userName']}{RESET}: {reply['message']}")
```

# Get a Comment

A single comment can be fetched by `comment_id` with `fetch_comment()`. For replies to show up, `related_id` must also be given (`related_id` is page the comment was posted to, if the comment is a reply the `related_id` is the original comment's `id`). This is useful for checking if a comment was approved or has replies.

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

comment_id = "a2wUp000006bvQTIAY"
corner_booth_id = "a35Up000000Qn9xIAC"

comment_data = client.fetch_comment(comment_id=comment_id, related_id=corner_booth_id)

for main_comment in comment_data.get("comments", []):
    # Print the parent comment details
    print(f"Status: {main_comment.get('status')}")
    print(f"● {main_comment['userName']}: {main_comment['message']}")

    # Loop through the nested replies (only avalible if related_id is given)
    for reply in main_comment.get("comments", []):
        print(f"  └── {reply['userName']}: {reply['message']}")
```
