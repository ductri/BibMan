import curses
from anytree import Node, PreOrderIter
from anytree.resolver import Resolver, ChildResolverError
import datetime
import itertools

from bibman.base import ScrollableList
from bibman.utils import others


class TreeList(ScrollableList):
    def construct_tree(parent, mdict):
        for k, v in mdict.items():
            node = Node(k, parent=parent, expanded=False)
            TreeList.construct_tree(node, v)

    def __init__(self, database, pos, mdict=dict(), is_on_focus=False, default_tag_name='default'):
        """
        This class does too much business than it should!
        """

        nlines, ncols, begin_line, begin_col = pos
        self.database = database
        self.mdict = mdict
        self.tree = Node(default_tag_name, expanded=True)
        TreeList.construct_tree(self.tree, mdict)
        self.flatten_nodes = TreeList.render_tree(self.tree)
        ScrollableList.__init__(self, pos, [item.name for item in self.flatten_nodes], visible_off_focus=True, is_on_focus=is_on_focus)
        self.win.bkgd(curses.color_pair(2))
        self.channels = dict()
        self._selected_node = None if len(self.flatten_nodes) == 0 else self.flatten_nodes[0] # The `selected node` could be different from the `chosen_ind` node, it is the item at the ENTER event.
        self.muted_nodes= []

    def __decorate_nodes(nodes):
        decorated_flatten_nodes = [' '*(node.depth-1)*2 + '▹' + node.name if node.children != () else ' '*(node.depth-1)*2 + ' ' + node.name for node in nodes]
        return decorated_flatten_nodes


    def lost_focus(self):
        ScrollableList.lost_focus(self)
        event = {'name': 'LOST_FOCUS', 'owner': 'tree'}
        self.broadcast(event, 0)
        self.broadcast(event, 1)

    def expand(self):
        chosen_node = self.flatten_nodes[self.get_single_chosen_item()]
        chosen_node.expanded = True
        self.flatten_nodes = TreeList.render_tree(self.tree)
        decorated_flatten_nodes = TreeList.__decorate_nodes(self.flatten_nodes)
        ScrollableList.update(self, decorated_flatten_nodes, \
                chosen_ind=self.get_single_chosen_item(), start_index=self.start_index, \
                secondary_chosen_ind=others.get_node_index_from_list(self._selected_node, self.flatten_nodes))

    def collapse(self):
        chosen_node = self.flatten_nodes[self.get_single_chosen_item()]
        chosen_node.parent.expanded=False
        self.flatten_nodes = TreeList.render_tree(self.tree)
        new_secondary_chosen_ind = -1 if self._selected_node not in self.flatten_nodes else self.flatten_nodes.index(self._selected_node)

        decorated_flatten_nodes = TreeList.__decorate_nodes(self.flatten_nodes)
        ScrollableList.update(self, decorated_flatten_nodes, \
                chosen_ind=self.flatten_nodes.index(chosen_node.parent), start_index=self.start_index, \
                secondary_chosen_ind=others.get_node_index_from_list(self._selected_node, self.flatten_nodes))

    def __add_indent(flatten_nodes):
        return [' '*(node.depth-1)*2 + node.name for node in flatten_nodes]

    def render_tree(root):
        flatten_nodes = []
        for node in root.children:
            flatten_nodes.append(node)
            if node.expanded:
                flatten_nodes.extend(TreeList.render_tree(node))
        return flatten_nodes

    def __get_tags(self):
        if self._selected_node:
            return set(others.get_path(self._selected_node).split('/'))
        else:
            return set()

    def __get_neg_tags(self):
        return set(itertools.chain(*[others.get_path(n).split('/') for n in self.muted_nodes]))

    def get_current_item(self):
        """you are on thin ince"""
        return self.__get_tags()

    def init_data(self, mdict):
        self.tree = Node('default', expanded=True)
        TreeList.construct_tree(self.tree, mdict)
        self.flatten_nodes = TreeList.render_tree(self.tree)
        self._selected_node = self.flatten_nodes[0]
        decorated_flatten_nodes = TreeList.__decorate_nodes(self.flatten_nodes)
        # TreeList.__add_indent(self.flatten_nodes), 
        ScrollableList.update(self, decorated_flatten_nodes, \
                chosen_ind=self.get_single_chosen_item(), start_index=self.start_index,
                secondary_chosen_ind=self.flatten_nodes.index(self._selected_node))
        self.broadcast_new_collection()

    def broadcast_new_collection(self):
        event = {'name': 'NEW_COLLECTION', 'owner': 'tree', 'papers': self.database.get_list_papers(self.__get_tags())}
        self.broadcast(event, 0)

    def broadcast_request_update(self):
        event = {'name': 'UPDATE_COLLECTION', 'owner': 'tree', \
                'papers': self.database.get_list_papers(self.__get_tags(), self.__get_neg_tags())}
        self.broadcast(event, 0)

    def update(self, mdict):
        new_tree = Node('default', expanded=True)
        TreeList.construct_tree(new_tree, mdict)

        for node in PreOrderIter(self.tree):
            new_node = others.find_node(new_tree, others.get_path(node))
            if new_node:
                new_node.expanded = node.expanded
        self.tree = new_tree
        new_flatten_nodes = TreeList.render_tree(self.tree)

        self.flatten_nodes = new_flatten_nodes

        decorated_flatten_nodes = TreeList.__decorate_nodes(self.flatten_nodes)
        ScrollableList.update(self, decorated_flatten_nodes, \
                chosen_ind=self.get_single_chosen_item(), start_index=self.start_index,
                secondary_chosen_ind=others.get_node_index_from_list(self._selected_node, self.flatten_nodes))
        self.broadcast_request_update()

    def toggle_mute(self):
        ind = others.get_node_index_from_list(self.flatten_nodes[self.get_single_chosen_item()], self.muted_nodes)
        if ind != -1:
            self.muted_nodes.remove(self.muted_nodes[ind])
        else:
            self.muted_nodes.append(self.flatten_nodes[self.get_single_chosen_item()])

        muted_inds = [others.get_node_index_from_list(n, self.flatten_nodes) for n in self.muted_nodes]
        ScrollableList.update(self, TreeList.__add_indent(self.flatten_nodes), \
                chosen_ind=self.get_single_chosen_item(), start_index=self.start_index,
                secondary_chosen_ind=others.get_node_index_from_list(self._selected_node, self.flatten_nodes),\
                disable_inds=muted_inds)
        self.broadcast_request_update()

    def add_new_child_tag(self, tag_name):
        chosen_node = self.flatten_nodes[self.get_single_chosen_item()]
        self.database.add_new_tag(tag_name, path_to_parent=others.get_path(chosen_node))
        self.update(self.database.get_collection())

    def add_new_sibling_tag(self, tag_name):
        chosen_node = self.flatten_nodes[self.get_single_chosen_item()].parent
        self.database.add_new_tag(tag_name, path_to_parent=others.get_path(chosen_node))
        self.update(self.database.get_collection())

    def receive_event(self, event):
        if event['owner'] == 'main_app':
            if event['name'] == 'DOWN':
                ScrollableList.select_next(self)
            elif event['name'] == 'UP':
                ScrollableList.select_previous(self)
            elif event['name'] == 'RIGHT':
                self.lost_focus()
            elif event['name'] == 'GOTO':
                line_number = event['line_number']
                ScrollableList.goto(self, line_number)
            elif event['name'] == 'ENTER':
                self._selected_node = self.flatten_nodes[self.get_single_chosen_item()]
                self.secondary_chosen_ind = self.get_single_chosen_item()
                self.broadcast_new_collection()
                self.render()
            elif event['name'] == 'EXPAND':
                self.expand()
            elif event['name'] == 'COLLAPSE':
                self.collapse()
            elif event['name'] == 'TOGGLE_MUTE':
                self.toggle_mute()
            elif event['name'] == 'SHIFT_RIGHT':
                self.shift_right()
            elif event['name'] == 'SHIFT_LEFT':
                self.shift_left()
            elif event['name'] == 'NEW_CHILD_TAG':
                self.add_new_child_tag(event['tag_name'])
            elif event['name'] == 'NEW_SIBLING_TAG':
                self.add_new_sibling_tag(event['tag_name'])
        if event['owner'] == 'paper_col':
            if event['name'] == 'LOST_FOCUS':
                if event['direction'] == 'LEFT':
                    ScrollableList.get_focus(self)

    def get_list_commands(self):
        return ['- `new_child_tag` tag_name', \
                '- `new_sibling_tag` tag_name', \
                '- `add_google_bib`', \
                ]

