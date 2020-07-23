# Banhammer.py
By [Mariavi](https://dan6erbond.github.io/mariavi)

**Banhammer.py** is a framework that allows you to build your very own Banhammer! *Banhammer* is the concept that got Mariavi started and pursues the goal of bringing subreddit moderation to your very own Discord server. By streaming any and all moderatable items to Discord channels and allowing users to then moderate the subreddit through a joint bot account using **Reactions**, there's no need to use Reddit's moderation interface anymore!

## Features
 - Streaming new and reported posts to your Discord bot.
 - Adding and handling reactions.
 - Fetching reactions from subreddit wiki.
 - Changing bot presence on Discord.
 - Generating embeds and messages for items and actions.

## Usage
### Installation
Currently the PyPi release of Banhammer.py has not been tested which is why we recommend cloning the repository to your local machine after which you can `cd` into the directory with the files to install the requirements which are notated in the [requirements.txt](requirements.txt) file:
 - `pip install -r requirements.txt`

### Quick Example
Once the dependencies have been installed, the bot can be created. For that the general structure of a Discord `Client` or `Bot` (if commands are of importance use `Bot`) needs to be created and then Banhammer initialized as well as ran.

```python
import discord
from discord.ext import commands

from banhammer import banhammer
from banhammer import subreddit

bot = commands.Bot(command_prefix='>')
reddit = praw.Reddit(client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
                     password=PASSWORD, username=USERNAME, user_agent=USER_AGENT)
bh = banhammer.Banhammer(reddit, bot=bot)
bh.add_subreddits(subreddit.Subreddit(bh, SUBNAME))

@bot.event
async def on_command_error(ctx, error):
    print(error)

@bot.event
async def on_ready():
    print(str(bot.user) + ' is running.')
    bh.run()

@bh.new()
async def handle_new(p):
    msg = await bot.get_channel(CHANNEL_ID).send(embed=await p.get_embed())
    await p.add_reactions(m)

bot.run(TOKEN)
```

`bh.run()` must be called so that Banhammer can start the internal event loop. More examples can be found in the (examples)[examples] folder or in the [Banhacker](https://github.com/Dan6erbond/Banhacker) as well as the [D6B](https://github.com/Dan6erbond/D6B) GitHub repositories that both show different (and more complex) implementations of the framework.

## Contributing
Banhammer.py is open-source! That means we'd love to see your contributions and hopefully be able to accept them in the next release. If you want to become a contributor, try to follow these rules to keep the code clean:
 - Variable and file names must be written in snake-case. (eg. `variable_name`)
 - Class names must be pascal-case. (eg. `ClassName`)
 - Only use `async` where necessary.
 - Use the OOP approach; create classes when it makes sense.
 - Document as much as you can, preferably with inline comments.
 - Use the Google Style docstring format.
 - Store data in JSON, INI or YAML format to eliminate dependencies for other formats.
 - Create an `__init__.py` file for sub-modules.
 - Don't use f-strings as they aren't supported in older versions of Python.

## Roadmap
 - [x] Returning actions performed.
 - [x] Improved support for modmail.
 - [x] `MessageBuilder` object to create custom messages/embeds.
 - [ ] `save()` function for `Subreddit` object.
 - [x] Support for newer PRAW features (such as locking comments).
 - [ ] Validation of inputs.
 - [x] Better exception handling and outputs.
 - [ ] Support for variable function arguments.

## Links
 - [Documentation](https://dan6erbond.github.io/mariavi/banhammer-py.html)
 - [Official Discord server](https://discordapp.com/invite/9JrGC8f)
 - [PyPi Release](https://pypi.org/project/banhammer.py/)
 - [Discord.py](https://discordpy.readthedocs.io/en/latest)
 - [PRAW](https://praw.readthedocs.io/en/latest)
 - [Mariavi](https://dan6erbond.github.io/mariavi)

### Contributors
The awesome people that worked on this framework and its idea to make it a reality!
 - [Dan6erbond](https://dan6erbond.github.io) (Dan6erbond#2259)
 - [lydocia](https://www.lydocia.com) (lydocia#2301)

### Users
Some bots that makes use of this framework.
 - [Banhammer](https://dan6erbond.github.io/mariavi/banhammer.html)
 - [Banhacker](https://github.com/Dan6erbond/Banhacker)
 - [D6B](https://github.com/Dan6erbond/D6B)
