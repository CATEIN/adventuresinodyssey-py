# Example programs

# AIOClient

## [bedtime.py](/examples/bedtime.py)
Plays the newest radio episode every night at 8:00. Requires `mpv` and `schedule`

```bash
pip install mpv
```

```bash
pip install schedule
```

*windows users have to add mpv to PATH or include it in the project folder to use it.

## [promotrivia.py](/examples/promotrivia.py)
A simple trivia game where the user guesses the name of an episode based on promo being played. Requires `mpv`

```bash
pip install mpv
```

*windows users have to add mpv to PATH or include it in the project folder to use it.

## [thumbnail.py](/examples/thumbnail.py)
Download the thumbnail for a content page.

Usage:

```bash
python thumbnail.py content_url_here
```
(make sure the url is a content url! https://app.adventuresinodyssey.com/content/... )

# ClubClient

These programs require `python-dotenv` and .env file like:

```bash
AIO_EMAIL=email_here
AIO_PASSWORD=password_here
AIO_PROFILE_USERNAME=username_here
AIO_PIN=pin_here_or_0000
# optional but good
AIO_VIEWER_ID=profile_id_here
```

## [player.py](/examples/player.py)

A simple player in the terminal with a queue system. Reqiures `mpv` and `textual`


```bash
pip install mpv
```

```bash
pip install textual
```
