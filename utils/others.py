
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
