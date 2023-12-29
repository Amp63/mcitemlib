from setuptools import setup, find_packages

VERSION = '0.1.0'

setup(
    name='mcitemlib',
    version=VERSION,
    description='A library for creating and editing Minecraft items using python.',
    author='Amp',
    url='https://github.com/Amp63/mcitemlib',
    license='MIT',
    keywords=['minecraft', 'item', 'block'],
    packages=find_packages()
)