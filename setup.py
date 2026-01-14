from setuptools import setup, find_packages

setup(
    name='zyphus-engine',
    version='2.0.0.post1',
    packages=find_packages(where='/home/ubuntu/Zyphus/Zyphus/src'),
    package_dir={'': '/home/ubuntu/Zyphus/Zyphus/src'},
    include_package_data=True,
    install_requires=[
        'click',
        'psutil',
        'watchdog',
        'lz4',
        'python-dotenv',
        'SQLAlchemy',
        'greenlet',
        'attrs',
        'propcache',
        'typing_extensions',
    ],
    entry_points={
        'console_scripts': [
            'zyphus=main:cli',
        ],
    },
    author='Zyphus Developer',
    description='A fully CLI-based DEVmind Fusion Engine.',
    long_description=open('README.md').read() if 'README.md' else '',
    long_description_content_type='text/markdown',
)
