"""Seed all 5 FinanceCo tables with realistic demo data."""
import datetime
from dotenv import load_dotenv
load_dotenv()

from memory import (
    members_table, transactions_table, pay_friends_table,
    fraud_flags_table, remember_ticket,
)
from schema import Member, Transaction, PayFriendsEdge, FraudFlag


def ts(y, m, d, h=12, mi=0):
    return datetime.datetime(y, m, d, h, mi, tzinfo=datetime.timezone.utc)


# ── Members ───────────────────────────────────────────────────────────────────
MEMBERS = [
    Member(member_id="MBR-BOB-001", name="Bob Johnson",
           email="bob.johnson@email.com", spotme_limit=200.0,
           account_status="active"),
    Member(member_id="MBR-SAR-002", name="Sarah Chen",
           email="sarah.chen@email.com", spotme_limit=100.0,
           account_status="active"),
    Member(member_id="MBR-MIK-003", name="Mike Torres",
           email="mike.torres@email.com", spotme_limit=50.0,
           account_status="active"),
    Member(member_id="MBR-ALE-004", name="Alex Rivera",
           email="alex.r994@email.com", spotme_limit=0.0,
           account_status="flagged"),
    Member(member_id="MBR-JOR-005", name="Jordan Kim",
           email="jkim_2024@email.com", spotme_limit=0.0,
           account_status="frozen"),
]

# ── Transactions ──────────────────────────────────────────────────────────────
TRANSACTIONS = [
    Transaction(
        transaction_id="TXN-240115-001", member_id="MBR-BOB-001",
        merchant_name="Shell Gas Station", merchant_category="gas",
        amount=45.00, status="declined",
        decline_reason=(
            "Out-of-state transaction flag: member account registered in "
            "Chicago IL, transaction attempted in Houston TX. No travel alert on file."
        ),
        created_at=ts(2024, 1, 15, 14, 22),
    ),
    Transaction(
        transaction_id="TXN-240115-002", member_id="MBR-BOB-001",
        merchant_name="Whole Foods Market", merchant_category="grocery",
        amount=67.50, status="approved",
        created_at=ts(2024, 1, 15, 10, 15),
    ),
    Transaction(
        transaction_id="TXN-240114-001", member_id="MBR-BOB-001",
        merchant_name="Netflix", merchant_category="streaming",
        amount=15.99, status="approved",
        created_at=ts(2024, 1, 14, 8, 0),
    ),
    Transaction(
        transaction_id="TXN-240113-001", member_id="MBR-BOB-001",
        merchant_name="Starbucks", merchant_category="food",
        amount=6.45, status="approved",
        created_at=ts(2024, 1, 13, 9, 30),
    ),
    Transaction(
        transaction_id="TXN-240112-001", member_id="MBR-BOB-001",
        merchant_name="Amazon", merchant_category="retail",
        amount=89.99, status="approved",
        created_at=ts(2024, 1, 12, 16, 45),
    ),
    Transaction(
        transaction_id="TXN-240110-001", member_id="MBR-BOB-001",
        merchant_name="CVS Pharmacy", merchant_category="health",
        amount=23.14, status="approved",
        created_at=ts(2024, 1, 10, 11, 0),
    ),
    Transaction(
        transaction_id="TXN-240108-001", member_id="MBR-BOB-001",
        merchant_name="Uber", merchant_category="transportation",
        amount=18.50, status="approved",
        created_at=ts(2024, 1, 8, 19, 45),
    ),
]

# ── Pay Friends edges ─────────────────────────────────────────────────────────
# Normal transfer (Bob -> Sarah) and the suspicious chain (Bob->Mike->Alex->Jordan)
PAY_FRIENDS = [
    PayFriendsEdge(
        from_member_id="MBR-BOB-001", to_member_id="MBR-SAR-002",
        amount=35.00, status="completed", transfer_id="TRF-2024-002",
        created_at=ts(2024, 1, 8, 19, 30),
    ),
    PayFriendsEdge(
        from_member_id="MBR-BOB-001", to_member_id="MBR-MIK-003",
        amount=200.00, status="completed", transfer_id="TRF-2024-001",
        created_at=ts(2024, 1, 13, 10, 0),
    ),
    PayFriendsEdge(
        from_member_id="MBR-MIK-003", to_member_id="MBR-ALE-004",
        amount=180.00, status="flagged", transfer_id="TRF-2024-003",
        created_at=ts(2024, 1, 13, 10, 28),
    ),
    PayFriendsEdge(
        from_member_id="MBR-ALE-004", to_member_id="MBR-JOR-005",
        amount=170.00, status="flagged", transfer_id="TRF-2024-004",
        created_at=ts(2024, 1, 13, 10, 43),
    ),
]

# ── Fraud flags ───────────────────────────────────────────────────────────────
FRAUD_FLAGS = [
    FraudFlag(
        member_id="MBR-BOB-001", transaction_id="TXN-240115-001",
        flag_type="out_of_state", confidence_score=0.82,
        description=(
            "Transaction in Houston TX while member account is Chicago IL-based. "
            "Geo-velocity check failed. No travel alert was active."
        ),
        resolved=False, created_at=ts(2024, 1, 15, 14, 22),
    ),
    FraudFlag(
        member_id="MBR-MIK-003", transaction_id="TRF-2024-003",
        flag_type="high_velocity_forwarding", confidence_score=0.91,
        description=(
            "$180 forwarded to new contact within 28 minutes of receiving $200 "
            "from MBR-BOB-001. 90% pass-through rate triggers structuring alert."
        ),
        resolved=False, created_at=ts(2024, 1, 13, 10, 28),
    ),
    FraudFlag(
        member_id="MBR-ALE-004", transaction_id="TRF-2024-004",
        flag_type="money_mule_pattern", confidence_score=0.97,
        description=(
            "3-hop forwarding chain detected. Alex Rivera forwarded 94% of received "
            "funds to MBR-JOR-005 within 15 minutes. Jordan Kim has zero prior "
            "FinanceCo transaction history. Classic money mule staging pattern."
        ),
        resolved=False, created_at=ts(2024, 1, 13, 10, 43),
    ),
]

# ── Support tickets (hybrid search memory for Bob) ────────────────────────────
BOB_TICKETS = [
    ("TKT-BOB-001",
     "Gas pump declined at Shell Houston TX. Member Bob Johnson attempted to fill up "
     "at a Shell station on I-10 in Houston Texas on January 15. Transaction declined "
     "due to out-of-state flag - account registered in Chicago IL and no travel alert "
     "was set. Advised Bob to verify the charge wasn't fraudulent and to set a travel "
     "notification next time before out-of-state trips. Debit card remains active."),

    ("TKT-BOB-002",
     "SpotMe limit increase approved for Bob Johnson. Member requested an increase "
     "from $100 to $200. Direct deposit history verified showing consistent bi-weekly "
     "deposits from PayRoll Inc totaling $2,400 every two weeks. Income stability "
     "confirmed over six months. SpotMe limit upgraded to $200 effective immediately."),

    ("TKT-BOB-003",
     "Card freeze requested for international travel. Bob Johnson traveling to Mexico "
     "City January 10 through 20. Temporary international mode enabled on debit card. "
     "ATM withdrawal limit set to $500 per day for trip duration. Fraud monitoring "
     "adjusted for Mexico City merchant category codes. Card unfrozen January 21."),

    ("TKT-BOB-004",
     "Unauthorized Amazon charge investigated for Bob. Bob reported a $156.99 charge "
     "he didn't recognize on his statement. Investigation confirmed it was an Alexa "
     "voice purchase order placed through Bob's Echo Dot device by his child. "
     "Bob confirmed it was an accidental purchase. Refund processed in 3-5 business days. "
     "Bob educated on disabling voice purchasing in Alexa app settings."),

    ("TKT-BOB-005",
     "Pay Friends transfer failed to Sarah Chen. Bob attempted to send $50 to Sarah Chen "
     "MBR-SAR-002 via Pay Friends. Transfer rejected because Sarah's account was "
     "temporarily frozen for identity verification. Advised Bob that Sarah's account "
     "would be reinstated in 24 to 48 hours. Retry confirmed successful the following day."),

    ("TKT-BOB-006",
     "Multiple rapid gas station transactions triggered fraud alert for Bob. Three "
     "transactions at different gas stations within 5 minutes triggered an automated "
     "fraud alert. Bob called in and confirmed he was testing his newly activated card "
     "at a gas station with multiple separate payment terminals that each processed "
     "independently. Alert cleared manually after verification. No fraud confirmed."),

    ("TKT-BOB-007",
     "Direct deposit setup completed for Bob Johnson. New employer PayRoll Inc "
     "depositing $2,400 bi-weekly starting January 5. Routing number and account "
     "number confirmed correct. First deposit expected next Friday. SpotMe remains "
     "active and fully available during the employer transition period."),

    ("TKT-BOB-008",
     "Annual account review completed for Bob Johnson. Account in excellent standing. "
     "Zero NSF fees in past 12 months. Consistent direct deposit history from two employers. "
     "No chargebacks or disputes pending. Eligible for FinanceCo premium features "
     "including expanded $200 SpotMe and early paycheck access up to 2 days early. "
     "Upgrade offer sent via push notification and in-app message."),
]


def main():
    print("Seeding FinanceCo demo data...")
    print()

    # Members
    existing_members = {r["member_id"] for r in members_table.query().to_list()}
    inserted = 0
    for m in MEMBERS:
        if m.member_id not in existing_members:
            members_table.insert(m)
            print(f"  + Member: {m.name} ({m.member_id})")
            inserted += 1
    print(f"  Members: {inserted} inserted, {len(MEMBERS)-inserted} skipped\n")

    # Transactions
    existing_txns = {r["transaction_id"] for r in transactions_table.query().to_list()}
    inserted = 0
    for t in TRANSACTIONS:
        if t.transaction_id not in existing_txns:
            transactions_table.insert(t)
            print(f"  + Transaction: {t.transaction_id} ({t.merchant_name}, ${t.amount:.2f}, {t.status})")
            inserted += 1
    print(f"  Transactions: {inserted} inserted, {len(TRANSACTIONS)-inserted} skipped\n")

    # Pay Friends
    existing_edges = {r["transfer_id"] for r in pay_friends_table.query().to_list()}
    inserted = 0
    for e in PAY_FRIENDS:
        if e.transfer_id not in existing_edges:
            pay_friends_table.insert(e)
            print(f"  + Transfer: {e.transfer_id} (${e.amount:.2f}, {e.status})")
            inserted += 1
    print(f"  Pay Friends: {inserted} inserted, {len(PAY_FRIENDS)-inserted} skipped\n")

    # Fraud flags
    existing_flags = {r["transaction_id"] for r in fraud_flags_table.query().to_list()}
    inserted = 0
    for f in FRAUD_FLAGS:
        if f.transaction_id not in existing_flags:
            fraud_flags_table.insert(f)
            print(f"  + Fraud flag: {f.flag_type} (confidence: {f.confidence_score:.2f})")
            inserted += 1
    print(f"  Fraud flags: {inserted} inserted, {len(FRAUD_FLAGS)-inserted} skipped\n")

    # Support tickets (with vector embeddings)
    from memory import support_tickets_table
    existing_tickets = {r["ticket_id"] for r in support_tickets_table.query().to_list()}
    inserted = 0
    for tid, content in BOB_TICKETS:
        if tid not in existing_tickets:
            remember_ticket("MBR-BOB-001", tid, content)
            print(f"  + Ticket: {tid} (embedding generated)")
            inserted += 1
    print(f"  Support tickets: {inserted} inserted, {len(BOB_TICKETS)-inserted} skipped\n")

    print("Seeding complete!")


if __name__ == "__main__":
    main()
