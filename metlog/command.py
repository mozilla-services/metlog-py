#!/usr/bin/env python
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
#   Rob Miller (rmiller@mozilla.com)
#
# ***** END LICENSE BLOCK *****
from docopt import docopt
from metlog.config import client_from_dict_config, client_from_stream_config

mb_doc = """mb: MetlogBench, blast messages at a Metlog router.

Usage:
  mb HOST PORT [--metlogcfg=<ini file>]

Arguments:
  HOST             Hostname or IP address of metlog router to test
  PORT             Port on which metlog router is listening

Options:
  --metlogcfg=<ini file>        Path to metlog client config file
"""


def mb():
    arguments = docopt(mb_doc)
    host = arguments.get('HOST')
    port = int(arguments.get('PORT'))

    DEFAULT_CONFIG = {'logger': 'mb',
                      'sender': {'class': 'metlog.senders.udp.UdpSender',
                                 'args': (host, port),
                                 },
                      }

    if arguments.get('--metlogcfg'):
        with open(arguments['--metlogcfg']) as cfgfile:
            client = client_from_stream_config(cfgfile, 'metlog')
    else:
        client = client_from_dict_config(DEFAULT_CONFIG)

    while True:
        client.metlog('MBTEST', payload='MBTEST')
