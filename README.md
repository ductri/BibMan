# BibMan


## What is this

A TUI bibliography manager.
Its goal is to support *basis* features as a general bibliography manager.
<!-- ![demo](https://github.com/ductri/BibMan/blob/main/src/bibman/screenshot/demo1.png) -->

[![demo](https://img.youtube.com/vi/Tt_wGJYMHY8/0.jpg)](https://www.youtube.com/watch?v=Tt_wGJYMHY8)

<!-- A short [youtube-demo](https://youtu.be/Tt_wGJYMHY8) -->

## Why not Zotero/Mendeley

Mendeley is not open-source, so whether its features fit my needs is out of my control.
Zotero is open source, which is great. There are lots of extensions customizing toward individual needs. But I have found no extension/app that made it a keyboard-oriented app such as a TUI version of Zotero. So I decided to make one.


## General goal

- Everything should be as **transparent** as possible. For example, database is just one text file. Every modification of this text file should be effective to the application. (of course, changes made by the application itself is more preferable.)
You should be able to manage all data via text editor. That means: collection is stored in `data/collection_tree.txt`, bibfile is stored in `data/bib_collection.bib`, and all pdfs files are at `data/pdfs/`. The inferface is used as a convenient way to access/modify your data, otherwise you should be able to do every task yourself.
- Vim-like movement, ranger-like interface

Model
- Everything is fat, there is no explicit hierachical structure in organizing papers.
- Instead, tag is used as a main tool to group relevant papers. 
- The first column which appears as a tree is just a convinient way to provide some shortcut. Think of it as a predefined set of tags, where selecting a particular nodes means to create a filter of all tags along the path from root the that node.
For example,
```
.
|---a
|   |
|   ---a1
|   ---a2
|---b
|---a1

```
when choosing the child node a1, it will show all papers containng both tags a and a1, while choosing node a1 in the bottom of the tree will show all papers containing tag a1.

## Features

A brief introduction at: [https://ductri.github.io/note/2023/09/27/bibman.html](https://ductri.github.io/note/2023/09/27/bibman.html)

## Manual
Require: `vim` for editing bib file, `zathura` and/or `evince` for opening pdf files. Without these apps, corresponding features will not be available (other features will be fine though).

Install:
```
pip install bibman
```
And run from terminal
```
bibman
```
Config file can be found at `~/.config/bibman/config.yml`, and data directory is (configurable) at `~/bibman_data/`.

The layout contains 3 columns: collections, papers, attributes from left to right. 

```
---------------
SHORT KEYS
(still updating ...)
---------------
* General:
- h,j,k,l: basic movement as in vim
- 0: go to beginning
- G: go to the end
- r: reload every thing (from database)

* Collection colum:
Show list of collections in a tree format.

- e: expand sub-collections
- Enter: show list of papers under current collections to the paper column (second column)

* Paper column:
Show list of papers under the current collection

- J/K: move the current item up/down
- Enter: open the chosen paper by default pdf application; in attributes column, it will copy the chosen attribute to clipboard.
- V: open the 'database', which is a text file containing all bibtex entries, in Vim and move to the current item. You can modify it in whatever way you want, just don't corrupt the file.
- B: same effect as command ``add_bib``
- mb: copy bib key

* Attribute column:
Show all attributes of the current paper

- Enter: copy the chosen attribute

-----------------
COMMANDS
-----------------
- Enter a command by ':'
- List of commands:
    + add_paper <paper_name>: add new paper to the current collection
    + add_bib: let user input a bib text in vim and add ti to current collection as a new paper
    + download <url>: download a pdf file for the current paper
    + add_local_file <path>: copy a pdf file for the current paper
    + remove: remove the current paper
    + add_tag: add a new tag
    + note: add or modify the note associating to the current paper
    + ...
```

### Todo

- Warning when removing a paper having a note
