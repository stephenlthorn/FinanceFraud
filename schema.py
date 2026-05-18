import datetime
from typing import Optional
from pytidb.schema import TableModel, Field, FullTextField
from pytidb.embeddings import EmbeddingFunction

embed_fn = EmbeddingFunction("tidbcloud_free/amazon/titan-embed-text-v2")


class Member(TableModel, table=True):
    __tablename__ = "fc_members"
    __table_args__ = {"extend_existing": True}
    id: int = Field(default=None, primary_key=True)
    member_id: str = Field(index=True, max_length=32)
    name: str = Field(max_length=128)
    email: str = Field(max_length=128)
    spotme_limit: float = Field(default=50.0)
    account_status: str = Field(default="active", max_length=32)
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )


class Transaction(TableModel, table=True):
    __tablename__ = "fc_transactions"
    __table_args__ = {"extend_existing": True}
    id: int = Field(default=None, primary_key=True)
    transaction_id: str = Field(index=True, max_length=32)
    member_id: str = Field(index=True, max_length=32)
    merchant_name: str = Field(max_length=128)
    merchant_category: str = Field(max_length=64)
    amount: float
    status: str = Field(max_length=32)
    decline_reason: Optional[str] = Field(default=None, max_length=512)
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )


class PayFriendsEdge(TableModel, table=True):
    __tablename__ = "fc_pay_friends_edges"
    __table_args__ = {"extend_existing": True}
    id: int = Field(default=None, primary_key=True)
    from_member_id: str = Field(index=True, max_length=32)
    to_member_id: str = Field(index=True, max_length=32)
    amount: float
    status: str = Field(default="completed", max_length=32)
    transfer_id: str = Field(max_length=32)
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )


class FraudFlag(TableModel, table=True):
    __tablename__ = "fc_fraud_flags"
    __table_args__ = {"extend_existing": True}
    id: int = Field(default=None, primary_key=True)
    member_id: str = Field(index=True, max_length=32)
    transaction_id: str = Field(index=True, max_length=32)
    flag_type: str = Field(max_length=64)
    confidence_score: float
    description: str = Field(max_length=512)
    resolved: bool = Field(default=False)
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )


class SupportTicket(TableModel, table=True):
    __tablename__ = "fc_support_tickets"
    __table_args__ = {"extend_existing": True}
    id: int = Field(default=None, primary_key=True)
    member_id: str = Field(index=True, max_length=32)
    ticket_id: str = Field(index=True, max_length=32)
    content: str = FullTextField()
    content_vec: list[float] = embed_fn.VectorField(source_field="content")
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
