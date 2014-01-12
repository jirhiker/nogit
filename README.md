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
3. refs- cpntains head and tag documents
4. HEAD- contains the HEAD document
5. index- contains staging area document


use a serverless