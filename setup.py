import os
from setuptools import setup

def readfile(*paths):
    """Build a file path from *paths* and return the contents."""
    with open(os.path.join(*paths), 'r') as f:
        return f.read()

setup(
    name = 'opto',
    py_modules = ['opto'],
    version = '0.1',
    description = 'Python interface to Optotune focus-tunable lenses',
    long_description=(readfile('README.rst')),
    license='MIT',

    author = 'Steven A. Cholewiak',
    author_email = 'steven@cholewiak.com',
    url = 'https://github.com/OrganicIrradiation/opto',
    download_url = 'https://github.com/OrganicIrradiation/opto/tarball/v0.1',
    keywords = ['Optotune', 'optics', 'lens'],
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules'],
    install_requires=['pyserial'],
)
