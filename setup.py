# -*- coding: utf-8 -*-

from os.path import join
from setuptools import setup, find_packages

version = '0.2b1'

install_requires = [
    'cromlech.browser',
    'cromlech.io',
    'dawnlight >= 0.13b2',
    'grokcore.component >= 2.4',
    'setuptools',
    'zope.component',
    'zope.interface',
    ]

tests_require = [
    'pytest',
    'zope.testing',
    ]

setup(
    name='cromlech.dawnlight',
    version=version,
    description="Dawnlight publisher for Cromlech applications.",
    long_description=(open("README.txt").read() + "\n\n" +
                      open(join("docs", "HISTORY.txt")).read()),
    classifiers=[
        "Programming Language :: Python",
        ],
    keywords='Cromlech Publisher',
    author='The Dolmen team',
    author_email='dolmen@list.dolmen-project.org',
    url='http://gitweb.dolmen-project.org',
    license='ZPL',
    packages=find_packages('src', exclude=['ez_setup']),
    package_dir={'': 'src'},
    namespace_packages=['cromlech'],
    include_package_data=True,
    zip_safe=False,
    tests_require=tests_require,
    install_requires=install_requires,
    extras_require={'test': tests_require},
    entry_points="""
    # -*- Entry points: -*-
    """,
    )
