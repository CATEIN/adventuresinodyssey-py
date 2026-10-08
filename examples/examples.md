# Example programs

Complete programs that use the library. Install the package first (`pip install adventuresinodyssey`), plus any extra packages each example lists.

Several examples play audio with [mpv](https://mpv.io/). You need both the mpv program and its Python bindings:

```bash
pip install mpv
```

On Windows, download mpv and add its folder to your `PATH` (or put `libmpv-2.dll` next to the script).

## No account needed (AIOClient)

| Example | What it does | Extra packages |
| --- | --- | --- |
| [bedtime.py](bedtime.py) | Plays the newest radio episode every night at 8:00. | `mpv`, `schedule` |
| [promotrivia.py](promotrivia.py) | Trivia game: guess the episode from its promo. | `mpv` |
| [thumbnail.py](thumbnail.py) | Downloads the thumbnail for a content page. | |

Run `thumbnail.py` with a content URL:

```bash
python thumbnail.py https://app.adventuresinodyssey.com/content/a354W0000046U7kQAE
```

## Club account needed (ClubClient)

| Example | What it does | Extra packages |
| --- | --- | --- |
| [player.py](player.py) | A terminal music player with a queue. Caches episode metadata so audio loads faster. | `mpv`, `textual` |
| [comment_with_replies.py](comment_with_replies.py) | Posts text longer than the 255-character limit by splitting it into a comment plus replies. Moderators may not approve every reply. | |

These read your login from a `.env` file in the same folder (`pip install python-dotenv`):

```bash
AIO_EMAIL=you@example.com
AIO_PASSWORD=your_password
AIO_VIEWER_ID=your_profile_id    # see "Finding your viewer ID" in the ClubClient docs
AIO_PIN=1234                     # or 0000 if the profile has no PIN

# Alternative to AIO_VIEWER_ID (slower):
AIO_PROFILE_USERNAME=your_profile_username
```

Don't commit `.env` or `club_session.json` to git. See [ClubClient → Finding your viewer ID](../docs/clubclient.md#finding-your-viewer-id).
