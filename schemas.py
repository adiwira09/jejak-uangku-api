from pydantic import BaseModel
from typing import List

class Transaction(BaseModel):
    item: str
    amount: float

class TransactionPayload(BaseModel):
    telegram_id: str
    transactions: List[Transaction]

class User(BaseModel):
    telegram_id: str
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None

class SpreadsheetConfigRequest(BaseModel):
    telegram_id: str
    spreadsheet_id: str
    sheet_name: str

class OAuthStateRequest(BaseModel):
    telegram_id: str
    state: str