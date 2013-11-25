import os
import re
from setuptools import setup


here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README')).read()
CHANGES = open(os.path.join(here, 'CHANGES')).read()

with open(os.path.join(here, 'flask_dogpile_cache.py')) as main_file:
    pattern = re.compile(r".*__version__ = '(.*?)'", re.S)
    VERSION = pattern.match(main_file.read()).group(1)


setup(name='Flask-Dogpile-Cache',
      version=VERSION,
      description="A caching front-end based on the Dogpile lock.",
      long_description=open(README).read(),
      keywords='caching',
      author='Vitalii Ponomar',
      author_email='vitalii.ponomar@gmail.com',
      url='http://bitbucket.org/ponomar/flask-dogpile-cache',
      license='BSD',
      packages=['flask_dogpile_cache'],
      namespace_packages=['dogpile'],
      zip_safe=False,
      platforms='any',
      install_requires=['Flask',
                        'dogpile.cache>=0.5.2'],
      classifiers=['Development Status :: 4 - Beta',
                   'Environment :: Web Environment',
                   'Intended Audience :: Developers',
                   'License :: OSI Approved :: BSD License',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python'],
)
