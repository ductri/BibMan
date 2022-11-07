
from anytree import Node, PreOrderIter
from anytree.resolver import Resolver, ChildResolverError

def get_path(node):
    """
    bad library so that I have to implement this trivial function
    """
    return '/'.join([n.name for n in node.path])

tree_resolver = Resolver('name')
def find_node(tree, path_str):
    """
    bad library so that I have to implement this trivial function
    excluding root name
    """
    try:
        return tree_resolver.get(tree, '/'.join(path_str.split('/')[1:]))
    except ChildResolverError:
        return None

def export_bib_format(paper_dict):
    """
    kind of boring
    """
    text = ''
    text += '@'+paper_dict['ENTRYTYPE']+ ('{%s,\n'% paper_dict['ID'])
    text += 'author = {%s}, \n' % paper_dict['author']
    text += 'booktitle = {%s}, \n' % paper_dict['booktitle']
    text += 'journal = {%s}, \n' % paper_dict['journal']
    text += 'pages = {%s}, \n' % paper_dict['pages']
    text += 'volume = {%s}, \n' % paper_dict['volume']
    text += 'title = {%s}, \n' % paper_dict['title']
    text += 'year = {%s}, \n' % paper_dict['year']
    text += '}'
    return text

def get_node_index_from_list(node, list_nodes):
    list_node_paths = [get_path(n) for n in list_nodes]
    try:
        return list_node_paths.index(get_path(node))
    except ValueError:
        return -1


