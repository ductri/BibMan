from typing import Dict
from dataclasses import dataclass
from dataclasses import field


@dataclass(init=True)
class MyEvent:
    name: str = ''
    data: Dict = field(default_factory=dict)
    source: object = None
    def x(self):
        pass


class Subscriber:
    def publisher_new_update(self, event: MyEvent):
        pass

class Publisher:
    def __init__(self):
        self.subscribers = []

    def add_listener(self, s):
        self.subscribers.append(s)

    def notify_event(self, event: MyEvent):
        for s in self.subscribers:
            s.publisher_new_state(event)
