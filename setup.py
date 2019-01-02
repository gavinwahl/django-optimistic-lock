import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='django-optimistic-lock',
    version='1.0.0',
    description='Offline optimistic locking for Django',
    url='https://github.com/gavinwahl/django-optimistic-lock',
    long_description=read('README.rst'),
    license='BSD',
    author='Gavin Wahl',
    author_email='gavinwahl@gmail.com',
    packages=['ool'],
    install_requires=['django >= 1.11'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
)
