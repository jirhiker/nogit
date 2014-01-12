NoGit
======

Concept
----------

Implement a NoSQL database with GIT-style version control. Allows version control with content queries
So if blobs contain analysis information such as age, you can find all analyses that match a query e.g. age>10


Collections
------------
1. commits- contains the commit documents
2. objects- contains blob and tree documents
3. refs- contains head and tag documents
4. HEAD- contains the HEAD document

#local
5. index- contains staging area document
6. config- contains the config document


a serverless nosql database is run on each computer.
a server nosql database is run on the server computer.

all changes are committed to the local database.
changes can be pushed, pulled, merged from the remote database

phase 1. local
--------------
1. add branching
2. add tagging
3. **add subtree**
5. diff
    a. blobs
    b. trees
6. merge
7. rebase

phase 2. remote
----------------
1. define remote
2. pull -pull diff between remote and local
    a. fetch
    b. upsert
3. push -push diff between local and remote
    a. upsert
4. identify conflicts
    - commit on remote > last commit of local

When synchronizing between local and remote add diffed commits and objects, HEAD and refs/remotes