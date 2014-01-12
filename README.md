mongit
======

Concept
----------

Implement a NoSQL database with GIT-style version control. Allows version control with content queries
So if blobs contain analysis information such as age, you can find all analyses that match a query e.g. age>10


Collections
------------
1. commits- contains the commit documents
2. objects- contains blob and tree documents
3. refs- cantains head and tag documents
4. meta- contains the HEAD document
