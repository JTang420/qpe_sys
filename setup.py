# -*- coding: UTF-8 -*-
from setuptools import setup, find_packages


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
        'netCDF4==1.6.5',
        'numba==0.58.1',
        'numpy==1.26.1',
        'pandas==2.1.2',
        'xarray==2023.10.1',
        'scipy=1.11.3'
      ]
}

setup(
    packages=find_packages(
        exclude=['*.src', '*.tests', '*.script']),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'ywqpe=ywqpe.cli:cli']
    },
    **metainfo)
