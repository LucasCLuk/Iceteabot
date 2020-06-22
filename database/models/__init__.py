import typing

from .activity import Activity
from .channel import Channel
from .command_call import CommandCall
from .faq import FAQ
from .reaction_role import ReactionRole
from .guild import Guild, CommandStats
from .member import Member
from .model import Model
from .nickname import NickName
from .prefix import Prefix
from .reminder import Reminder
from .tag import Tag, TagLookup
from .tag_call import TagCall
from .task import Task
from .user import User

tables: typing.Dict[type, str] = {
    User: "users",
    Guild: "guilds",
    Reminder: "reminders",
    FAQ: "faqs",
    Activity: "activities",
    Member: "members",
    Tag: "tags",
    Prefix: "prefixes",
    NickName: "nicknames",
    Channel: "channels",
    Task: "tasks",
    CommandCall: "commands",
    TagLookup: "tagslink",
    TagCall: "tagcalls",
    ReactionRole: "reaction_role"
}
