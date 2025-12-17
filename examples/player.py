import os
import random
from datetime import timedelta
from dotenv import load_dotenv

from adventuresinodyssey import ClubClient
from adventuresinodyssey import set_logging_level
import mpv

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, ListItem, ListView, Label, Button, Input
from textual.containers import Horizontal, Vertical
from textual.binding import Binding

load_dotenv()
set_logging_level('INFO')

class OdysseyTUI(App):
    CSS = """
    #top_bar {
        height: 3;
        margin: 1;
    }
    #search_box { width: 3fr; }
    #btn_random { width: 1fr; margin-left: 1; }

    #main_content { height: 1fr; }
    #episode_table { width: 3fr; border: tall $primary; }
    #queue_panel { width: 1fr; border: tall $secondary; background: $surface; }
    
    #player_area {
        height: 10; 
        border: tall $accent;
        background: $surface;
        margin: 1;
        padding: 1;
    }
    
    .status-text {
        text-align: center;
        width: 100%;
        text-style: bold;
    }
    
    #percentage_label {
        color: $warning;
        margin: 0 0 1 0;
    }

    #controls_row {
        align: center middle;
        height: 3;
        width: 100%;
    }
    Button { margin: 0 1; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("space", "toggle_pause", "Play/Pause"),
        Binding("n", "next_track", "Skip"),
        Binding("left", "seek_backward", "-15s"),
        Binding("right", "seek_forward", "+15s"),
        Binding("/", "focus_search", "Search"),
        Binding("r", "play_random", "Random"),
    ]

    def __init__(self):
        super().__init__()
        self.player = mpv.MPV(ytdl=False, video="no")
        self.player.http_header_fields = ["Sec-Fetch-Dest: audio"]
        
        self.client = None
        self.all_episodes = []
        self.filtered_episodes = [] 
        self.queue = [] 
        self.current_cookie = ""

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="top_bar"):
            yield Input(placeholder="Search episodes... (Press /)", id="search_box")
            yield Button("Shuffle Random (R)", id="btn_random", variant="success")

        with Horizontal(id="main_content"):
            yield DataTable(id="episode_table")
            with Vertical(id="queue_panel"):
                yield Label("PLAY QUEUE", variant="header")
                yield ListView(id="queue_list")
        
        with Vertical(id="player_area"):
            yield Label("Logging in...", id="now_playing", classes="status-text")
            yield Label("0% Remaining", id="percentage_label", classes="status-text")
            with Horizontal(id="controls_row"):
                yield Button("Pause", id="btn_pause", variant="warning")
                yield Button("Skip", id="btn_skip", variant="primary")
                yield Button("Stop", id="btn_stop", variant="error")
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self.setup_odyssey, thread=True)
        self.set_interval(1, self.update_status)
        self.query_one("#episode_table").focus()

    def setup_odyssey(self) -> None:
        try:
            self.client = ClubClient(
                email=os.getenv("AIO_EMAIL"),
                password=os.getenv("AIO_PASSWORD"),
                profile_username=os.getenv("AIO_PROFILE_USERNAME"),
                pin=os.getenv("AIO_PIN"),
            )
            self.all_episodes = self.client.cache_episodes()
            self.filtered_episodes = list(self.all_episodes)
            self.current_cookie = self.client.fetch_signed_cookie('audio')
            self.call_from_thread(self.populate_table)
        except Exception as e:
            self.notify(f"Login Failed: {e}", severity="error")

    def populate_table(self, episodes_to_show=None) -> None:
        table = self.query_one("#episode_table", DataTable)
        table.clear(columns=True)
        table.add_columns("Title", "Album", "Duration")
        table.cursor_type = "row"

        display_list = episodes_to_show if episodes_to_show is not None else self.all_episodes

        for idx, ep in enumerate(display_list):
            ms = ep.get("media_length", 0)
            duration = str(timedelta(milliseconds=ms)).split(".")[0][2:]
            table.add_row(ep.get("short_name", "Unknown"), ep.get("album_name", "Unknown"), duration, key=str(idx))
        
        self.query_one("#now_playing").update("Ready")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search_box":
            query = event.value.lower()
            self.filtered_episodes = [
                ep for ep in self.all_episodes 
                if query in ep.get("short_name", "").lower() or query in ep.get("album_name", "").lower()
            ]
            self.populate_table(self.filtered_episodes)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """When pressing Enter in search, focus the table for scrolling."""
        self.query_one("#episode_table").focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        index = int(event.row_key.value)
        episode = self.filtered_episodes[index]
        self.add_to_queue(episode)

    def add_to_queue(self, episode):
        self.queue.append(episode)
        self.query_one("#queue_list").append(ListItem(Label(episode['short_name'])))
        if not self.player.filename:
            self.play_next()

    def play_next(self):
        if not self.queue:
            self.query_one("#now_playing").update("Queue Empty")
            self.query_one("#percentage_label").update("0% Remaining")
            self.player.stop()
            return

        episode = self.queue.pop(0)
        try:
            self.query_one("#queue_list").pop(0)
        except: pass

        url = "https://media.adventuresinodyssey.com/" + episode["download_url"] + self.current_cookie
        self.query_one("#now_playing").update(f"Playing: {episode['short_name']}")
        self.player.play(url)

    def update_status(self):
        if self.player.time_pos is not None and self.player.duration is not None:
            time_left = self.player.duration - self.player.time_pos
            percent_remaining = (time_left / self.player.duration) * 100
            self.query_one("#percentage_label").update(f"{int(percent_remaining)}% Remaining")
            
            if percent_remaining < 0.5:
                self.play_next()

    def action_play_random(self):
        if self.all_episodes:
            episode = random.choice(self.all_episodes)
            self.notify(f"Added Random: {episode['short_name']}")
            self.add_to_queue(episode)

    def action_focus_search(self):
        self.query_one("#search_box").focus()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn_random": self.action_play_random()
        elif event.button.id == "btn_pause": self.action_toggle_pause()
        elif event.button.id == "btn_skip": self.play_next()
        elif event.button.id == "btn_stop":
            self.player.stop()
            self.query_one("#now_playing").update("Stopped")

    def action_seek_forward(self):
        if self.player.filename: self.player.seek(15)

    def action_seek_backward(self):
        if self.player.filename: self.player.seek(-15)

    def action_toggle_pause(self):
        self.player.pause = not self.player.pause
        self.query_one("#btn_pause").label = "Play" if self.player.pause else "Pause"

    def action_next_track(self):
        self.play_next()

if __name__ == "__main__":
    app = OdysseyTUI()
    app.run()