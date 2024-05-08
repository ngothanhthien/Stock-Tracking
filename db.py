from typing import Optional

from tinydb import TinyDB, Query

from type import PriceReturn, PriceRecord, PriceType, PriceLength
from utils import now

db = TinyDB('db.json')


def table_exists(table_name: str) -> bool:
    return len(db.table(table_name).all()) > 0


def init_db() -> None:
    if not table_exists('auth'):
        db.table('auth').insert({'token': None, 'expiry': 0})
    if not table_exists('settings'):
        db.table('settings').insert({'name': 'watch_list', 'value': []})
    if not table_exists('prices'):
        db.table('prices').insert({'code': None, 'price': 0, 'type': 'current', 'expiry': 0, 'length': None})


def insert_price_record(code: str, length: Optional[PriceLength], price_info: PriceReturn, price_type: PriceType) -> PriceRecord:
    price_record: PriceRecord = {
        'code': code,
        'price': price_info['price'],
        'type': price_type,
        'expiry': price_info['expiry'],
    }
    query = {'code': code, 'type': price_type}

    if length:
        price_record['length'] = length
        query['length'] = length

    query = Query().fragment(query)
    db.table('prices').update(price_record, query)

    return price_record

def get_price_record(code: str, price_type: PriceType, length: Optional[PriceLength]) -> PriceRecord | None:
    query = {'code': code, 'type': price_type}
    if length:
        query['length'] = length
    query = Query().fragment(query)
    record = db.table('prices').search(query)
    if not record:
        return None
    if record_expired(record[0]):
        return None
    return record[0]


def record_expired(record: dict | None) -> bool:
    if not record:
        return True
    expiry = record.get('expiry')
    if not expiry:
        return False
    return expiry < now()


def get_stock_account_id_record() -> int | None:
    account_id = db.table('settings').search(Query().name == 'account_id')
    if account_id:
        account_id = account_id[0]['value']
    return account_id


def insert_stock_account_id_record(account_id: int) -> None:
    db.table('settings').update({'name': 'account_id', 'value': account_id}, Query().name == 'account_id')
