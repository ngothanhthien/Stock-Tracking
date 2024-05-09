import re

import discord
from discord.ext import commands, tasks

from constant import DISCORD_BOT_TOKEN, DISCORD_TEST_CHANNEL_ID
from services import get_root_price, get_last_price, get_min_max_price, get_watch_list, get_own_list
from db import init_db

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)


def direction_percent(root: float, sub: float, option=None) -> str:
    option = {
        'prefix': True,
        'threshold': None,
        'up_color': 'green',
        'down_color': 'red',
        'with_root': False,
        'from_a_to_b': False,
        **(option or {})
    }
    if option['from_a_to_b']:
        percent_last = (sub - root) / root * 100
    else:
        percent_last = (root - sub) / sub * 100
    prefix = ''
    if option['prefix']:
        prefix = '+' if percent_last >= 0 else ''

    if option['threshold']:
        if percent_last > option['threshold']:
            percent_last_color = option['up_color']
        elif percent_last < 0:
            percent_last_color = option['down_color']
        else:
            percent_last_color = 'normal'
    else:
        percent_last_color = option['up_color'] if percent_last >= 0 else option['down_color']

    if abs(percent_last) > 12:
        percent_text = int(percent_last)
    elif abs(percent_last) > 1:
        percent_text = f'{percent_last:.1f}'
    else:
        percent_text = f'{percent_last:.2f}'
    full_percent_text = format_color(f'{prefix}{percent_text}%', percent_last_color) if abs(percent_last) > 0 else ''
    root_text = ''
    if option['with_root']:
        root_text = f'{root:.2f} '
    return f'{root_text}{full_percent_text}'


async def print_table_to_discord(table: list[dict[str, str]], title, channel=None) -> None:
    column_widths = {}
    label = table[0].keys()
    for key in label:
        max_column_width = len(key)
        for item in table:
            column_width = visible_length(str(item[key]))
            max_column_width = max(max_column_width, column_width)
        column_widths[key] = max_column_width

    header = " | ".join(key.ljust(column_widths[key]) for key in label)
    data_text = "```ansi\n" + title + "\n" + header + "\n"
    for item in table:
        row = " | ".join(custom_ljust(str(item[key]), column_widths[key]) for key in label)
        data_text += row + "\n"

    data_text += "```"
    if not channel:
        channel = bot.get_channel(int(DISCORD_TEST_CHANNEL_ID))
    await channel.send(data_text)


async def show_summary(channel=None) -> None:
    table = []
    option = {
        'prefix': False,
        'threshold': 15,
        'up_color': 'green',
        'down_color': 'red',
        'with_root': True
    }
    for code in get_watch_list():
        root_price = get_root_price(code)
        last_price = get_last_price(code)
        min_price_3m, max_price_3m = get_min_max_price(code, '3M')
        min_price_1y, max_price_1y = get_min_max_price(code, '1Y')
        min_price_3y, max_price_3y = get_min_max_price(code, '3Y')
        table.append({
            'Code': code,
            'Last': f'{last_price:.2f} {direction_percent(last_price, root_price)}',
            'Min 3M': min_price_3m,
            'Max 3M': direction_percent(max_price_3m, last_price, option),
            'Min 1Y': min_price_1y,
            'Max 1Y': direction_percent(max_price_1y, last_price, option),
            'Max 3Y': direction_percent(max_price_3y, last_price, option),
            'Min 3Y': min_price_3y,
        })
    await print_table_to_discord(table, summary_title(), channel)


async def show_own_list(channel=None) -> None:
    table = []
    option = {
        'prefix': False,
        'up_color': 'green',
        'down_color': 'red',
        'with_root': True
    }
    for stock in get_own_list():
        code = stock['code']
        buy_at = stock['buy_price']
        root_price = get_root_price(code)
        last_price = get_last_price(code)
        _, max_price_3m = get_min_max_price(code, '3M')
        _, max_price_1y = get_min_max_price(code, '1Y')
        _, max_price_3y = get_min_max_price(code, '3Y')

        table.append({
            'Code': code,
            'Available': f"{stock['available']}/{stock['total']}",
            'Buy at': f"{direction_percent(buy_at, last_price, {'with_root': True, 'from_a_to_b': True})}",
            'Direction': direction_percent(last_price, root_price),
            'Max 3M': direction_percent(max_price_3m, buy_at, option),
            'Max 1Y': direction_percent(max_price_1y, buy_at, option),
            'Max 3Y': direction_percent(max_price_3y, buy_at, option),
        })
    await print_table_to_discord(table, own_list_title(), channel)


def format_color(string: str, color: str) -> str:
    color_code = {'red': '31', 'green': '32', 'yellow': '33', 'blue': '34', 'purple': '35', 'cyan': '36',
                  'white': '37'}.get(color)
    return f'\x1b[2;{color_code}m{string}\x1b[0m' if color_code else string


def visible_length(s: str) -> int:
    return len(re.sub(r'\x1B\[[0-;]*[mK]', '', s))


def custom_ljust(s: str, width: int) -> str:
    needed = width - visible_length(s)
    return s + ' ' * needed


#font: SUB-ZERO
#size: 6pt
#https://www.asciiart.eu/text-to-ascii-art
def summary_title() -> str:
    return r"""
 ______     __  __     __    __     __    __     ______     ______     __  __   
/\  ___\   /\ \/\ \   /\ "-./  \   /\ "-./  \   /\  __ \   /\  == \   /\ \_\ \  
\ \___  \  \ \ \_\ \  \ \ \-./\ \  \ \ \-./\ \  \ \  __ \  \ \  __<   \ \____ \ 
 \/\_____\  \ \_____\  \ \_\ \ \_\  \ \_\ \ \_\  \ \_\ \_\  \ \_\ \_\  \/\_____\
  \/_____/   \/_____/   \/_/  \/_/   \/_/  \/_/   \/_/\/_/   \/_/ /_/   \/_____/
    """


def own_list_title() -> str:
    return r"""
 ______     __     __     __   __        __         __     ______     ______ 
/\  __ \   /\ \  _ \ \   /\ "-.\ \      /\ \       /\ \   /\  ___\   /\__  _\
\ \ \/\ \  \ \ \/ ".\ \  \ \ \-.  \     \ \ \____  \ \ \  \ \___  \  \/_/\ \/
 \ \_____\  \ \__/".~\_\  \ \_\\"\_\     \ \_____\  \ \_\  \/\_____\    \ \_\
  \/_____/   \/_/   \/_/   \/_/ \/_/      \/_____/   \/_/   \/_____/     \/_/
"""


async def check_owner(ctx) -> bool:
    if not (ctx.guild and ctx.author.id == ctx.guild.owner_id):
        await ctx.send("Permission denied.")
        return False
    return True


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    init_db()
    # await show_summary()
    # await show_own_list()


@bot.command()
async def ping(ctx):
    if await check_owner(ctx):
        await ctx.send('Pong!')


@bot.command(
    aliases=['show_o', 'sol', 'show_own']
)
async def c_show_own_list(ctx):
    await show_own_list(ctx)


@bot.command(
    aliases=['show_sm', 'ssl']
)
async def c_show_summary(ctx):
    await show_summary(ctx)


bot.run(DISCORD_BOT_TOKEN)
