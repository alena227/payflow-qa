"""Pydantic-модели запросов/ответов. Decimal в JSON-ответах отдается строкой ("100.00"),
чтобы клиент не терял точность на float."""
import datetime as dt
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

Amount = Field(gt=0, le=1_000_000, max_digits=9, decimal_places=2)


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str


class AccountOut(BaseModel):
    id: int
    currency: str
    balance: Decimal


class TopupIn(BaseModel):
    amount: Decimal = Amount


class TransferIn(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: Decimal = Amount


class TransactionOut(BaseModel):
    id: UUID
    type: str
    from_account_id: int | None
    to_account_id: int
    amount: Decimal
    currency: str
    fee: Decimal
    rate: Decimal | None
    amount_to: Decimal
    currency_to: str
    status: str
    created_at: dt.datetime


class HistoryItemOut(TransactionOut):
    direction: Literal["in", "out", "self"]
