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

class GitEngine(HasTraits):
    adapter=Any


    #porcelain
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

        self.add_tree('/')

    def add(self, parent, name, text):
        """
            add a blob to the staging area
        """
        col = self.adapter.get_collection('index')
        objects_col = self.adapter.get_collection('objects')

        idx=self.get_index()

        blobs=idx['blobs']
        objects =idx['objects']

        sha = self._digest(parent, name, text)

        blob=objects_col.find_one({'sha1':sha})
        if not blob:
            blob = objects_col.find_one({'path_sha1': self._digest(parent, name)})
            if not blob:
                nbid=objects_col.insert(self._create_blob(parent, name, text))
                blobs.append(nbid)
                objects.append((parent, nbid, 'new file'))
                col.update({'_id':idx['_id']}, {'$set':{'blobs':blobs, 'objects':objects}})

                #add to working tree
                wtree=self._get_working_tree()
                blobs=wtree['blobs']
                blobs.append(nbid)
                objects_col.update({'_id':wtree['_id']}, {'$set':{'blobs':blobs}})

            else:
                objects_col.update({'_id':blob['_id']}, {'$set': {'text':text, 'sha1':sha}})


        #is sha already staged
        # blob=col.find_one({'sha1':sha})
        # if not blob:
        #     #is this name already staged
        #     blob=col.find_one({'path_sha1':self._digest(parent, name)})
        #     if not blob:
        #         nbid=objects_col.insert(self._create_blob(parent, name, text))
        #         blobs.append(nbid)
        #         objects.append((parent, nbid, 'new file'))
        #
        #         col.update({'_id':idx['_id']}, {'$set':{'blobs':blobs, 'objects':objects}})
        #     else:
        #         col.update({'_id':blob['_id']}, {'$set': {'text':text, 'sha1':sha}})

    def commit(self, msg):
        """
        """
        wtree=self._get_working_tree()
        if wtree:
            self.commit_tree(msg, wtree['_id'])

    #plumbing
    def add_tree(self, name, kind='wtree'):
        if not self._get_tree(name):
            objects=self.adapter.get_collection('objects')
            objects.insert({'name':name, 'kind':kind,
                            'blobs':[], 'trees':[]})

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

    def get_ref(self,name):
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
        objects=self.adapter.get_collection('objects')

        objects.update({'_id':tree['_id']}, {'$set':{'kind':'tree'}})

        tree.pop('_id')
        objects.insert(tree)

    def get_commits(self):
        return list(self._walk_commits())

    #private
    def _walk_commits(self):
        """
        """

        def gen():
            head = self._get_head()
            ref = head['ref']
            ref = self._get_ref(ref)
            cid = ref['cid']
            while 1:
                commit = self._get_commit(cid)
                yield commit
                cid = commit['pid']
                if not cid:
                    break

        return gen()

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
            wtree=self._get_working_tree()
            if wtree and wtree['name']!=name:
                col=self.adapter.get_collection('objects')
                for p in name.split('/'):
                    if not p:
                        continue

                    for ti in wtree['trees']:
                        tt=col.find_one({'_id':ti})
                        if tt['name']==name:
                            wtree=tt
            return wtree

        else:
            objects=self.adapter.get_collection('objects')
            return objects.find_one({'_id':name})

    def _get_working_tree(self):
        objects=self.adapter.get_collection('objects')
        #get the current commit
        #get the tree from the current commit
        return objects.find_one({'kind':'wtree'})

        # #if no current commit use latest root tree doc
        # commits=self.adapter.get_collection('commits')
        # if not commits.count():
        #     cursor=objects.find({'kind':'tree','name':'/'}).sort('_id',-1).limit(1)
        #     if cursor.count():
        #         return cursor[0]
        # else:
        #     ref=self._get_head()['ref']
        #     cid=self._get_ref(ref)['cid']
        #     commit=commits.find_one({'_id':cid})
        #     return objects.find_one({'_id':commit['tid']})

    def _create_blob(self, parent, name, text):
        sha=self._digest(parent, name, text)
        return {'name':name, 'text':text,
                'path_sha1':self._digest(parent, name),
                'sha1':sha}

    def _get_ref(self, rid):
        ts = self.adapter.get_collection('refs')
        if isinstance(rid, (str, unicode)):
            q = {'name': rid, 'kind': 'head'}
        else:
            q = {'_id': rid, 'kind': 'head'}

        return ts.find_one(q)

    def _update_head(self, ref_name, kind):
        m = self.adapter.get_collection('meta')
        m.update({'name': 'HEAD'}, {'$set': {'ref': ref_name,
                                             'kind': kind}})

    def _get_head(self):
        m = self.adapter.get_collection('HEAD')
        return m.find_one({'name': 'HEAD'})

    def _digest(self, *args):
        sha = hashlib.sha1()
        for ai in args:
            sha.update(ai)
        return sha.hexdigest()

    @property
    def ncollections(self):
        return len(self.adapter.collection_names(include_system_collections=False))

#============= EOF =============================================

