from nogit.errors import NoBranchError

__author__ = 'ross'

import unittest


class PychronEngineTestCase(unittest.TestCase):
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
        self.engine.add('/minnabluff', 'project', {'project':'minnabluff','location':'Antarctica'})
        self.engine.add('/minnabluff/51000', '51000-01A', {'identifier':'51000','aliquot':'01','step':'A',
                                                           'isotopes':{'Ar40':10}})

        idx=self.engine.get_index()
        self.assertEqual(len(idx['blobs']), 2)

        wtree=self.engine.get_working_tree()
        self.assertEqual(len(wtree['blobs']), 0)

        self.assertEqual(len(wtree['trees']), 1)
        c1=self.engine.commit('first comiit')

        self.engine.add('/minnabluff/51000', '51000-01A', {'identifier': '51000', 'aliquot': '01', 'step': 'A',
                                                           'isotopes': {'Ar40': 22}})
        c2=self.engine.commit('second commit')

        d=self.engine.diff('/minnabluff/51000/51000-01A', c1, c2)
        ls,rs=zip(*self.engine.extract_diff(d))

        self.assertEqual(ls[0],'10')
        self.assertEqual(rs[0],'22')



if __name__ == '__main__':
    unittest.main()