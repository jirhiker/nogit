from mongit.git_engine import GitEngine
from mongit.mongo_adapter import MongoAdapter

engine=GitEngine(adapter=MongoAdapter())
tree_id=engine.add_tree('root')

name='file1'
txt='hello mongit 1'
engine.add_blob(tree_id, name, txt)

engine.commit_tree('first commit', tree_id)

db=engine.adapter._db

db.commits
# for c in db.commits.find():
#     print c