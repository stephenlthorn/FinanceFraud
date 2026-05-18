# FinanceCo AI Demo

A TiDB Cloud demo showing how a fintech AI support agent uses persistent memory and graph-based fraud detection.

## What it demonstrates

- **Hybrid Search** (BM25 + vector): Surfaces relevant past support tickets using both keyword and semantic similarity - personalized responses vs. generic ones
- **Recursive CTE Graph Traversal**: Traces multi-hop Pay Friends transfer chains to detect money mule patterns - no graph database needed
- **Relational + AI in one DB**: Members, transactions, fraud flags, graph edges, and vector embeddings in a single TiDB Cloud cluster

## Setup

```bash
pip install -r requirements.txt
# Add your TIDB_URL to .env
python seed.py       # Seed all 5 tables + generate embeddings
streamlit run app.py
```

## Architecture

| Table | Purpose |
|-------|---------|
| `fc_members` | Member profiles (name, SpotMe limit, status) |
| `fc_transactions` | Transaction history with decline reasons |
| `fc_pay_friends_edges` | Graph edges for Pay Friends transfers |
| `fc_fraud_flags` | Fraud detection flags with confidence scores |
| `fc_support_tickets` | Hybrid-searchable support history (BM25 + vector) |

## Demo scenarios

1. **Gas pump declined** - Bob asks why his Shell transaction failed. Hybrid search retrieves the exact out-of-state incident record.
2. **Suspicious Pay Friends** - Bob's $200 transfer triggered a 3-hop forwarding chain. Recursive CTE walks Bob -> Mike -> Alex -> Jordan and surfaces fraud flags at each hop.
3. **Fraud notification** - Bob got an alert. Relational lookup + hybrid search surfaces both active flags with full context.
