#!/usr/bin/env python3
"""
Setup script for Audook
Alternative installation method using pip
"""

from setuptools import setup, find_packages
import sys

# Read requirements
with open('requirements.txt') as f:
 requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

# Read long description
with open('README.md', 'r', encoding='utf-8') as f:
 long_description = f.read()

setup(
 name='Audook',
 version='1.0.0',
 description='A modern audiobook client for Windows supporting Audiobookshelf and Plex',
 long_description=long_description,
 long_description_content_type='text/markdown',
 author='Audook Team',
 author_email='',
 url='https://github.com/pxomaker-hue/Audook',
 packages=find_packages(),
 package_data={
 'app': ['**/*.py'],
 'assets': ['**/*'],
 },
 include_package_data=True,
 install_requires=requirements,
 python_requires='>=3.10',
 entry_points={
 'gui_scripts': [
 'audook = main:main',
 ],
 },
 classifiers=[
 'Development Status :: 4 - Beta',
 'Intended Audience :: End Users/Desktop',
 'License :: OSI Approved :: MIT License',
 'Operating System :: Microsoft :: Windows',
 'Programming Language :: Python :: 3',
 'Programming Language :: Python :: 3.10',
 'Programming Language :: Python :: 3.11',
 'Programming Language :: Python :: 3.12',
 'Topic :: Multimedia :: Sound/Audio',
 'Topic :: Utilities',
 ],
 keywords='audiobook player audiobookshelf plex windows',
 project_urls={
 'Bug Reports': 'https://github.com/pxomaker-hue/Audook/issues',
 'Source': 'https://github.com/pxomaker-hue/Audook',
 },
)
