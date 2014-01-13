from nogit.errors import NoBranchError

__author__ = 'ross'

import unittest


class EngineTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from nogit.git_engine import GitEngine
        from nogit.mongo_adapter import MongoAdapter

        engine = GitEngine(adapter=MongoAdapter())
        cls.engine=engine
        engine.drop_database()

        engine.adapter.connect()

    def setUp(self):
        self.engine.init()

    def test_init(self):
        self.engine.init()

        n=self.engine.ncollections
        self.assertGreaterEqual(n, 5)

    def test_add_blob(self):
        self.engine.add('/', 'file1', 'version1')
        self.engine.add('/', 'file2', 'version1')

        idx=self.engine.get_index()
        self.assertEqual(len(idx['blobs']), 2)

        wtree=self.engine.get_working_tree()
        self.assertEqual(len(wtree['blobs']), 2)

        # self.engine.add_tree('/test')
        self.engine.add('/test', 'file3', 'version1')

        wtree = self.engine.get_working_tree()
        self.assertEqual(len(wtree['trees']), 1)
        self.assertEqual(len(wtree['blobs']), 2)

        self.engine.commit('test commit')

        self.engine.add('/test', 'file3', 'version1234')
        self.engine.add('/test/foo', 'file5', 'version1')
        self.engine.add('/test/foo/bar', 'file6', 'version1')

        # self.engine.add('/test', 'file3', 'version1234')
        # o = self.engine.adapter.get_collection('objects')
        # self.assertEqual(o.count(), 7)
        #
        # wtree = self.engine.get_working_tree()
        # self.assertEqual(len(wtree['trees']), 1)
        # self.assertEqual(len(wtree['blobs']), 2)
        #
        self.engine.commit('test commit 2')
        commits=self.engine.get_commits()
        self.assertEqual(len(commits), 2)

    def test_structure(self):
        top=list(self.engine.walk_tree())
        self.assertEqual(len(top),10)

    def test_add_branch(self):
        self.engine.branch('develop')

        branches=self.engine.get_branches()
        self.assertEqual(len(list(branches)), 2)

    def test_checkout(self):
        self.assertRaises(NoBranchError, self.engine.checkout, 'dev')

        self.engine.checkout('develop')
        ref=self.engine.get_head_ref()
        self.assertEqual(ref,'develop')

        self.engine.add('/dev','filedev','version1')
        self.engine.commit('add dev')

        dev_top=list(self.engine.walk_tree('develop'))
        master_top=list(self.engine.walk_tree('master'))

        self.assertNotEqual(dev_top, master_top)

    # def test_commit_staged(self):
    #     msg='test commit message'
    #     self.engine.commit(msg)
    #
    #     commits=self.engine.get_commits()
    #     self.assertEqual(len(commits), 1)

if __name__ == '__main__':
    unittest.main()
