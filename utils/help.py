from discord.ext import commands


class IceHelpCommand(commands.DefaultHelpCommand):

    def __init__(self, **options):
        super().__init__(**options)

    def get_command_signature(self, command):
        return f"{self.clean_prefix}{command.qualified_name} {command.signature}"

    def send_bot_help(self, mapping):
        return super().send_bot_help(mapping)
