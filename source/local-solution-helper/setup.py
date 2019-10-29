# coding: utf-8

from setuptools import setup, find_packages
# Solution Helper - 09/06/2018 - Pip version
# pip version handling
try: # for pip >= 10
    from pip._internal.req import parse_requirements
except ImportError: # for pip <= 9.0.3
    from pip.req import parse_requirements

setup(
    name='local_solution_helper',
    version='1.0',
    description='AWS Solution Helper Custom Resource',
    author='AWS Solutions Development',
    license='Apache 2.0',
    zip_safe=False,
    packages=['local_solution_helper', 'pycfn_custom_resource'],
    package_dir={'local_solution_helper': '.', 'pycfn_custom_resource' : './pycfn_custom_resource'},
    install_requires=[
        'requests>=2.22.0'
    ],
    classifiers=[
        'Programming Language :: Python :: 3.7',
    ],
)
