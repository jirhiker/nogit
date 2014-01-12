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
from datetime import datetime
import hashlib
from traits.api import HasTraits, Any
from traitsui.api import View, Item

#============= standard library imports ========================
#============= local library imports  ==========================

class GitEngine(HasTraits):
    adapter = Any

    def commit_tree(self, msg, tree_id):
        if not tree_id:
            return

        author = 'foo'

        commits = self.adapter.get_collection('commits')
        p = self.adapter._get_last('commits')
        tree = self._get_tree(tree_id)

        commits.insert({
            'pid': p['_id'] if p else None,
            'tid': tree['_id'],
            'msg': msg,
            'author': author })

    def add_tree(self, name, blobs=None, trees=None):
        objects = self.adapter.get_collection('objects')

        obj = objects.insert({'name': name,
                              'kind': 'tree',
                              'blobs': blobs,
                              'trees': trees})
        return obj

    def add_subtree(self, parent, name, blobs=None, trees=None):
        tree = self._get_tree(parent)

        objs = self.adapter.get_collection('objects')
        if trees:
            trees=[self._get_tree(ti)['_id'] for ti in trees]

        ntid = objs.insert({'name': name,
                            'kind': 'tree',
                            'blobs': blobs,
                            'trees': trees})

        ptrees = tree['trees']
        if not ptrees:
            ptrees=[]

        ptrees.append(ntid)
        tree['trees'] = ptrees
        tree.pop('_id')
        return objs.insert(tree)

    def modify_blob(self, tree, name, text):
        tree = self._get_tree(tree)

        objs = self.adapter.get_collection('objects')
        r = objs.find_one({'name': name})
        if r:
            rid = r['_id']
            if rid in tree['blobs']:
                #insert new blob
                r.pop('_id')
                r['text'] = text
                nid = objs.insert(r)

                blobs = tree['blobs']
                blobs.remove(rid)
                blobs.append(nid)

                #insert new tree
                tree.pop('_id')
                return objs.insert(tree)

    def add_blob(self, tree, name, text, new_tree=True):
        tree = self._get_tree(tree)
        tid = tree['_id']
        blobs = tree['blobs']

        objs = self.adapter.get_collection('objects')
        gid = self._digest(name, text)

        r = objs.find_one({'gid': gid})
        if r:
            bid = r['_id']
        else:
            bid = objs.insert({'name': name,
                               'kind':'blob',
                               'text': text,
                               'gid': gid})

        if not blobs:
            #use existing tree doc
            objs.update({'_id': tree['_id']},
                        {'$set': {'blobs': [bid]}})
        else:
            blobs.append(bid)
            if new_tree:
                #add new tree
                tree.pop('_id')
                tree['blobs'] = blobs
                tid = objs.insert(tree)
            else:
                objs.update(tree, {'$set': {'blobs': blobs}})

        return tid

    def _get_tree(self, tid):
        ts = self.adapter.get_collection('objects')
        if isinstance(tid, str):
            q = {'name': tid, 'kind':'tree'}
        else:
            q = {'_id': tid,  'kind':'tree'}

        return list(ts.find(q).sort('_id', -1).limit(1))[0]

    def _digest(self, *args):
        sha = hashlib.sha1()
        for ai in args:
            sha.update(ai)
        return sha.hexdigest()

#============= EOF =============================================

