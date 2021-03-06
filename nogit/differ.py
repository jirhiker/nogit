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
from difflib import ndiff
from bson.json_util import dumps
from traits.api import HasTraits
from traitsui.api import View, Item

#============= standard library imports ========================
#============= local library imports  ==========================

class Differ(HasTraits):
    def __init__(self, left, right, *args, **kw):
        super(Differ, self).__init__(*args, **kw)

        if isinstance(left, dict):
            left=dumps(left, indent=4).split('\n')
        if isinstance(right, dict):
            right = dumps(right, indent=4).split('\n')

        self._left=left
        self._right=right

    def diff(self):
        return ndiff(self._left, self._right)


#============= EOF =============================================

