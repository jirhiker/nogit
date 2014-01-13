#===============================================================================
# Copyright 2014 Jake Ross
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#===============================================================================

#============= enthought library imports =======================
import hashlib
from pymongo.errors import CollectionInvalid
from traits.api import HasTraits, Any


#============= standard library imports ========================
#============= local library imports  ==========================
from nogit.differ import Differ
from nogit.errors import NoBranchError


class GitObject(object):
    pass


class Commit(GitObject):
    def _digest(self, *args):
        sha = hashlib.sha1()
        for ai in args:
            sha.update(ai)
        return sha.hexdigest()


class Tree(GitObject):
    name = ''
    trees = None
    blobs = None


class Blob(GitObject):
    name = '' #relative path
    text = ''

    @property
    def sha(self):
        return self._digest(self.name, self.text)


class GitEngine(HasTraits):
    adapter = Any

    #print porcelain
    def pdiff(self, a,b):
        d=self.diff(a,b)
        for di in d:
            print di

    def plog(self):
        for p in self.log():
            print p

    def pstatus(self):
        for p in self.status():
            print p

    #porcelain
    def status(self):
        idx = self.get_index()
        template = '''# On branch "{}"
    # Changes to be committed:

    {}
    '''
        def assemble_object(tree, oi, action):
            blob = self._get_object(oi)
            if tree == '/':
                tree = ''
            else:
                tree = '{}/'.format(tree[1:])

            return '#        {}:    {}{}'.format(action, tree, blob['name'])

        head = self._get_head()
        branch = head['ref']
        changes = '\n'.join([assemble_object(*o) for o in idx['objects']])
        txt = template.format(branch, changes)
        return txt.split('\n')

    def log(self):
        """
            return a list of formatted commit messages
            author, date
            sha1

                message
        """
        template = '''commit {}
Author: {}
Date: {}

    {}\n'''

        def assemble_log(commit):
            a = commit['author']
            d = commit['_id'].generation_time
            s = commit['_id']
            m = commit['msg']
            return template.format(s, a, d.strftime('%a %b %d %H:%M %Y'), m)

        return [assemble_log(c) for c in self.walk_commits()]

    def diff(self, path, c1, c2):
        a=self.get_blob(path, c1)
        print 'commit',c1, 'blob', a

        b=self.get_blob(path, c2)
        print 'commit',c2, 'blob',b

        d=Differ(a,b)
        return d.diff()

    def drop_database(self):
        self.adapter.drop_database()

    def init(self):
        """
            add some defaults
        """
        #make empty collections
        try:
            self.adapter.create_collection('commits')
            self.adapter.create_collection('objects')
        except CollectionInvalid:
            pass

        m = self.adapter.get_collection('HEAD')
        if not m.find_one({'name': 'HEAD'}):
            m.insert({'name': 'HEAD', 'ref': 'master', 'kind': 'head'})

        if not self._get_ref('master'):
            self.add_ref('master', None)

        m = self.adapter.get_collection('index')
        if not m.find_one({'kind': 'index'}):
            m.insert({'kind': 'index',
                      'trees': [], 'blobs': [], 'objects': []})

        self.add_root()

    def checkout(self, name):
        """
            checkout a ref. (branch or tag)

        """
        ref = self._get_ref(name)
        if ref is None:
            raise NoBranchError(name)
        else:
            self._update_head(ref['name'], ref['kind'])

    def branch(self, name, commit_id=None):
        """
            add a branch named ``name``. if commit_id is None use the latest commit
        """
        if not commit_id:
            commit_id = self.adapter.get_last('commits')['_id']

        b = self.add_ref(name, commit_id)

        #update HEAD
        self._update_head(name, 'head')
        return b

    def add(self, parent, name, doc):
        """
            add a blob to the staging area
        """
        col = self.adapter.get_collection('index')
        objects_col = self.adapter.get_collection('objects')

        idx = self.get_index()

        blobs = idx['blobs']
        objects = idx['objects']

        sha = self._digest(parent, name, doc)

        blob = objects_col.find_one({'sha1': sha})
        if not blob:
            blob = objects_col.find_one({'path_sha1': self._digest(parent, name)})
            if not blob:
                nbid = objects_col.insert(self._create_blob(parent, name, doc))
                blobs.append(nbid)
                objects.append((parent, nbid, 'new file'))
                col.update({'_id': idx['_id']}, {'$set': {'blobs': blobs, 'objects': objects}})

                tree = self._get_tree(parent)
                if not tree:
                    ntid = self.add_tree(parent, kind='tree', blobs=[nbid])

                    ptree = self._get_parent_tree(parent)
                    trees = ptree['trees']
                    for tid in trees:
                        tt = objects_col.find_one({'_id': tid})
                        if tt['name'] == parent:
                            trees.remove(tid)
                            break

                    trees.append(ntid)
                    objects_col.update({'_id': ptree['_id']}, {'$set': {'trees': trees}})
                else:
                    blobs = tree['blobs']
                    blobs.append(nbid)
                    objects_col.update({'_id': tree['_id']}, {'$set': {'blobs': blobs}})

            else:
                # if blob is already in staging area
                if self._is_staged(blob):
                    print 'staged'
                    doc['sha']=sha
                    objects_col.update({'_id': blob['_id']},
                                       {'$set': doc})
                else:
                    nbid = objects_col.insert(self._create_blob(parent, name, doc))
                    blobs.append(nbid)
                    objects.append((parent, nbid, 'modified'))
                    col.update({'_id': idx['_id']}, {'$set': {'blobs': blobs, 'objects': objects}})

                    #make new tree
                    args=parent.split('/')
                    n=len(args)
                    for i in range(n):
                        d=n-i
                        p='/'.join(args[:d])
                        if not p:
                            p='/'

                        t=self._get_tree(p)
                        pid=t['_id']
                        t.pop('_id')
                        if i==0:
                            blobs = t['blobs']
                            for bid in blobs:
                                bi = objects_col.find_one({'_id': bid})
                                if bi['path_sha1'] == self._digest(parent, name):
                                    blobs.remove(bid)
                            blobs.append(nbid)
                            t['blobs'] = blobs
                            ntid = objects_col.insert(t)
                            ppath = p

                        else:
                            trees=t['trees']
                            for tid in t['trees']:
                                ti=objects_col.find_one({'_id':tid})
                                if ti['name']==ppath:
                                    trees.remove(tid)

                            trees.append(ntid)
                            t['trees']=trees
                            if p=='/':
                                objects_col.update({'_id':pid},{'$set':{'trees':trees}})
                                break
                            else:
                                ntid=objects_col.insert(t)
                                ppath = p

    def commit(self, msg):
        """
        """
        wtree = self._get_working_tree()
        if wtree:
            return self.commit_tree(msg, wtree['_id'])

    #plumbing
    def extract_diff(self, d):
        lefts=[]
        rights=[]
        for l in d:
            if l[0]=='-':
                l=l.strip().split(':')[1].strip()
                lefts.append(l)
            elif l[0]=='+':
                l = l.strip().split(':')[1].strip()
                rights.append(l)

        return zip(lefts, rights)

    def get_blob(self, path, commit):
        commit=self._get_commit(commit)
        objects=self.adapter.get_collection('objects')
        tree=objects.find_one({'_id':commit['tid']})
        # print 'ffff', commit['_id'], tree['_id']
        for bi in self.walk_tree(tree, return_object=True, blobs_only=True):
            # print bi['name'], bi['_id']
            if bi['name']==path:
                return bi

    def get_branches(self):
        col = self.adapter.get_collection('refs')
        return col.find({'kind': 'head'})

    def walk_tree(self, root=None, return_object=False, blobs_only=False):
        objects = self.adapter.get_collection('objects')
        if root is None:
            root = self._get_working_tree()
        elif isinstance(root, str):
            ref = self._get_ref(root)
            commits = self.adapter.get_collection('commits')
            commit = commits.find_one({'_id': ref['cid']})
            root = objects.find_one({'_id': commit['tid']})

        def gen():
            for tree in root['trees']:
                tree = objects.find_one({'_id': tree})
                if not blobs_only:
                    ret=tree
                    if not return_object:
                        ret=ret['name']
                    yield ret

                for di in self.walk_tree(tree, return_object, blobs_only):
                    yield di

            for blob in root['blobs']:
                blob = objects.find_one({'_id': blob})

                if not return_object:
                    blob=blob['name']

                yield blob

        return gen()

    def add_root(self):
        self.add_tree('/')

    def add_tree(self, name, kind='wtree', blobs=None):
        if blobs is None:
            blobs = []

        if not self._get_tree(name):
            objects = self.adapter.get_collection('objects')
            oid = objects.insert({'name': name, 'kind': kind,
                                  'blobs': blobs, 'trees': []})
            return oid

    def add_ref(self, name, commit_id, kind='head'):
        col = self.adapter.get_collection('refs')
        return col.insert({'cid': commit_id,
                           'kind': kind,
                           'name': name})

    def update_ref(self, name, commit_id):
        ref = self._get_ref(name)
        if ref is None:
            self.add_ref(name, commit_id)
        else:
            col = self.adapter.get_collection('refs')
            col.update(ref, {'$set': {'cid': commit_id}})

    def get_ref(self, name):
        self._get_ref(name)

    def get_index(self):
        col = self.adapter.get_collection('index')
        return col.find_one({'kind': 'index'})

    def get_working_tree(self):
        return self._get_working_tree()

    def commit_tree(self, msg, tree_id):
        if not tree_id:
            return

        author = 'foo'

        commits = self.adapter.get_collection('commits')
        p = self.adapter.get_last('commits')

        tree = self._get_tree(tree_id)

        cid = commits.insert({
            'pid': p['_id'] if p else None,
            'tid': tree['_id'],
            'msg': msg,
            'author': author})

        #update the current head to point to latest reference
        head = self._get_head()
        self.update_ref(head['ref'], cid)

        #clear staging area
        self._clean_stage()

        #make new working tree
        objects = self.adapter.get_collection('objects')

        objects.update({'_id': tree['_id']}, {'$set': {'kind': 'tree'}})

        tree.pop('_id')
        objects.insert(tree)
        return cid

    def get_commits(self):
        return list(self.walk_commits())

    def get_head_ref(self):
        return self._get_head()['ref']

    def walk_commits(self, ref=None):
        """
        """
        if ref is None:
            head = self._get_head()
            ref = head['ref']

        def gen():
            cid = self._get_ref(ref)['cid']
            while 1:
                commit = self._get_commit(cid)
                yield commit
                cid = commit['pid']
                if not cid:
                    break

        return gen()

    #private
    def _get_parent_tree(self, path):
        wtree = self._get_working_tree()
        if path == '/':
            return wtree
        else:
            args = path.split('/')
            if len(args) > 2:
                name = '/'.join(args[:-1])
            else:
                name = '/'

            r = self._get_tree(name)
            return r

    def _is_staged(self, blob):
        idx = self.get_index()
        # print idx['objects']
        for _, oi, _ in idx['objects']:
            # print oi, blob['_id']
            if oi == blob['_id']:
                return True

    def _clean_stage(self):
        idx = self.adapter.get_collection('index')
        idx.update({'kind': 'index'}, {'$set': {'objects': [],
                                                'trees': [],
                                                'blobs': []}})

    def _get_commit(self, cid):
        ts = self.adapter.get_collection('commits')
        q = {'_id': cid}
        return ts.find_one(q)

    def _get_tree(self, name):
        if isinstance(name, (str, unicode)):
            return self._get_tree_path(name)
        else:
            objects = self.adapter.get_collection('objects')
            return objects.find_one({'_id': name})

    def _get_tree_path(self, name):
        wtree = self._get_working_tree()
        if wtree:
            return self.find_tree(wtree, name)

    def find_tree(self, root, name):
        if not root:
            return
        elif root['name'] == name:
            return root
        else:
            col = self.adapter.get_collection('objects')

            basename = name.split('/')[1:-1]
            basename = '/{}'.format('/'.join(basename))
            nroot = None
            for ti in root['trees']:
                tt = col.find_one({'_id': ti})
                if tt['name'] in (name, basename):
                    nroot = tt

            return self.find_tree(nroot, name)

    def _get_working_tree(self):
        objects = self.adapter.get_collection('objects')
        return objects.find_one({'kind': 'wtree'})

    def _create_blob(self, parent, name, doc):
        sha = self._digest(parent, name, doc)
        if parent == '/':
            pname = '/{}'.format(name)
        else:
            pname = '{}/{}'.format(parent, name)

        doc.update({'name': pname,
                    'path_sha1': self._digest(parent, name),
                    'sha1': sha})
        return doc


    def _get_ref(self, rid):
        ts = self.adapter.get_collection('refs')
        if isinstance(rid, (str, unicode)):
            q = {'name': rid, 'kind': 'head'}
        else:
            q = {'_id': rid, 'kind': 'head'}

        return ts.find_one(q)

    def _update_head(self, ref_name, kind):
        m = self.adapter.get_collection('HEAD')
        m.update({'name': 'HEAD'}, {'$set': {'ref': ref_name,
                                             'kind': kind}})

    def _get_head(self):
        m = self.adapter.get_collection('HEAD')
        return m.find_one({'name': 'HEAD'})

    def _get_object(self, value, key='_id'):
        m = self.adapter.get_collection('objects')
        return m.find_one({key: value})

    def _digest(self, *args):
        sha = hashlib.sha1()
        for ai in args:
            if isinstance(ai, dict):
                ai=hashlib.sha1(repr(sorted(ai.items()))).hexdigest()
            sha.update(ai)
        return sha.hexdigest()

    @property
    def ncollections(self):
        return len(self.adapter.collection_names(include_system_collections=False))


#============= EOF =============================================

