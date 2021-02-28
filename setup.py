import re

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup
with open("invoker/__init__.py", 'r') as f:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', f.read(), re.MULTILINE).group(1)
setup(
    name="invoker",
    version=version,
    url="https://git.bilibili.co/live-test/invoker",
    license="MIT",
    author="Ark",
    author_email="lifangzhou@bilibili.com",
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    description="live api test framework",
    long_description=open("README.md", 'r', encoding='utf-8').read(),
    zip_safe=False,
    entry_points={
        'pytest11': ['invoker = invoker.plugin']
    },
    install_requires=[
        "rich",
        "aiohttp",
        "aioredis",
        "aiomysql",
        "allure-pytest",
        "allure-python-commons",
        "attrdict",
        "deepdiff",
        "grpcio-tools",
        "jsonpath_ng",
        "motor",
        "pre-commit",
        "pymemcache",
        "pymongo",
        "pymysql",
        "pytest",
        "pytest-rerunfailures",
        "pytest-html",
        "python-json-logger",
        "pytz",
        "redis",
        "requests",
        "simplejson",
        "termcolor",
        "mitmproxy",
        "bitstring",
        "apscheduler",
    ],
)
