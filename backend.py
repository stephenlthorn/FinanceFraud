import os
import pymysql
from urllib.parse import urlparse, unquote


def _get_conn():
    url = os.getenv("TIDB_URL", "")
    p = urlparse(url)
    return pymysql.connect(
        host=p.hostname,
        port=p.port or 4000,
        user=unquote(p.username),
        password=unquote(p.password),
        database=(p.path or "/demo").lstrip("/"),
        ssl={"ssl_mode": "VERIFY_IDENTITY"},
        connect_timeout=10,
        cursorclass=pymysql.cursors.DictCursor,
    )


def get_member(member_id: str) -> dict | None:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM fc_members WHERE member_id = %s LIMIT 1",
                (member_id,),
            )
            return cur.fetchone()


def get_recent_transactions(member_id: str, limit: int = 10) -> list[dict]:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM fc_transactions WHERE member_id = %s "
                "ORDER BY created_at DESC LIMIT %s",
                (member_id, limit),
            )
            return cur.fetchall()


def get_fraud_flags(member_id: str) -> list[dict]:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM fc_fraud_flags WHERE member_id = %s "
                "ORDER BY created_at DESC",
                (member_id,),
            )
            return cur.fetchall()


def trace_pay_friends_network(from_member_id: str, max_depth: int = 3) -> list[dict]:
    """Recursive CTE tracing the full Pay Friends transfer chain for fraud analysis."""
    sql = """
WITH RECURSIVE pay_chain AS (
    SELECT
        e.from_member_id,
        e.to_member_id,
        e.amount,
        e.transfer_id,
        e.status,
        e.created_at,
        0 AS depth,
        CAST(e.from_member_id AS CHAR(1000)) AS transfer_path
    FROM fc_pay_friends_edges e
    WHERE e.from_member_id = %s

    UNION ALL

    SELECT
        e.from_member_id,
        e.to_member_id,
        e.amount,
        e.transfer_id,
        e.status,
        e.created_at,
        pc.depth + 1,
        CONCAT(pc.transfer_path, ' -> ', e.from_member_id)
    FROM fc_pay_friends_edges e
    JOIN pay_chain pc ON e.from_member_id = pc.to_member_id
    WHERE pc.depth < %s
)
SELECT
    pc.from_member_id,
    pc.to_member_id,
    pc.amount,
    pc.transfer_id,
    pc.status,
    pc.created_at,
    pc.depth,
    pc.transfer_path,
    mf.name AS from_name,
    mt.name AS to_name,
    ff.flag_type,
    ff.confidence_score,
    ff.description AS flag_description
FROM pay_chain pc
LEFT JOIN fc_members mf ON mf.member_id = pc.from_member_id
LEFT JOIN fc_members mt ON mt.member_id = pc.to_member_id
LEFT JOIN fc_fraud_flags ff ON ff.transaction_id = pc.transfer_id
ORDER BY pc.depth, pc.created_at
"""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (from_member_id, max_depth))
            return cur.fetchall()


def get_all_pay_friends() -> list[dict]:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT e.*, mf.name AS from_name, mt.name AS to_name,
                       ff.flag_type, ff.confidence_score
                FROM fc_pay_friends_edges e
                LEFT JOIN fc_members mf ON mf.member_id = e.from_member_id
                LEFT JOIN fc_members mt ON mt.member_id = e.to_member_id
                LEFT JOIN fc_fraud_flags ff ON ff.transaction_id = e.transfer_id
                ORDER BY e.created_at
            """)
            return cur.fetchall()


def get_db_stats() -> dict:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            stats = {}
            for table, key in [
                ("fc_members", "members"),
                ("fc_transactions", "transactions"),
                ("fc_support_tickets", "support_tickets"),
                ("fc_fraud_flags", "fraud_flags"),
                ("fc_pay_friends_edges", "pay_friends_edges"),
            ]:
                cur.execute(f"SELECT COUNT(*) AS cnt FROM {table}")
                row = cur.fetchone()
                stats[key] = row["cnt"] if row else 0

            cur.execute(
                "SELECT COUNT(*) AS cnt FROM fc_support_tickets "
                "WHERE content_vec IS NOT NULL"
            )
            row = cur.fetchone()
            stats["embeddings"] = row["cnt"] if row else 0
            return stats


def get_index_info() -> list[dict]:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SHOW INDEX FROM fc_support_tickets")
            return cur.fetchall()


def get_ddl_jobs() -> list[dict]:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("ADMIN SHOW DDL JOBS 30")
            all_jobs = cur.fetchall()
            fc_tables = {"fc_support_tickets", "fc_members", "fc_transactions",
                         "fc_pay_friends_edges", "fc_fraud_flags"}
            return [j for j in all_jobs if j.get("table_name") in fc_tables][:12]


def get_all_tickets() -> list[dict]:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ticket_id, member_id, created_at,
                       LEFT(content, 140) AS snippet,
                       VEC_DIMS(content_vec) AS vec_dims
                FROM fc_support_tickets
                ORDER BY id
            """)
            return cur.fetchall()


def get_all_fraud_flags() -> list[dict]:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT f.*, m.name AS member_name
                FROM fc_fraud_flags f
                LEFT JOIN fc_members m ON m.member_id = f.member_id
                ORDER BY f.created_at DESC
            """)
            return cur.fetchall()
