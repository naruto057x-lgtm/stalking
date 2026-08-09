import discord

# لو Intents مش موجودة، نضيف نسخة وهمية
if not hasattr(discord, 'Intents'):
    class DummyIntents:
        def __init__(self, **kwargs):
            self.value = kwargs.get('default', True)
            for k, v in kwargs.items():
                setattr(self, k, v)

        @classmethod
        def default(cls):
            return cls(messages=True, message_content=True)

        @classmethod
        def all(cls):
            return cls(messages=True, message_content=True, presences=True, members=True)

    discord.Intents = DummyIntents
