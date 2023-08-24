import re
import requests
import bibtexparser
import os


from anytree import Node, PreOrderIter
from anytree.resolver import Resolver, ChildResolverError

# import bibman.definitions
from bibman import config

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

def format_bib(info, path_to_file):
    def format_authors(author_info):
        return ' and '.join([author['family']+', '+author['given'] for author in author_info])

    paper_dict = dict()
    paper_dict['title'] = info['title']
    paper_dict['author'] = format_authors(info['author'])
    paper_dict['year'] = str(info.get('year', ''))
    paper_dict['booktitle'] = info.get('booktitle', '')
    paper_dict['pages'] = str(info.get('pages', ''))
    paper_dict['organization'] = info.get('organization', '')
    return paper_dict

def search_title(papers, key):
    result = [paper for paper in papers if paper['title'].lower().find(key.lower())!=-1]
    return result

def search_author(papers, key):
    def satisfied(authors):
        return any([author.lower().find(key.lower()) !=-1 for author in authors.split('and')])

    result = [paper for paper in papers if satisfied(paper['author'])]
    return result

def search_all(papers, key):
    def paper2str(paper):
        text = ','.join([str(k)+':'+str(v) for k, v in paper.items()])

        path_to_file = os.path.join(config.data_dir, paper['ID']+'_note')
        try:
            with open(path_to_file, 'rt') as file_handler:
                note = file_handler.read()
                text = text + ',' + 'note:%s'%note
            return text
        except:
            return text

    def satisfied(paper):
        return paper2str(paper).lower().find(key.lower()) != -1

    result = [paper for paper in papers if satisfied(paper)]
    return result

def rawbib2json(raw_str):
    tmp = bibtexparser.loads(raw_str).entries
    bib_entry = tmp[0]
    return bib_entry


