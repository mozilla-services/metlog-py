# ***** BEGIN LICENSE BLOCK *****
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2012
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Rob Miller (rmiller@mozilla.com)
#   Victor Ng (vng@mozilla.com)
#
# ***** END LICENSE BLOCK *****
import os
from setuptools import setup, find_packages

version = '0.9.8'

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()

setup(name='metlog-py',
      version=version,
      description="Metrics Logging",
      long_description=README,
      classifiers=[
          'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
          ],
      keywords='metlog metrics logging client',
      author='Rob Miller',
      author_email='rmiller@mozilla.com',
      url='https://github.com/mozilla-services/metlog-py',
      license='MPLv2.0',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
          'docopt',
          ],
      extras_require={
          'zeromqpub': ['pyzmq'],
          },
      tests_require=[
          'nose',
          'mock',
          'pyzmq',
          ],
      entry_points={
          'console_scripts': [
              'mb = metlog.command:mb',
              ],
          },
      )
