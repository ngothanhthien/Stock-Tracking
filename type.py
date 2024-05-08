from typing import TypedDict, Literal, Optional


class AuthToken(TypedDict):
    token: str
    expiry: int


PriceType = Literal['min', 'max', 'current', 'last', 'root', 'sub root']
PriceLength = Literal['3M', '1Y', '3Y', '1M']


class PriceRecord(TypedDict):
    code: str
    price: float
    type: PriceType
    expiry: int | None
    length: Optional[PriceLength]


class OwnStock(TypedDict):
    code: str
    total: int
    available: float
    buy_price: float


class PriceReturn(TypedDict):
    expiry: int | None
    price: float
