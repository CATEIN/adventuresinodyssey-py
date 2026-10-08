# Async clients

`AsyncAIOClient` and `AsyncClubClient` work exactly like [`AIOClient`](aioclient.md) and [`ClubClient`](clubclient.md): same methods, same arguments, same return values. The difference is that every method is a coroutine you `await`. They use [httpx](https://www.python-httpx.org/) instead of requests.

Use them when you want to make many requests at once, or when you're already in async code (a Discord bot, a web server, Textual).

## AsyncAIOClient

Use it as an async context manager so the connection is closed for you:

```python
import asyncio
from adventuresinodyssey import AsyncAIOClient

async def main():
    async with AsyncAIOClient() as client:
        content = await client.fetch_content("a354W0000046U7kQAE")
        print(content["short_name"])

asyncio.run(main())
```

Or manage it yourself:

```python
client = AsyncAIOClient()
await client.open()
...
await client.close()
```

## AsyncClubClient

Takes the same [constructor options](clubclient.md#constructor-options) as `ClubClient`, and logs in the same way (and shares the same [session file](clubclient.md#the-session-file) format).

```python
import asyncio
import os
from dotenv import load_dotenv
from adventuresinodyssey import AsyncClubClient

load_dotenv()

async def main():
    async with AsyncClubClient(
        email=os.getenv("AIO_EMAIL"),
        password=os.getenv("AIO_PASSWORD"),
        viewer_id=os.getenv("AIO_VIEWER_ID"),
        pin=os.getenv("AIO_PIN"),
    ) as client:
        episode = await client.fetch_random()
        print(episode["short_name"])

asyncio.run(main())
```

If you don't use `async with`, call `await client.close()` when you're done. That only closes the connection. To log out of the Club, use `await client.logout()`.

Concurrent requests are safe: if several start at once while the client isn't logged in, only one login happens and the others wait for it.

## Running requests in parallel

This is where the async clients pay off. `asyncio.gather()` runs the requests at the same time instead of one after another:

```python
import asyncio
import random
from adventuresinodyssey import AsyncAIOClient

async def main():
    async with AsyncAIOClient() as client:
        episodes = await client.cache_episodes()
        picked = random.sample(episodes, 5)

        pages = await asyncio.gather(
            *(client.fetch_content(ep["id"]) for ep in picked)
        )

        for page in pages:
            print(page["short_name"], "-", page.get("author"))

asyncio.run(main())
```

Please be considerate: avoid firing off hundreds of requests at once.

## Errors

The async clients raise httpx exceptions instead of requests ones:

| Sync | Async |
| --- | --- |
| `requests.exceptions.HTTPError` | `httpx.HTTPStatusError` |
| `requests.exceptions.Timeout` | `httpx.TimeoutException` |
