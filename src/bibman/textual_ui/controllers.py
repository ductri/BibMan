from bibman.utils.data_manager import DatabaseManager
from anytree import ContRoundStyle, Node, PreOrderIter

from bibman.utils import others
from bibman.textual_ui.observer_dp import MyEvent, Subscriber, Publisher




class TagController(Publisher):
    def __init__(self, tags_dict, default_tag_name='default'):
        super().__init__()
        self.tags_dict = tags_dict
        self.tree_root = Node(default_tag_name, expanded=True)
        self.construct_tree(self.tree_root, self.tags_dict)
        self.flattened_nodes = self.flatten_tree(self.tree_root)

        self._selected_node = None if len(self.flattened_nodes) == 0 else self.flattened_nodes[0]
        self.default_tag_name = default_tag_name

    def ui_init(self):
        node = self.flattened_nodes[12]
        print(f'UI feedback: choosing node: {str(node)}')
        self.my_action_choose_tag(node)


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

    def my_action_choose_tag(self, node):
        tags = set(others.get_path(node).split('/'))
        event = MyEvent(name='choose_tags', data= {'tags': tags}, source=self)
        self.notify_event(event)

    def action_choose_tag(self, index):
        self.my_action_choose_tag(self.flattened_nodes[index])

    def render(self):
        decorated_flatten_nodes = [' '*(node.depth-1)*2 + '▹' + node.name if node.children != () else ' '*(node.depth-1)*2 + ' ' + node.name for node in self.flattened_nodes]
        for node in decorated_flatten_nodes:
            print(node)

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


class PaperController(Publisher):
    def __init__(self):
        super().__init__()
        self.__papers = [] # todo maybe we dont need this much info
        self.deco_type = 'INDEX'

    def ui_init(self):
        pass

    def publisher_new_state(self, event: MyEvent):
        if isinstance(event.source, Controller):
            if event.name == 'choose_tags':
                self.__papers = event.data['papers']

    def render(self):
        def papers2strs(papers, deco_type='SIMPLE'):
            deco_title = lambda paper: (f"[{','.join(sorted(list(paper['label'])))}] " if len(paper['label']) !=0 else '') + paper['title']
            if deco_type == 'SIMPLE':
                return ['> '+ deco_title(paper) for paper in papers]
            elif deco_type == 'INDEX':
                return [f'{i}. '+deco_title(paper) for i, paper in enumerate(papers)]
            elif deco_type == 'EMPTY':
                return [deco_title(paper) for paper in papers]
            else:
                raise Exception(f'Unsupported deco_type of {deco_type}')

        items = papers2strs(self.__papers, deco_type=self.deco_type)
        print('\n'.join (items))

    def my_action_choose_paper(self, paper):
        event = MyEvent(name='choose_paper', data={'paper': paper}, source=self)
        self.notify_event(event)

    def action_choose_paper(self, index):
        self.my_action_choose_paper(self.__papers[index])


class AttributeController(Publisher):
    ATTRIBUTES = (('title', 'Title: '), ('author','Authors: '), ('year', 'Year: '), ('journal', 'Venue: '), ('created_time',  'Created: '))

    def __init__(self):
        super().__init__()
        self.atts = []

    def publisher_new_state(self, event: MyEvent):
        if isinstance(event.source, Controller):
            if event.name == 'choose_paper':
                paper = event.data['paper']
                self.atts = self.get_paper_attributes(paper)

    def render(self):
        def add_decoration(attr_values, ncols):
            def title2lines(title, ncols):
                max_lines = 4
                head_len = max(ncols-10, 0)
                head = title[:head_len]
                tail = title[head_len:]
                step = ncols - 3
                lines = ['  ' + tail[i:i+step] for i in range(0, len(tail), step)]
                if len(lines) > max_lines:
                    lines = lines[:max_lines-1] + ['   ...']
                else:
                    lines = lines + ['']*(max_lines - len(lines))
                lines = [head] + lines
                assert any([len(line)<=step+2 for line in lines])
                return lines
            def author2lines(author_str):
                max_lines = 4
                lines = [' - ' + author.strip() for author in author_str.split(' and ')]
                if len(lines)>max_lines:
                    lines = lines[:max_lines-1] + [' ...']
                else:
                    lines = lines + [''] * (max_lines-len(lines))
                lines = [''] + lines
                return lines
            results = []
            for ((attr_key, attr_name), attr_value) in zip(AttributeController.ATTRIBUTES, attr_values):
                if attr_key == 'created_time':
                    results.append(attr_name + '\n    ' + attr_value)
                elif attr_key == 'title':
                    lines = title2lines(attr_value, ncols)
                    results.append(attr_name + '\n'.join(lines))
                elif attr_key == 'author':
                    lines = author2lines(attr_value)
                    results.append(attr_name + '\n'.join(lines))
                elif attr_key == 'year':
                    lines = [attr_value, '']
                    results.append(attr_name + '\n'.join(lines))
                elif attr_key == 'booktitle':
                    head_len = max(ncols-10, 0)
                    head = attr_value[:head_len]
                    tail = attr_value[head_len:]
                    step = ncols - 3
                    lines = ['  ' + tail[i:i+step] for i in range(0, len(tail), step)]
                    max_lines = 4
                    if len(lines) > max_lines:
                        lines = lines[:max_lines-1] + ['   ...']
                    else:
                        lines = lines + ['']*(max_lines - len(lines))
                    lines = [head] + lines +['']
                    results.append(attr_name + '\n'.join(lines))
                else:
                    results.append(attr_name + attr_value + '\n')
            return results
        items = add_decoration(self.atts, 50)
        print('\n'.join(items))

    def get_paper_attributes(self, paper):
        if paper:
            return [paper[item[0]] for item in AttributeController.ATTRIBUTES]
        else:
            return []


class Controller(Publisher):
    def __init__(self):
        super().__init__()
        self.database = DatabaseManager()

        self.tag_clt = TagController(self.database.get_collection())
        self.tag_clt.add_listener(self)

        self.paper_clt = PaperController()
        self.paper_clt.add_listener(self)
        self.add_listener(self.paper_clt)

        self.attribute_clt = AttributeController()
        self.add_listener(self.attribute_clt)

        self.database.add_listener(self.tag_clt)

        self.tag_clt.ui_init()

    def publisher_new_state(self, event: MyEvent):
        if isinstance(event.source, TagController):
            if event.name == 'new_tag':
                tag_name = event.data['tag_name']
                path_to_parent = event.data['path_to_parent']
                self.database.add_new_tag(tag_name, path_to_parent)
            elif event.name == 'choose_tags':
                tags = event.data['tags']
                papers = self.database.get_list_papers(tags)
                event = MyEvent(name='choose_tags', data={'papers': papers}, source=self)
                self.notify_event(event)
        elif isinstance(event.source, PaperController):
            if event.name == 'choose_paper':
                event.source = self
                self.notify_event(event)





if __name__ == "__main__":

    controller = Controller()

    print('---------------- Test 1 ----------- \n')
    controller.tag_clt.my_action_expand(2)
    controller.tag_clt.render()

    print('---------------- Test 2 ----------- \n')
    controller.tag_clt.my_action_add_new_tag('new_tag', controller.tag_clt.flattened_nodes[1])
    controller.tag_clt.my_action_expand(1)
    controller.tag_clt.my_action_add_new_tag('new_tag2', controller.tag_clt.flattened_nodes[5])
    controller.tag_clt.render()

    print('---------------- Test 3 ----------- \n')
    controller.tag_clt.action_choose_tag(12)
    controller.paper_clt.render()

    print('---------------- Test 4 ----------- \n')
    controller.tag_clt.action_choose_tag(17)
    controller.paper_clt.render()

    print('---------------- Test 5 ----------- \n')
    controller.tag_clt.action_choose_tag(12)
    controller.paper_clt.action_choose_paper(-1)
    controller.attribute_clt.render()

