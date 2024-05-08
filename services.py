import requests
from typing import Literal

from tinydb import Query

from constant import TIME_OUT, get_url
from db import db, insert_price_record, get_price_record, get_stock_account_id_record, insert_stock_account_id_record
from auth import get_auth_headers
from utils import convert_date_to_timestamp, now, expiry_plus
from type import PriceRecord, PriceReturn, OwnStock, PriceLength


def fetch_watch_list() -> set[str]:
    url = get_url('watch_list', auth=True)
    headers = get_auth_headers()
    response = requests.get(url, headers=headers, timeout=TIME_OUT)
    parsed = response.json()
    watch_lists = parsed.get('d', [])
    if not bool(watch_lists):
        raise ValueError("Invalid response")
    watch_list = set()
    for watch in watch_lists:
        symbols = watch.get('symbols', [])
        if bool(symbols):
            watch_list.update(symbols)
    return {item for item in watch_list if item}


def get_watch_list() -> list[str]:
    watch_list = db.table('settings').search(Query().name == 'watch_list')
    if watch_list:
        watch_list = watch_list[0]['value']
    if len(watch_list) == 0:
        watch_list = fetch_watch_list()
        db.table('settings').update({'name': 'watch_list', 'value': list(watch_list)})
    return watch_list


def determine_root_and_sub_price(root: float, sub: float, last: float) -> tuple[float, float]:
    # return root, sub
    if sub == last: # cache
        return root, sub

    price_direction_consistent = (root > sub) == (sub > last)
    if price_direction_consistent:
        return root, last

    return sub, last


def get_root_price(code: str) -> float:
    root_record: PriceRecord = get_price_record(code=code, price_type='root', length=None)
    sub_root_record: PriceRecord = get_price_record(code=code, price_type='sub root', length=None)
    last_price = get_last_price(code)
    if not root_record or not sub_root_record:
        root, _ = init_root_price(code)
        return root

    root, sub_root = determine_root_and_sub_price(root_record['price'], sub_root_record['price'], last_price)
    if not root == root_record['price']:
        insert_price_record(code, None, {'expiry': None, 'price': root}, 'root')
    if not sub_root == sub_root_record['price']:
        insert_price_record(code, None, {'expiry': None, 'price': sub_root}, 'sub root')

    return root


def init_root_price(code: str) -> tuple[float, float]:
    """Example: root = None, sub_root = None, prices = [10, 20, 30, 25, 20, 36], return root = 20 and sub_root = 36
        Explain:
        value - root - sub_root
        10    - 10   - None
        20    - 10   - 20
        30    - 10   - 30
        25    - 30   - 25
        20    - 30   - 20
        36    - 20   - 36
    """
    url = get_url('price_chart').format(code=code, type='1M')
    response = requests.get(url, timeout=TIME_OUT)
    parsed = response.json()

    prices = parsed.get('PriceHistory', [])
    prices.sort(key=lambda x: convert_date_to_timestamp(x.get('TradingDate')))
    if not bool(prices):
        raise ValueError("Invalid response: PriceHistory is empty")

    prices_value = [price.get('ClosePrice') for price in prices]
    root, sub_root = None, None
    for value in prices_value:
        if value is None:
            raise ValueError("Invalid response: ClosePrice is missing")

        if not root:
            root = value
            continue
        if not sub_root:
            sub_root = value
            continue
        root, sub_root = determine_root_and_sub_price(root, sub_root, value)

    root = format_price(root)
    sub_root = format_price(sub_root)
    db.table('prices').insert_multiple([
        {'code': code, 'price': root, 'type': 'root'},
        {'code': code, 'price': sub_root, 'type': 'sub root'}
    ])
    return root, sub_root


def fetch_last_price_and_save(code: str) -> PriceRecord:
    url = get_url('price_chart').format(code=code, type='1W')
    response = requests.get(url, timeout=TIME_OUT)
    parsed = response.json()

    prices = parsed.get('PriceHistory', [])
    if not bool(prices):
        raise ValueError("Invalid response: PriceHistory is empty")

    prices.sort(key=lambda x: convert_date_to_timestamp(x.get('TradingDate')))
    last_price = prices[-1].get('ClosePrice')
    if last_price is None:
        raise ValueError("Invalid response: ClosePrice is missing")

    return insert_price_record(code, None, {
        'expiry': now() + expiry_plus('end_day'),
        'price': format_price(last_price)
    }, 'last')


def get_last_price(code: str) -> float:
    last_price: PriceRecord = get_price_record(code=code, price_type='last', length=None) or fetch_last_price_and_save(code)
    return last_price['price']


def fetch_min_max_price(code: str, length: Literal['3M', '1Y', '3Y']) -> tuple[PriceReturn, PriceReturn]:
    url = get_url('price_chart').format(code=code, type=length)
    response = requests.get(url, timeout=TIME_OUT)
    parsed = response.json()

    prices = parsed.get('PriceHistory', [])
    if not bool(prices):
        raise ValueError("Invalid response")

    max_value, min_value = float('-inf'), float('inf')
    date_of_max, date_of_min = None, None
    for price in prices:
        close_price = price.get('ClosePrice')
        trading_date = price.get('TradingDate')
        if close_price is None or trading_date is None:
            missing_key = 'ClosePrice' if close_price is None else 'TradingDate'
            raise ValueError(f"Invalid response key: {missing_key}")

        if close_price > max_value:
            max_value, date_of_max = close_price, trading_date
        if close_price < min_value:
            min_value, date_of_min = close_price, trading_date

    max_price: PriceReturn = {
        'expiry': convert_date_to_timestamp(date_of_max) + expiry_plus(length),
        'price': format_price(max_value)
    }
    min_price: PriceReturn = {
        'expiry': convert_date_to_timestamp(date_of_min) + expiry_plus(length),
        'price': format_price(min_value)
    }

    return min_price, max_price


def get_min_max_price(code: str, length: Literal['3M', '1Y', '3Y']) -> tuple[float, float]:
    min_price: PriceRecord = get_price_record(code, 'min', length)
    max_price: PriceRecord = get_price_record(code, 'max', length)
    if not min_price or not max_price:
        f_min_price, f_max_price = fetch_min_max_price(code, length)
        if not min_price or f_min_price['price'] < min_price['price']:
            min_price = insert_price_record(code, length, f_min_price, 'min')
        if not max_price or f_max_price['price'] > max_price['price']:
            max_price = insert_price_record(code, length, f_max_price, 'max')

    return min_price['price'], max_price['price']


def format_price(price: float) -> float:
    return round(price / 1000, 2)


def fetch_account_id() -> int:
    url = get_url('account_list', auth=True)
    headers = get_auth_headers()
    res = requests.get(url, headers=headers, timeout=TIME_OUT)
    parsed = res.json()
    accounts = parsed.get('d')
    if not bool(accounts):
        raise ValueError("Invalid response")
    stock_account_id = None
    for account in accounts:
        product_type = account.get('producttype')
        if product_type == 'NN':
            stock_account_id = account.get('id')
    if not stock_account_id:
        raise ValueError("Invalid response")

    insert_stock_account_id_record(stock_account_id)
    return stock_account_id

def get_stock_account_id() -> int | None:
    account_id = get_stock_account_id_record()
    if not account_id:
        account_id = fetch_account_id()

    return account_id


def fetch_and_save_own_list() -> list[OwnStock]:
    url = get_url('own_list', auth=True).format(account_id=get_stock_account_id())
    headers = get_auth_headers()
    response = requests.get(url, headers=headers, timeout=TIME_OUT)
    parsed = response.json()
    data = parsed.get('d', [])
    if not bool(data):
        raise ValueError("Invalid response")
    own_list = []
    for item in data:
        code = item.get('symbol')
        total = item.get('total')
        available = item.get('trade')
        buy_price = item.get('costPrice')
        if not code or not total or not available or not buy_price:
            raise ValueError("Invalid response")
        own_stock: OwnStock = {
            'code': code,
            'total': total,
            'available': available,
            'buy_price': format_price(buy_price)
        }
        own_list.append(own_stock)

    db.table('settings').update({'name': 'own_list', 'value': own_list, 'expiry': now() + expiry_plus('end_day')})
    return own_list

def get_own_list() -> list[OwnStock]:
    own_list = db.table('settings').search(Query().name == 'own_list')
    if not own_list:
        own_list = fetch_and_save_own_list()
    else:
        own_list = own_list[0]['value']
    return own_list


if __name__ == '__main__':
    print(get_root_price('VNM'))
    pass
