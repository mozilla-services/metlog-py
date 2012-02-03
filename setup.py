# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****

from setuptools import setup, find_packages

version = '0.1'

setup(name='metlog',
      version=version,
      description="Metrics Logging",
      long_description="""\
""",
      classifiers=[],  # Get strings from
                       # http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='Rob Miller',
      author_email='rmiller@mozilla.com',
      url='',
      license='MPLv2.0',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
          ],
      extras_require={
          'zeromqpub': ['pyzmq'],
          },
      tests_require=[
          'nose',
          'mock',
          'pyzmq',
          ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
