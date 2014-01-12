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

    def test_commit_staged(self):
        msg='test commit message'
        self.engine.commit(msg)

        commits=self.engine.get_commits()
        self.assertEqual(len(commits), 1)


if __name__ == '__main__':
    unittest.main()
