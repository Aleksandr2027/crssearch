from setuptools import setup, find_packages

setup(
    name="XML_search",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        'python-telegram-bot>=20.7',
        'python-dotenv>=1.0.0',
        'lxml>=4.9.3',
        'psycopg2-binary>=2.9.9',
        'shapely>=2.0.2',
        'numpy>=1.24.3',
        'unidecode>=1.3.6',
        'pytz>=2024.1',
        'typing-extensions>=4.5.0',
        'ujson>=5.8.0',
        'aiohttp>=3.8.5',
        'pyproj>=3.6.1',
        'pandas>=2.0.3',
        'requests>=2.31.0',
        'asyncio>=3.4.3',
        'httpx>=0.25.2',
        'transliterate>=1.10.2',
        'python-Levenshtein>=0.25.0',
        'pywin32>=306'
    ],
    python_requires='>=3.11',
) 