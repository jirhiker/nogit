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
from traits.api import HasTraits, Str, Int
from traitsui.api import View, Item
from pymongo import MongoClient
#============= standard library imports ========================
#============= local library imports  ==========================


class MongoAdapter(HasTraits):
    host=Str('localhost')
    port=Int(27017)
    database_name=Str('nogit')

    def __init__(self, *args, **kw):
        super(MongoAdapter, self).__init__(*args, **kw)
        self.connect()

    def drop_database(self):
        self._client.drop_database(self.database_name)

    def connect(self):
        self._client = MongoClient(self.host, self.port)
        self._db = self._client[self.database_name]

    def get_collection(self, *args):
        return self._get_collection(*args)

    def _get_collection(self, collection):
        col=self._db[collection]
        return col

    def get_last(self, collection):
        """
            return the last document in collection
        """
        c=self._get_collection(collection)
        r=c.find().sort('_id', -1).limit(1)
        try:
            return list(r)[0]
        except IndexError:
            return

    def __getattr__(self, item):
        if hasattr(self._db, item):
            return getattr(self._db, item)





#============= EOF =============================================

