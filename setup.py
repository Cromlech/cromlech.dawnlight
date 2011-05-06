from setuptools import setup, find_packages
import os

version = '0.1a1'

install_requires = [
    'grokcore.component >= 2.3',
    'setuptools',
    'cromlech.browser',
    'cromlech.io',
    'dawnlight',
    ]

tests_require = [
    'pytest',
    'cromlech.browser[test]',
    ]

setup(name='cromlech.dawnlight',
      version=version,
      description="Dawnlight publisher for Cromlech Web Framework",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      classifiers=[
        "Programming Language :: Python",
        ],
      keywords='Cromlech Dolmen Framework',
      author='The Dolmen team',
      author_email='dolmen@list.dolmen-project.org',
      url='http://gitweb.dolmen-project.org/',
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
