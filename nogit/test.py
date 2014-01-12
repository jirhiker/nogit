from nogit.git_engine1 import GitEngine
from nogit.mongo_adapter import MongoAdapter

engine = GitEngine(adapter=MongoAdapter())

# engine.checkout('test')

# engine.add_blob('root','file4', 'modified index test')
# engine.commit_tree('added file3',t)
# engine.add_branch('test')
# engine.plog()
engine.init()

# engine.add_subtree('/','test1')
# engine.add_blob('/test1','file2','version1')
# engine.add_blob('/','file1','version1')
# engine.add_blob('/','file1','version1asdf')
# engine.modify_blob('/','file2','version1dasjjjjkkkkjkj')
# engine.commit('first commit')
engine.commit('second commit')
# engine.commit('fifth commit')
engine.pstatus()

# engine.commit('first commit')

#
# ## first
# tree_id=engine.add_tree('root')
# #
# name='file1'
# txt='hello nogit 1'
# engine.add_blob(tree_id, name, txt)
# engine.commit_tree('first commit', tree_id)
#
# ##second
# ##add blob
# tree_id=engine.add_blob('root', 'file2', 'hello nogit 2')
# engine.commit_tree('second commit', tree_id)
#
# ##third
# ##modify blob
# tree_id=engine.modify_blob('root', 'file2', 'modified-hello nogit 2')
# engine.commit_tree('third commit', tree_id)
#
# # #fourth
# # #add subtree
# trees=['root']
# blobs=[]
# tree_id=engine.add_subtree('root','foo', trees=trees, blobs=blobs)
# engine.commit_tree('fourth commit', tree_id)
#
# trees=[]
# blobs=[]
# tree_id=engine.add_subtree('root','foo', trees=trees, blobs=blobs)
# engine.commit_tree('fifth commit', tree_id)

# print engine.master


# db=engine.adapter._db

# db.commits
# for c in db.commits.find():
#     print c