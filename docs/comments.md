# Comments

Everything on this page needs a [`ClubClient`](clubclient.md). Comments are posted as the logged-in [profile](clubclient.md#choosing-a-profile).

Comments can be attached to [content pages](content.md) and [content groups](groupings.md) that have `enable_commenting` set to `True`. Replies are comments attached to another comment.

## related_id

Most comment methods take a `related_id`: the ID of the thing the comment belongs to.

* For a comment on a page, it's the page's ID (content or content group).
* For a reply, it's the ID of the comment being replied to.

## Reading comments

`fetch_comments(related_id)` returns a page of comments, newest first. Each comment includes its replies:

```python
corner_booth_id = "a35Up000000Qn9xIAC"

page = client.fetch_comments(related_id=corner_booth_id, page_number=1, page_size=10)

for comment in page["comments"]:
    print(f"● {comment['userName']}: {comment['message']}")
    for reply in comment.get("comments", []):
        print(f"  └── {reply['userName']}: {reply['message']}")
```

| Argument | Default | Description |
| --- | --- | --- |
| `related_id` | `None` | Page or comment ID. Leave it out to get the latest comments from the whole site. |
| `page_number` | `1` | |
| `page_size` | `10` | |
| `order_by` | `"CreatedDate DESC"` | Sort order. `"CreatedDate ASC"` gives oldest first. |

### Comment fields

| Field | Description |
| --- | --- |
| `id` | Comment ID. |
| `userName` | Who posted it. |
| `message` | The text. |
| `status` | Moderation status. New comments must be approved before others can see them. |
| `comments` | Replies (a list of comments). |
| `relatedToId`, `relatedToName`, `relatedToObject` | What it was posted on. `relatedToObject` is `"Comment"` for replies. |
| `inReplyToCommentId` | For replies, the parent comment's ID. |

## Reading one comment

`fetch_comment(comment_id, related_id)` fetches a single comment. This is handy for checking whether your comment has been approved yet:

```python
comment_id = "a2wUp000006bvQTIAY"
corner_booth_id = "a35Up000000Qn9xIAC"

result = client.fetch_comment(comment_id=comment_id, related_id=corner_booth_id)

for comment in result["comments"]:
    print("Status:", comment["status"])
    print(f"● {comment['userName']}: {comment['message']}")
    for reply in comment.get("comments", []):
        print(f"  └── {reply['userName']}: {reply['message']}")
```

Replies are only included if you pass `related_id` (the page the comment is on, or the parent comment's ID for a reply).

## Posting

```python
# Comment on a page
response = client.post_comment("What a great episode!", related_id=corner_booth_id)

# Reply to a comment
client.post_reply("I agree!", related_id=comment_id)
```

* Messages must be **under 255 characters**. See [comment_with_replies.py](../examples/comment_with_replies.py) for a way to post longer text.
* New comments are moderated, so they won't appear for others until approved.
* Please follow the Club's community guidelines, and don't spam.

## Deleting

```python
client.delete_comment(comment_id)
```

## Finding active pages

`find_comment_pages()` looks at the 100 most recent comments on the site and returns the pages they were posted on, most active first:

```python
for page in client.find_comment_pages():
    print(page["comment_count"], page["page_type"], page["name"], page["id"])
```

Replies are counted toward the page their thread is on. Each result has `id`, `name`, `page_type` (e.g. `"Content__c"`) and `comment_count`.
