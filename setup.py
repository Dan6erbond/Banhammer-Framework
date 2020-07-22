import setuptools

from banhammer import __author__, __license__, __tag__, __version__

with open("README.md", "r", encoding="utf8") as f:
    long_description = f.read()

setuptools.setup(
    name="banhammer.py",
    version="{}-{}".format(__version__, __tag__) if __tag__ else __version__,
    license=__license__,
    author=__author__,
    author_email="moravrav@gmail.com",
    description="A Discord bot integration framework for Reddit moderation.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Dan6erbond/Banhammer.py",
    packages=setuptools.find_packages(include=['banhammer', 'banhammer.*']),
    package_data={'banhammer': ['WELCOME.md', 'reactions.yaml']},
    include_package_data=True,
    install_requires=[
        'discord.py>=1.1.1',
        'apraw>=0.6.0a0'
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Operating System :: OS Independent",
        "Topic :: Communications",
        "Topic :: Internet",
        "Topic :: Utilities",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
)

# classifiers can be found here: https://pypi.org/classifiers/
