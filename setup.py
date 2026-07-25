#!/usr/bin/env python3
"""
Script d'installation pour Audook
Méthode d'installation alternative en utilisant pip
"""

from setuptools import setup, find_packages
import sys

# Lire les dépendances
with open('requirements.txt') as f:
 requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

# Lire la description longue
with open('README.md', 'r', encoding='utf-8') as f:
 long_description = f.read()

setup(
 name='Audook',
 version='1.0.0',
 description='Un client moderne de livres audio pour Windows prenant en charge Audiobookshelf et Plex',
 long_description=long_description,
 long_description_content_type='text/markdown',
 author='Équipe Audook',
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
 'Natural Language :: French',
 ],
 keywords='lecteur livres audio audiobookshelf plex windows',
 project_urls={
 'Bug Reports': 'https://github.com/pxomaker-hue/Audook/issues',
 'Source': 'https://github.com/pxomaker-hue/Audook',
 },
)
