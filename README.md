mongit
======

Concept
----------
Implement a NoSQL database with GIT-style version control. Allows version control with content queries
So if blobs contain analysis information such as age, you can find all analyses that match a query e.g. age>10

Collections
------------
#. commits- contains the commit documents
#. objects- contains blob and tree documents
#. meta- contains the HEAD document
