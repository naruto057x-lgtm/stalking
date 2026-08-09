# sitecustomize.py
# This file is auto-executed by Python before any script.
# It injects a fake discord.Intents class to allow scripts that use
# discord.Intents to run with discord.py-self, which lacks Intents.

import discord

# Try to import BaseFlags from discord.py-self (it should exist)
try:
    from discord.flags import BaseFlags, flag_value, fill_with_flags
except ImportError:
    # Fallback: a very simple fake class
    class FakeIntents:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
        @classmethod
        def default(cls):
            return cls(guilds=True, message_content=True)
        @classmethod
        def all(cls):
            return cls(guilds=True, members=True, presences=True, message_content=True)
    discord.Intents = FakeIntents
else:
    # Realistic fake using BaseFlags
    class Intents(BaseFlags):
        __slots__ = (
            'guilds', 'members', 'bans', 'emojis_and_stickers', 'integrations',
            'webhooks', 'invites', 'voice_states', 'presences', 'guild_messages',
            'dm_messages', 'guild_reactions', 'dm_reactions', 'guild_typing',
            'dm_typing', 'message_content', 'guild_scheduled_events', 'auto_moderation',
            'automod_configuration', 'automod_execution', 'guild_message_polls',
            'dm_message_polls'
        )

        @flag_value
        def guilds(self):
            return 1 << 0

        @flag_value
        def members(self):
            return 1 << 1

        @flag_value
        def bans(self):
            return 1 << 2

        @flag_value
        def emojis_and_stickers(self):
            return 1 << 3

        @flag_value
        def integrations(self):
            return 1 << 4

        @flag_value
        def webhooks(self):
            return 1 << 5

        @flag_value
        def invites(self):
            return 1 << 6

        @flag_value
        def voice_states(self):
            return 1 << 7

        @flag_value
        def presences(self):
            return 1 << 8

        @flag_value
        def guild_messages(self):
            return 1 << 9

        @flag_value
        def dm_messages(self):
            return 1 << 12

        @flag_value
        def guild_reactions(self):
            return 1 << 10

        @flag_value
        def dm_reactions(self):
            return 1 << 13

        @flag_value
        def guild_typing(self):
            return 1 << 11

        @flag_value
        def dm_typing(self):
            return 1 << 14

        @flag_value
        def message_content(self):
            return 1 << 15

        @flag_value
        def guild_scheduled_events(self):
            return 1 << 16

        @flag_value
        def auto_moderation(self):
            return 1 << 17

        @flag_value
        def automod_configuration(self):
            return 1 << 20

        @flag_value
        def automod_execution(self):
            return 1 << 21

        @flag_value
        def guild_message_polls(self):
            return 1 << 24

        @flag_value
        def dm_message_polls(self):
            return 1 << 25

        @classmethod
        def default(cls):
            self = cls()
            self.guilds = True
            self.message_content = True
            return self

        @classmethod
        def all(cls):
            self = cls()
            for attr in cls.__slots__:
                setattr(self, attr, True)
            return self

        @classmethod
        def none(cls):
            return cls()

    discord.Intents = Intents
