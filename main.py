import re

import discord
from discord.ext import commands, tasks

from constant import DISCORD_BOT_TOKEN, DISCORD_TEST_CHANNEL_ID
from services import get_root_price, get_last_price, get_min_max_price, get_watch_list
from db import init_db

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)


async def show_summary(watch_list: list[str]) -> None:
    table = []
    label = ['Code', 'Last', 'Min 3M', 'Max 3M', 'Min 1Y', 'Max 1Y']
    for code in watch_list:
        root_price = get_root_price(code)
        last_price = get_last_price(code)
        min_price_3m, max_price_3m = get_min_max_price(code, '3M')
        min_price_1y, max_price_1y = get_min_max_price(code, '1Y')
        percent_last = (last_price - root_price) / root_price * 100
        percent_last_color = 'green' if percent_last >= 0 else 'red'
        prefix = '+' if percent_last >= 0 else ''
        percent_last_str = format_color(f'{prefix}{percent_last:.2f}%', percent_last_color)
        percent_3m = int((max_price_3m - last_price) / last_price * 100)
        percent_1y = int((max_price_1y - last_price) / last_price * 100)

        threshold = 15
        percent_3m_str = format_color(f'{percent_3m}%', 'green') if percent_3m >= threshold else f'{percent_3m}%'
        percent_1y_str = format_color(f'{percent_1y}%', 'green') if percent_1y >= threshold else f'{percent_1y}%'
        table.append({
            'Code': code,
            'Last': f'{last_price:.2f} {percent_last_str}',
            'Min 3M': min_price_3m,
            'Max 3M': f'{max_price_3m:.2f} {percent_3m_str}',
            'Min 1Y': min_price_1y,
            'Max 1Y': f'{max_price_1y:.2f} {percent_1y_str}',
        })

    column_widths = {}
    for key in label:
        max_column_width = len(key)
        for item in table:
            column_width = visible_length(str(item[key]))
            max_column_width = max(max_column_width, column_width)
        column_widths[key] = max_column_width

    header = " | ".join(key.ljust(column_widths[key]) for key in label)
    title = summary_title()
    data_text = "```ansi\n" + title + "\n" + header + "\n"
    for item in table:
        row = " | ".join(custom_ljust(str(item[key]), column_widths[key]) for key in label)
        data_text += row + "\n"

    data_text += "```"
    channel = bot.get_channel(int(DISCORD_TEST_CHANNEL_ID))
    await channel.send(data_text)


def format_color(string: str, color: str) -> str:
    color_code = {'red': '31', 'green': '32', 'yellow': '33', 'blue': '34', 'purple': '35', 'cyan': '36', 'white': '37'}.get(color)
    return f'\x1b[2;{color_code}m{string}\x1b[0m' if color_code else string

def visible_length(s: str) -> int:
    return len(re.sub(r'\x1B\[[0-;]*[mK]', '', s))

def custom_ljust(s: str, width: int) -> str:
    needed = width - visible_length(s)
    return s + ' ' * needed


#font: SUB-ZERO
#size: 6pt
def summary_title() -> str:
    return r"""
 ______     __  __     __    __     __    __     ______     ______     __  __   
/\  ___\   /\ \/\ \   /\ "-./  \   /\ "-./  \   /\  __ \   /\  == \   /\ \_\ \  
\ \___  \  \ \ \_\ \  \ \ \-./\ \  \ \ \-./\ \  \ \  __ \  \ \  __<   \ \____ \ 
 \/\_____\  \ \_____\  \ \_\ \ \_\  \ \_\ \ \_\  \ \_\ \_\  \ \_\ \_\  \/\_____\
  \/_____/   \/_____/   \/_/  \/_/   \/_/  \/_/   \/_/\/_/   \/_/ /_/   \/_____/
    """
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    init_db()
    watch_list = get_watch_list()
    await show_summary(watch_list)


@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')


bot.run(DISCORD_BOT_TOKEN)
