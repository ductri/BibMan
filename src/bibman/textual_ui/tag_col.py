from typing import List, Dict
from typing_extensions import Self
from textual.app import App, ComposeResult
from textual.reactive import Reactive
from textual.widgets import Header, Footer, ListItem, ListView, Label, Static
from textual.reactive import reactive
from textual.message import Message
from textual import events

from anytree import Node

from bibman.utils import others
from .my_list_view import MyListView
from .observer_dp import MyEvent, Subscriber, Publisher


class TagController(Publisher):
    def __init__(self):
        super().__init__()
        default_tag_name='default'
        self.tags_dict = dict()
        self.tree_root = Node(default_tag_name, expanded=True)
        self.construct_tree(self.tree_root, self.tags_dict)
        self.flattened_nodes = self.flatten_tree(self.tree_root)

        self._selected_node = None if len(self.flattened_nodes) == 0 else self.flattened_nodes[0]
        self.default_tag_name = default_tag_name

    def update_new_data(self, tags_dict):
        self.tags_dict = tags_dict
        self.construct_tree(self.tree_root, self.tags_dict)
        self.flattened_nodes = self.flatten_tree(self.tree_root)
        self._selected_node = None if len(self.flattened_nodes) == 0 else self.flattened_nodes[0]

    def ui_init(self):
        node = self.flattened_nodes[0]
        self.my_action_choose_tag(node)
        # self.ui.update_new_data(self.flattened_nodes)

    def flatten_tree(self, root):
        flatten_nodes = []
        for node in root.children:
            flatten_nodes.append(node)
            if node.expanded:
                flatten_nodes.extend(self.flatten_tree(node))
        return flatten_nodes

    def construct_tree(self, parent, mdict):
        for k, v in mdict.items():
            node = Node(k, parent=parent, expanded=False)
            self.construct_tree(node, v)

    def my_action_expand(self, node_ind):
        chosen_node = self.flattened_nodes[node_ind]
        chosen_node.expanded = True
        self.flattened_nodes = self.flatten_tree(self.tree_root)

    def my_action_add_new_tag(self, tag_name, parent_node):
        chosen_node = parent_node
        new_tag_event = MyEvent(name='new_tag', data={'tag_name': tag_name,  'path_to_parent': others.get_path (chosen_node)}, source=self)
        self.notify_event(new_tag_event)

    # def my_action_choose_tag(self, node):
    #     tags = set(others.get_path(node).split('/'))
    #     event = MyEvent(name='choose_tags', data= {'tags': tags}, source=self)
    #     self.notify_event(event)

    def get_tags(self, index):
        node = self.flattened_nodes[index]
        tags = set(others.get_path(node).split('/'))
        return tags

    # def action_choose_tag(self, index):
    #     self.my_action_choose_tag(self.flattened_nodes[index])

    # def render(self):
    #     decorated_flatten_nodes = [' '*(node.depth-1)*2 + '▹' + node.name if node.children != () else ' '*(node.depth-1)*2 + ' ' + node.name for node in self.flattened_nodes]
    #     return decorated_flatten_nodes

    def publisher_new_state(self, event: MyEvent):
        if isinstance(event.source, DatabaseManager):
            # hard code, duplicated constant string
            if event.name == 'add_new_tag':
                print(' --- a new event received')
                # The logic here is too convoluted
                new_tree = Node(self.default_tag_name, expanded=True)
                new_tags_dict = event.data
                self.construct_tree(new_tree, new_tags_dict)

                for node in PreOrderIter(self.tree_root):
                    new_node = others.find_node(new_tree, others.get_path(node))
                    if new_node:
                        new_node.expanded = node.expanded
                self.tree_root = new_tree
                new_flatten_nodes = self.flatten_tree(self.tree_root)
                self.flattened_nodes = new_flatten_nodes

class GivingUpFocus(Message):
    def __init__(self, from_col):
        super().__init__()
        self.message = 'giving up focus'
        self.from_col = from_col


class TagColumn(Static):
    """
    - To render and to receive user input
    - It is stateless in terms of data, only stateful in terms of UI
    """

    class TagsSelection(Message):
        def __init__(self, tags):
            self.tags = tags
            super().__init__()


    BINDINGS = [
            ('enter', 'enter', 'Enter'),
            ]
    data = reactive([
                ('tag 1'),
                ('tag 2 10'),
                ('tag 100')
                ])
    def __init__(self):
        super().__init__()
        self.view = MyListView()
        self.controller = TagController()

    def compose(self) -> ComposeResult:
        yield self.view

    def focus(self, scroll_visible: bool = True) -> Self:
        self.view.focus()
        return self

    def action_move_right(self) -> None:
        self.view.blur()
        self.post_message(GivingUpFocus('from_tag'))

    def ui_update_new_data(self, data):
        decorated_flatten_nodes = [' '*(node.depth-1)*2 + '▹' + node.name if node.children != () else ' '*(node.depth-1)*2 + ' ' + node.name for node in self.controller.flattened_nodes]
        data = [ListItem(Label(item)) for item in decorated_flatten_nodes]
        self.view.clear()
        self.view.extend(data)

    def action_ui_select_tag(self, index):
        pass

    def on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            chosen_ind = self.view.index
            tags = self.controller.get_tags(chosen_ind)
            self.post_message(TagColumn.TagsSelection(tags))

    def action_select_tag(self, tags):
        self.post_message(TagColumn.TagsSelection(tags))

    def update_new_data(self, data: Dict):
        self.controller.update_new_data(data)
        self.ui_update_new_data(data)
        self.view.index = 0
        self.action_select_tag(set(['default']))



