# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2012
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Victor Ng (vng@mozilla.com)
#   Rob Miller (rmiller@mozilla.com)
#
# ***** END LICENSE BLOCK *****

try:
    import simplejson as json
except:
    import json  # NOQA


try:
    import msgpack
except:
    msgpack = None  # NOQA


def json_encoder(msg):
    return json.dumps(msg)

def json_decoder(data):
    return json.loads(data)


def msgpack_encoder(msg):
    return msgpack.packb(msg)

def msgpack_decoder(data):
    return msgpack.unpackb(data)


default_encoder = json_encoder
