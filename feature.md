** What is this

A TUI bibliography manager.
It aims to support only the most *basis* features as a general bibliography manager.

** Why not Zotero/Mendeley

Mendeley is not opensource, so whether its features fitting my needs is out of my control.
Zotero is open source, which is great. There are lots of custom extension we can install to customize individual needs. But I have no nothing about a TUI version of Zotero. So I made one.

** General goal
- Everything should be as **transparent** as possible. For example, database is just one text file. Every modification of this text file should be effective to the application. (of course, changes made by the application itself is more preferable.)
- Vim-like movement
- Ranger-like interface

** Features

I don't know how to list a list of features. 


** Manual
Open it by: 
```
source localenv/bin/activate
python main.py
```

There are 3 columns: collections, papers, attributes from left to right. 

- 'h,j,k,l': basic movement as in vim
- '0': Go to beginning
- 'G': Go to the end
- 'Enter': in collection column, it will open list of papers; in papers column, it will open the chosen paper by default pdf application; in attributes column, it will copy the chosen attribute to clipboard.
- 'J/K': move the current item up/down
- 'r': reload every thing (from database)
- 'V': open the 'database', which is a text file containing all bibtex entries, and move to the current item. You can modify it whatever you want, just don't corrupt the file.
- 'B': same effect as command ``add_bib``
- Enter a command by ':'
- List of commands:

    + ```add_paper <paper_name>```
    + ```add_bib```
    + and others


