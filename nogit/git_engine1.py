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

        m = self.adapter.get_collection('index')
        if not m.find_one({'name': 'index'}):
            m.insert({'name': 'index', 'trees': [],'blobs':[], 'objects':[]})

        self.add_tree('/')

    def checkout(self, name):
        """
            checkout a ref. (branch or tag)

        """
        ref = self._get_ref(name)
        if ref is None:
            raise NoBranchError(name)
        else:
            self._update_head(ref['name'], ref['kind'])

    def commit(self, msg):
        t=self.generate_tree()
        self.commit_tree(msg, t)

    def pstatus(self):
        """
            show contents of the index diffed against the last commit
        """
        for p in self.status():
            print p

    def plog(self):
        """
            print the return of self.log
        """
        for p in self.log():
            print p

    def status(self):
        idx=self._get_index()
        template='''# On branch "{}"
# Changes to be committed:

{}
'''

        def assemble_object(tree, oi, action):
            blob=self._get_blob(oi)
            if tree=='/':
                tree=''
            else:
                tree='{}/'.format(tree[1:])

            return '#        {}:    {}{}'.format(action, tree,blob['name'])

        head=self._get_head()
        branch=head['ref']
        changes='\n'.join([assemble_object(*o) for o in idx['objects']])
        txt=template.format(branch, changes)
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

    def generate_tree(self):
        idx=self._get_index()
        objs=self.adapter.get_collection('objects')
        c=self.adapter.get_collection('commits')

        for root, oi, action in idx['objects']:
            t = self._get_tree(root)

            blobs = t['blobs']
            if not blobs:
                blobs = []

            blobs.append(oi)
            objs.update({'_id': t['_id']},
                        {'$set': {'blobs': blobs}})

        if not c.count():

            #use existing empty root tree
            objs.update({'name':'/'}, {'$set':{'kind': 'tree',
                                       'blobs': idx['blobs'],
                                       'trees': idx['trees']}})
            return objs.find_one({'name':'/'})['_id']

        else:
            return objs.insert({'name':'/',
                            'kind':'tree',
                            'blobs':idx['blobs'],
                            'trees':idx['trees']})

        # for tree, oi, action in idx['objects']:
        #     if tree=='/':
        #         tree = self._get_tree(tree)
        #         tid = tree['_id']
        #         blobs = tree['blobs']
        #
        #         if not blobs:
        #             #use existing tree doc
        #             objs.update({'_id': tree['_id']},
        #                         {'$set': {'blobs': [oi]}})
        #         else:
        #             blobs.append(oi)
        #             # if new_tree:
        #                 #add new tree
        #             tree.pop('_id')
        #             tree['blobs'] = blobs
        #             tid = objs.insert(tree)
        #
        # return tid
                # else:
                #     objs.update(tree, {'$set': {'blobs': blobs}})

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
        self._clear_stage()

    def add_tree(self, name, blobs=None, trees=None):
        obj=self._get_blob(name, key='name')
        if not obj:
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

        hastree=False
        if trees:
            hastree= next((ti for ti in tree['trees']
                           if objs.find_one({'name': ti})), None)

        if not hastree:
            ntid = objs.insert({'name': name,
                                'kind': 'tree',
                                'blobs': blobs,
                                'trees': trees})

        ptrees = tree['trees']
        if not ptrees:
            ptrees = []

        ptrees.append(ntid)
        objs.update({'_id':tree['_id']}, {'$set':{'trees':ptrees}})
        # tree['trees'] = ptrees
        # tree.pop('_id')
        # return objs.insert(tree)

    def modify_blob(self, tree, name, text):
        tree = self._get_tree(tree)
        col = self.adapter.get_collection('objects')

        action = None
        for bid in tree['blobs']:
            bi=col.find_one({'_id':bid})
            if bi['name']==name:
                rtree=self._get_index()

                gid = self._digest(tree['name'], name, text)

                for b in rtree['blobs']:
                    # print b, bid,name
                    b = self._get_blob(b)
                    if b['name'] == name:
                        gid = self._digest(tree['name'], name, text)
                        col.update({'_id': b['_id']},
                                   {'$set': {'text': text, 'gid': gid}})
                        nid = b['_id']
                        break
                else:
                    bi.pop('_id')
                    bi['gid']=gid
                    bi['text']=text
                    nid=col.insert(bi)
                    action='modified'

                self._stage_blob(tree['_id'], nid, action=action, remove=bid)
                break

    def add_blob(self, tree, name, text):
        col = self.adapter.get_collection('objects')
        gid = self._digest(tree, name, text)

        r = col.find_one({'gid': gid})
        if not r:

            rtree = self._get_index()

            #is this blob name already in the index
            #if so update blob doc
            action=None
            for b in rtree['blobs']:
                b=self._get_blob(b)
                if b['name']==name:
                    col.update({'_id':b['_id']},
                                {'$set':{'text':text, 'gid':gid}})
                    bid=b['_id']
                    break
            else:
                # objs = rtree['objects']
                bid = col.insert({'name': name,
                               'kind': 'blob',
                               'text': text,
                               'gid': gid})
                action='new file'
                # objs.append((tree,bid,'new file'))

            self._stage_blob(tree, bid, action)

    def _stage_blob(self, tree, bid, action=None, remove=None):
        objs = self._get_index()['objects']
        if action is not None:
            objs.append((tree, bid, action))

        blobs=[]
        trees=[]

        root = self._get_tree('/')
        trees = root['trees']
        blobs = root['blobs']

        idx = self.adapter.get_collection('index')
        idxdoc=idx.find_one()

        if tree=='/':
            blobs=idxdoc['blobs']
            if not blobs:
                blobs = []
            blobs.append(bid)
        else:
            tree=self._get_tree(tree)
            trees=idxdoc['trees']
            if not trees:
                trees=[]

            trees.append(tree['_id'])

        if remove:
            if not hasattr(remove, '__iter__'):
                remove=(remove,)
            for ri in remove:
                blobs.remove(ri)

        # print blobs
        d={'blobs':blobs, 'trees':trees}
        if objs is not None:
            d['objects']=objs

        idx.update({'name': 'index'}, {'$set':d})

    def _clear_stage(self):
        idx = self.adapter.get_collection('index')
        idx.update({'name': 'index'}, {'$set': {'objects': [],
                                                'trees':[],
                                                'blobs':[]}})

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
            root=list(ts.find({'name': '/',
                               'kind': 'tree'}).sort('_id', -1).limit(1))[0]

            for pp in tid.split('/'):
                # print pp
                if not pp:
                    continue

                for ti in root['trees']:
                    tt=self._get_blob(ti)
                    # print pp, ti, tt['name']
                    if tt['name']==pp:
                        root=tt
            return root
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

    def _get_index(self):
        m = self.adapter.get_collection('index')
        return m.find_one({'name': 'index'})

    def _get_blob(self, value, key='_id'):
        m=self.adapter.get_collection('objects')
        return m.find_one({key:value})

    def _digest(self, *args):
        sha = hashlib.sha1()
        for ai in args:
            sha.update(ai)
        return sha.hexdigest()

#============= EOF =============================================

