from typing import List
from textual.app import App, ComposeResult
from textual.reactive import Reactive
from textual.widgets import Header, Footer, ListItem, ListView, Label, Static
from textual.reactive import reactive


class MyListView(ListView):
    BINDINGS = [("k", "cursor_up", "move up"),
                ("j", "cursor_down", "move down")
                ]

