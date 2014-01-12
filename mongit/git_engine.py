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
    adapter=Any

    def commit_tree(self, msg, tree_id):
        author = 'foo'

        commits = self.adapter.get_collection('commits')
        p = self.adapter._get_last('commits')
        commits.insert({
                        'pid': p['_id'] if p else None,
                        'tid': tree_id,
                        'msg': msg,
                        'author': author,
                        })

    def add_tree(self,name, blobs=None, trees=None):
        objects=self.adapter.get_collection('objects')
        print 'asf', name
        obj=objects.insert({'name':name,
                            'blobs':blobs,
                            'trees':trees})
        return obj

    def add_blob(self, tree, name, text):
        tree=self._get_tree(tree)
        blobs=tree['blobs']
        if not blobs:
            blobs=[]

        objs=self.adapter.get_collection('objects')
        gid=self._digest(name, text)

        r=objs.find_one({'gid':gid})
        if r:
            bid=r['_id']
            print 'already exists'
        else:
            bid=objs.insert({'name':name, 'text':text,
                            'gid':gid})
        if bid not in blobs:
            blobs.append(bid)
            # tree['blobs']=blobs
            # print tree['_id']
            objs.update({'_id':tree['_id']},
                        {'$set':{'blobs':blobs}})

    def _get_tree(self, tid):
        ts=self.adapter.get_collection('objects')
        return ts.find_one({'_id':tid})

    def _digest(self, *args):
        sha=hashlib.sha1()
        for ai in args:
            sha.update(ai)
        return sha.hexdigest()
#============= EOF =============================================

