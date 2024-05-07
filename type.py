from typing import TypedDict, Literal, Optional


class AuthToken(TypedDict):
    token: str
    expiry: int


PriceType = Literal['min', 'max', 'current', 'last', 'root', 'sub root']
PriceLength = Literal['3M', '1Y']


class PriceRecord(TypedDict):
    code: str
    price: float
    type: PriceType
    expiry: int | None
    length: Optional[PriceLength]


class PriceReturn(TypedDict):
    expiry: int | None
    price: float
