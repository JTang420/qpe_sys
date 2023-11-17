# -*- coding: UTF-8 -*-
from setuptools import setup, find_packages, Extension
from Cython.Build import cythonize


metainfo = {
    'name': 'ywqpe',
    'version': '0.1.0',
    'description': 'Radar-based precipitation estimation and forecast',
    'author': ['Xiaowen Tang', 'JiaJia Tang'],
    'author_email': 'xtang@cuit.edu.cn',
    'license': 'GPL',
    'zip_safe': False,
    'install_requires': [
        'click==8.1.7',
        'cython==3.0.5',
        'netCDF4==1.6.5',
        'numpy==1.26.1',
        'pandas==2.1.2',
        'xarray==2023.10.1',
        'scipy==1.11.3'
      ]
}

setup(
    packages=find_packages(
        exclude=['*.src', '*.tests', '*.script']),
    ext_modules=cythonize(
        [Extension('ywqpe.oi_core', ['src/oi_core.c'])]),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'ywqpe=ywqpe.cli:cli']
    },
    **metainfo)
