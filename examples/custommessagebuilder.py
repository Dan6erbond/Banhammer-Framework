from banhammer import messagebuilder


class CustomMessageBuilder(messagebuilder.MessageBuilder):
    def get_item_message(self, item):
        if item.type in ["submission", "comment"]:
            return "/u/{} posted a {} on /r/{}!\n\nhttps://www.reddit.com{}\n\n**Title:** {}\n**Body:**\n{}".format(
                item.item.author, item.type, item.item.subreddit, item.item.permalink, item.item.title,
                item.body)
        elif item.type == "modmail":
            return "New message in modmail conversation '{}' by /u/{}!\n\n{}".format(
                item.item.conversation.subject, item.item.author, item.body)
        else:
            return "/u/{} took an action on /r/{}!\n\n`{}`".format(item.item.mod, item.item.subreddit,
                                                                     item.body)
