# -*- coding: utf-8 -*-

from os.path import join
from setuptools import setup, find_packages

version = '1.0dev-crom'

install_requires = [
    'cromlech.browser >= 0.5',
    'dawnlight >= 0.13b2',
    'crom',
    'grokker',
    'setuptools',
    'zope.component',
    'zope.interface',
    'zope.location',
    'zope.proxy',
    ]

tests_require = [
    'cromlech.browser [test]',
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
