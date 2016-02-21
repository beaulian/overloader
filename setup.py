from setuptools import setup, find_packages

setup(
    name='overloader',
    version='0.0.0',
    packages=find_packages(),
    url='https://github.com/boramalper/overloader',
    license='MIT',
    author='Mert Bora ALPER',
    author_email='bora@boramalper.org',
    description='Assisted Overloading for Python',
    long_description=open('README.md').read(),
    install_requires=['typing'],
)
