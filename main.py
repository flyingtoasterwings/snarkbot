from typing import Final
import os
from dotenv import load_dotenv
from discord import Intents, Client, Message
from responses import get_response
from commands import parse_command, check_if_authorized

load_dotenv()
TOKEN: Final[str] = os.getenv('DISCORD_TOKEN')

intents: Intents = Intents.default()
intents.message_content = True
intents.members = True
client: Client = Client(intents=intents)

async def send_message(message: Message, user_message: str) -> None:
    if not user_message:
        print('(Message was empty)')
        return

    is_private = (user_message[0] == '?')
    if is_private:
        user_message = user_message[1:]

    try:
        response: str = get_response(user_message)
        await message.author.send(response) if is_private else await message.channel.send(response)
    except Exception as e:
        print(e)

def basic_message_stat_dump(message):
    print(f"Got message: {message.content}")
    print(f"-> channel: {message.channel}")
    print(f"-> author: {message.author.name}")
    print(f"-> guild: {message.guild.id}")
    print(f"-> channel {message.channel} in category {message.channel.category}")


@client.event
async def on_ready() -> None:
    print(f'{client.user} is now running!')

@client.event
async def on_message(message: Message) -> None:
    if message.author == client.user:
        return

    if message.author.bot:
        return 

    if (not message.author.guild_permissions.administrator) and (not check_if_authorized(message.author)):
        return

    username: str = str(message.author)
    user_message: str = message.content
    channel: str = str(message.channel)

    basic_message_stat_dump(message)

    print(f'[{channel}] {username}: "{user_message}"')
    await parse_command(message)

def main() -> None:
    client.run(token=TOKEN)


if __name__ == '__main__':
    main()

