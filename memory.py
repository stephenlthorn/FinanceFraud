import os
import sys
from urllib.parse import urlparse, unquote
from sqlalchemy import event
from pytidb import TiDBClient
from schema import Member, Transaction, PayFriendsEdge, FraudFlag, SupportTicket

# ── SQL capture ───────────────────────────────────────────────────────────────
_sql_log: list[dict] = []


def get_last_sql(n: int = 6) -> list[dict]:
    return _sql_log[-n:]


def clear_sql_log() -> None:
    _sql_log.clear()


def _connect():
    url = os.getenv("TIDB_URL")
    if not url:
        sys.exit("error: TIDB_URL not set. Check your .env file.")
    p = urlparse(url)
    if not all([p.hostname, p.username, p.password]):
        sys.exit("error: TIDB_URL must be mysql://user:pass@host:port/db form.")
    return TiDBClient.connect(
        host=p.hostname,
        port=p.port or 4000,
        username=unquote(p.username),
        password=unquote(p.password),
        database=(p.path or "/test").lstrip("/"),
        ensure_db=True,
    )


_db = _connect()


@event.listens_for(_db.db_engine, "after_cursor_execute")
def _capture_sql(conn, cursor, statement, parameters, context, executemany):
    stmt = statement.strip()
    if stmt.upper().startswith(("INSERT", "SELECT")):
        _sql_log.append({"sql": stmt, "params": parameters})


# Create all tables
members_table = _db.create_table(schema=Member, if_exists="skip")
transactions_table = _db.create_table(schema=Transaction, if_exists="skip")
pay_friends_table = _db.create_table(schema=PayFriendsEdge, if_exists="skip")
fraud_flags_table = _db.create_table(schema=FraudFlag, if_exists="skip")
support_tickets_table = _db.create_table(schema=SupportTicket, if_exists="skip")


def remember_ticket(member_id: str, ticket_id: str, content: str) -> None:
    support_tickets_table.insert(
        SupportTicket(member_id=member_id, ticket_id=ticket_id, content=content)
    )


def recall_support(member_id: str, query: str, limit: int = 5) -> list[dict]:
    clear_sql_log()
    results = (
        support_tickets_table.search(query, search_type="hybrid")
        .filter({"member_id": member_id})
        .limit(limit)
        .to_list()
    )
    return results
