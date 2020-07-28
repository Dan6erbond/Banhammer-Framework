import logging

__title__ = "banhammer"
__author__ = "Dan6erbond"
__license__ = "GNU General Public License v3 (GPLv3)"
__copyright__ = "© Copyright 2020 Dan6erbond"
__version__ = "2.3.4"
__tag__ = "beta"

BOT_VERSION_TEXT = "Banhammer.py v" + f"{__version__}-{__tag__}" if __tag__ else __version__

BOT_FOOTER = f"^({BOT_VERSION_TEXT} | /r/BanhammerBot | Join us on) ^[Discord](https://discord.gg/9JrGC8f)"
BOT_DISCLAIMER = "*This action was performed by the users of the [Banhammer.py](https://www.github.com/Dan6erbond/Banhammer.py) framework. " \
                 "Please [contact the moderators of this subreddit]({}) if you have any questions or concerns.*\n\n" + BOT_FOOTER

BANHAMMER_PURPLE = discord.Colour(0).from_rgb(207, 206, 255)

logging.root.setLevel(logging.NOTSET)
logger = logging.getLogger("banhammer")
