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
class NoBranchError(BaseException):
    def __init__(self, name):
        super(NoBranchError, self).__init__()
        self._name = name

    def __repr__(self):
        return 'No branch named "{}"'.format(self._name)


class GitEngine(HasTraits):
    adapter = Any

    @property
    def master(self):
        """
            return the master ref
        """
        return self._get_ref('master')

    def init(self):
        """
            add some defaults
        """
        m = self.adapter.get_collection('meta')
        if not m.find_one({'name': 'HEAD'}):
            m.insert({'name': 'HEAD', 'ref': 'master', 'kind': 'head'})

        if not self._get_ref('master'):
            self.add_ref('master', None)

    def checkout(self, name):
        """
            checkout a ref. (branch or tag)

        """
        ref = self._get_ref(name)
        if ref is None:
            raise NoBranchError(name)
        else:
            self._update_head(ref['name'], ref['kind'])

    def plog(self):
        """
            print the return of self.log
        """
        for p in self.log():
            print p

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

        return [assemble_log(c) for c in self._walk_commits()]

    def add_tag(self, name, commit_id):
        return self.add_ref(name, commit_id, kind='tag')

    def add_branch(self, name, commit_id=None):
        """
            add a branch named ``name``. if commit_id is None use the latest commit
        """
        if not commit_id:
            commit_id = self.adapter.get_last('commits')['_id']

        b = self.add_ref(name, commit_id)

        #update HEAD
        self._update_head(name, 'head')
        # h = self.adapter.get_collection('HEAD')
        # h.update({'name': 'HEAD'}, {'$set': {'ref': name, 'kind': 'head'}})
        # self.checkout(name)
        return b

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
            trees = [self._get_tree(ti)['_id'] for ti in trees]

        ntid = objs.insert({'name': name,
                            'kind': 'tree',
                            'blobs': blobs,
                            'trees': trees})

        ptrees = tree['trees']
        if not ptrees:
            ptrees = []

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
                               'kind': 'blob',
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

    def _get_commit(self, cid):
        ts = self.adapter.get_collection('commits')
        q = {'_id': cid}
        return ts.find_one(q)

    def _get_ref(self, rid):
        ts = self.adapter.get_collection('refs')
        if isinstance(rid, (str, unicode)):
            q = {'name': rid, 'kind': 'head'}
        else:
            q = {'_id': rid, 'kind': 'head'}

        return ts.find_one(q)

    def _get_tree(self, tid):
        ts = self.adapter.get_collection('objects')
        if isinstance(tid, (str, unicode)):
            q = {'name': tid, 'kind': 'tree'}
        else:
            q = {'_id': tid, 'kind': 'tree'}

        return list(ts.find(q).sort('_id', -1).limit(1))[0]

    def _update_head(self, ref_name, kind):
        m = self.adapter.get_collection('meta')
        m.update({'name': 'HEAD'}, {'$set': {'ref': ref_name,
                                             'kind': kind}})

    def _get_head(self):
        m = self.adapter.get_collection('meta')

        return m.find_one({'name': 'HEAD'})

    def _digest(self, *args):
        sha = hashlib.sha1()
        for ai in args:
            sha.update(ai)
        return sha.hexdigest()

#============= EOF =============================================

