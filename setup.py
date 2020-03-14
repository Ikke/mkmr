from setuptools import setup

__author__ = 'Leo'
__version__ = '0.0.2'
__contact__ = 'thinkabit.ukim@gmail.com'
__url__ = 'https://github.com/maxice8/mkmr'
__license__ = 'GPL-3.0-or-later'

setup(name='mkmr',
      version=__version__,
      description="Convenient tools to make merge requests to any GitLab host",
      author=__author__,
      author_email=__contact__,
      url=__url__
      packages=['mkmr'],
      zip_safe=False,
      license=__license__,
      platforms='any',
      classifiers=[
          'Topic :: Utilities',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: GPL-3.0-or-later',
          'Development Status :: 2 - Pre-Alpha',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.8',
      ],
      entry_points={
          'console_scripts': ['mkmr=mkmr.mkmr:main'],
      },
      install_requires=[
          'gitpython>=3.0.0,<4',
          'python-gitlab>=2.0.0,<3',
          'python-editor>=1.0.0,<2',
          'inquirer>=2.6.0,<3',
      ])
