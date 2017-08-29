from setuptools import setup, find_packages

def read_license():
    with open("LICENSE") as f:
        return f.read()

setup(
    name='swadge_game',
    version='1.0',
    description='Demo Swadge Game',
    long_description="""Demonstrates the use of the Swadge Game API in Python""",    
    license=read_license(),
    author='Dylan Whichard',
    author_email='dylwhich@magfest.org',
    url='https://swadge.com',
    keywords=[
        'swadge', 'magfest'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3 :: Only',
    ],
    install_requires=[
        'autobahn',
        'asyncio',
    ],
    entry_points={
        'console_scripts': [
            'swadge_game=game',
        ]
    },
)
