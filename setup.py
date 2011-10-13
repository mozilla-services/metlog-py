from setuptools import setup, find_packages
import sys, os

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
      license='MPLv1.1',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
