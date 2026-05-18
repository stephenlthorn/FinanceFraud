"""FinanceCo AI Demo - TiDB Cloud memory + fraud graph showcase."""
import re
import os
from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import plotly.graph_objects as go

from memory import recall_support, get_last_sql
from backend import (
    trace_pay_friends_network, get_member, get_fraud_flags,
    get_recent_transactions, get_db_stats, get_index_info,
    get_all_pay_friends, get_all_tickets, get_all_fraud_flags,
)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FinanceCo AI Demo",
    page_icon="💚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Backend shim (direct imports, no lazy loading needed) ────────────────────
def _load_backends():
    return {
        "recall_support": recall_support,
        "get_last_sql": get_last_sql,
        "trace_pay_friends_network": trace_pay_friends_network,
        "get_member": get_member,
        "get_fraud_flags": get_fraud_flags,
        "get_recent_transactions": get_recent_transactions,
        "get_db_stats": get_db_stats,
        "get_index_info": get_index_info,
        "get_all_pay_friends": get_all_pay_friends,
        "get_all_tickets": get_all_tickets,
        "get_all_fraud_flags": get_all_fraud_flags,
    }


be = _load_backends()

# ── Session state ──────────────────────────────────────────────────────────────
if "active_q" not in st.session_state:
    st.session_state.active_q = None
if "q_results" not in st.session_state:
    st.session_state.q_results = {}

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
html,body,[class*="css"]{font-family:-apple-system,system-ui,BlinkMacSystemFont,sans-serif}
.block-container{padding:1.25rem 1.75rem 1rem;max-width:100%}
div[data-testid="stTabs"] button[data-baseweb="tab"]{
  font-size:14px;font-weight:600;padding:.45rem 1.25rem}

/* stat cards */
.stat-card{border-radius:10px;padding:1rem 1.25rem;text-align:center;border:1px solid}
.stat-num{font-size:2rem;font-weight:800;line-height:1.1}
.stat-lbl{font-size:11px;text-transform:uppercase;letter-spacing:.08em;margin-top:.25rem}

/* phone frame chat */
.chat-msg-user{text-align:right;margin-bottom:10px}
.chat-msg-ai{text-align:left;margin-top:6px}

/* SQL panel */
.sql-panel{background:#0F172A;border-radius:10px;padding:1.25rem 1.5rem;
           color:#E2E8F0;font-family:ui-monospace,monospace;font-size:12.5px;line-height:1.7}
.sql-section-label{font-family:-apple-system,system-ui,sans-serif;font-size:11px;
  font-weight:700;text-transform:uppercase;letter-spacing:.1em;display:inline-block;
  padding:3px 8px;border-radius:4px;margin:.9rem 0 .4rem}
.lbl-fts{background:#4C1D95;color:#DDD6FE}
.lbl-vec{background:#0C4A6E;color:#BAE6FD}
.lbl-rrf{background:#064E3B;color:#A7F3D0}
.lbl-cte{background:#78350F;color:#FDE68A}
.lbl-res{background:#1E1B4B;color:#C7D2FE}
.sql-block{background:#1E293B;border-radius:6px;padding:.7rem 1rem;
           margin:.35rem 0 .75rem;white-space:pre;overflow-x:auto}
.kw{color:#93C5FD}.fn{color:#6EE7B7}.str{color:#FCD34D}.dim{color:#475569}
.cte-kw{color:#FDE68A}
.result-row{background:#1E293B;border-radius:6px;padding:.45rem .8rem;margin-bottom:.4rem}
.res-tid{color:#60A5FA;font-weight:700;font-size:12px}
.res-score{float:right;color:#94A3B8;font-size:11px;font-variant-numeric:tabular-nums}
.res-snip{color:#CBD5E1;font-size:11.5px;margin-top:.2rem;line-height:1.5;
          font-family:-apple-system,system-ui,sans-serif}
.rrf-formula{color:#0F172A;background:#A7F3D0;padding:3px 10px;
             border-radius:4px;font-weight:700;font-size:13px}
</style>
""", unsafe_allow_html=True)

# ── Pre-written demo responses ─────────────────────────────────────────────────
QUESTIONS = {
    1: "Why was my gas pump declined?",
    2: "Did my Pay Friends transfer go through? It looks suspicious.",
    3: "I got a fraud notification. What happened?",
}

WITHOUT_MEM = {
    1: (
        "Gas pump declines can happen for several reasons:<br><br>"
        "&bull; Insufficient funds or daily limit reached<br>"
        "&bull; Card restriction on fuel merchants<br>"
        "&bull; Network connectivity issue at terminal<br>"
        "&bull; Security hold on new card<br><br>"
        "Please check your balance and try again. For further help, "
        "call us at <b>1-800-FINANCE</b>."
    ),
    2: (
        "Pay Friends transfers typically complete in 1-3 minutes.<br><br>"
        "To check status: <b>Home &rarr; Pay Friends &rarr; History</b><br><br>"
        "If a transfer is still pending after 24 hours, please contact "
        "support and have your transfer confirmation number ready."
    ),
    3: (
        "Fraud notifications are sent when we detect unusual activity "
        "on your account.<br><br>"
        "To review alerts:<br>"
        "<b>Settings &rarr; Security &rarr; Recent Alerts</b><br><br>"
        "If you see a charge you don&#39;t recognize, tap <b>Dispute</b> "
        "immediately and we&#39;ll investigate within 24 hours."
    ),
}

WITH_MEM = {
    1: (
        "Hi Bob! Found it. &#x1F50D;<br><br>"
        "Your <b>Shell Gas Station</b> charge on <b>Jan&nbsp;15 at 2:22&nbsp;PM</b> "
        "($45.00) was blocked by our fraud detection.<br><br>"
        "<b>Reason:</b> Your account is registered in <b>Chicago,&nbsp;IL</b> but "
        "the pump was in <b>Houston,&nbsp;TX</b> - with no travel alert on file.<br><br>"
        "Was this you? I can approve this location so you can retry right now."
    ),
    2: (
        "Hi Bob! Your $200 transfer to <b>Mike Torres</b> on Jan&nbsp;13 "
        "completed. &#x2705;<br><br>"
        "But I need to flag something:<br>"
        "<b>&#x26A0;&#xFE0F; Suspicious chain detected:</b><br>"
        "Bob &#x2192; Mike ($200) &#x2192; Alex Rivera ($180, +28&nbsp;min) "
        "&#x2192; Jordan Kim ($170, +15&nbsp;min)<br><br>"
        "Jordan Kim has <b>zero prior</b> FinanceCo history. Fraud model scores "
        "this chain at <b>97% confidence</b>. Want to dispute?"
    ),
    3: (
        "Hi Bob! You have <b>2 active items</b> flagged:<br><br>"
        "<b>1. &#x1F534; Gas Decline (Jan&nbsp;15)</b><br>"
        "Shell Houston TX blocked - Chicago account, no travel alert. Score: 82%<br><br>"
        "<b>2. &#x1F534; Pay Friends Chain (Jan&nbsp;13)</b><br>"
        "Your $200 to Mike triggered a 3-hop forwarding chain ending at Jordan Kim "
        "(new account). Score: 97%<br><br>"
        "Both pending your review. Want me to walk through each one?"
    ),
}

MEM_SNIPPETS = {
    1: ["TKT-BOB-001 - Gas pump declined Houston TX (score 0.94)",
        "TKT-BOB-006 - Rapid gas station fraud alert (score 0.67)"],
    2: ["TKT-BOB-005 - Pay Friends transfer failed (score 0.81)",
        "TKT-BOB-001 - Out-of-state decline context (score 0.58)"],
    3: ["TKT-BOB-006 - Multiple rapid gas fraud alert (score 0.88)",
        "TKT-BOB-001 - Out-of-state card decline (score 0.72)"],
}


# ── Helpers ────────────────────────────────────────────────────────────────────
STOP_WORDS = {
    "a","an","the","is","it","in","on","at","to","for","of","and","or","but",
    "why","how","what","when","where","who","my","your","i","did","was","were",
    "got","looks","looks","through","go","get","this","that","have",
}

def _tokenize(query: str) -> str:
    words = re.findall(r"[a-zA-Z0-9]+", query)
    parts, signals = [], []
    for w in words:
        if w.lower() in STOP_WORDS:
            parts.append(f'<span style="color:#475569;text-decoration:line-through;'
                         f'font-size:13px" title="Low IDF - near-zero BM25 weight">{w}</span>')
        else:
            parts.append(f'<span style="background:#7C3AED;color:#fff;padding:1px 6px;'
                         f'border-radius:4px;font-size:13px;font-weight:600;margin:0 2px">{w}</span>')
            signals.append(w)
    note = (
        '<div style="font-size:11.5px;color:#64748B;font-family:-apple-system,system-ui,sans-serif;'
        'margin-top:.25rem">All words indexed. Common words (crossed) have near-zero BM25 weight. '
        f'High-signal terms: {", ".join(f"<b>{k}</b>" for k in signals)}</div>'
    )
    return f'<div style="margin:.4rem 0 .7rem">{" ".join(parts)}</div>{note}'


def _highlight_sql(sql: str) -> str:
    sql = re.sub(r'\b(SELECT|FROM|WHERE|ORDER\s+BY|LIMIT|AND|OR|AS|ASC|DESC|'
                 r'INSERT|INTO|VALUES|NOT|JOIN|LEFT|ON|UNION|ALL|CONCAT|CAST)\b',
                 r'<span class="kw">\1</span>', sql)
    sql = re.sub(r'\b(WITH\s+RECURSIVE|WITH|RECURSIVE)\b',
                 r'<span class="cte-kw">\1</span>', sql)
    sql = re.sub(r'\b(FTS_MATCH_WORD|VEC_EMBED_COSINE_DISTANCE|VEC_COSINE_DISTANCE|'
                 r'VEC_DIMS|EMBED_TEXT|MATCH|AGAINST)\b',
                 r'<span class="fn">\1</span>', sql)
    sql = re.sub(r"'([^']*)'", r'<span class="str">\'\1\'</span>', sql)
    sql = re.sub(r'(candidates\.|_inner_hit\.|_hit\.)', r'<span class="dim">\1</span>', sql)
    return sql


def _phone_frame(label: str, q_text: str, response_html: str,
                 mem_snippets: list | None = None,
                 header_color: str = "#00C49A") -> str:
    mem_block = ""
    if mem_snippets:
        items = "".join(
            f'<div style="margin:2px 0;font-size:11px;color:#005F47">&#128206; {s}</div>'
            for s in mem_snippets
        )
        mem_block = (
            '<div style="background:#E6FAF5;border-left:3px solid #00C49A;'
            'padding:7px 10px;border-radius:4px;margin:8px 0">'
            '<div style="font-size:10px;font-weight:700;color:#007A57;'
            'text-transform:uppercase;letter-spacing:.5px;margin-bottom:3px">'
            'Memory Retrieved</div>'
            f'{items}</div>'
        )
    return f"""
<div style="border:6px solid #1B2B4A;border-radius:36px;background:#0A0E1A;
            padding:16px 14px 20px;max-width:310px;margin:0 auto;min-height:590px">
  <div style="text-align:center;margin-bottom:10px">
    <div style="background:#2D3D5A;width:70px;height:16px;border-radius:8px;
                display:inline-block"></div>
  </div>
  <div style="background:{header_color};padding:10px 14px;border-radius:14px 14px 0 0;
              text-align:center">
    <span style="color:white;font-weight:700;font-size:15px">&#128154; FinanceCo</span>
    <div style="color:rgba(255,255,255,.8);font-size:10px;margin-top:1px">{label}</div>
  </div>
  <div style="background:#F5F7FA;padding:14px 12px;border-radius:0 0 14px 14px;min-height:500px">
    <div style="text-align:right;margin-bottom:10px">
      <div style="display:inline-block;background:#00C49A;color:white;
                  padding:8px 12px;border-radius:16px 16px 4px 16px;
                  max-width:83%;font-size:12px;text-align:left;line-height:1.5">
        {q_text}
      </div>
    </div>
    {mem_block}
    <div style="text-align:left;margin-top:8px">
      <div style="display:inline-block;background:white;color:#1a2035;
                  padding:10px 13px;border-radius:4px 16px 16px 16px;
                  max-width:90%;font-size:12px;border:1px solid #E2E8F0;
                  line-height:1.6">
        {response_html}
      </div>
    </div>
  </div>
</div>
"""


@st.cache_data(ttl=300)
def _build_network_graph() -> go.Figure:
    """Plotly network graph of the Pay Friends transfer chain."""
    # Node positions
    nodes = {
        "MBR-BOB-001": (0.0, 0.0, "Bob Johnson", "#00C49A", 22),
        "MBR-SAR-002": (-0.8, 0.9, "Sarah Chen", "#00C49A", 18),
        "MBR-MIK-003": (1.0, 0.0, "Mike Torres", "#F59E0B", 18),
        "MBR-ALE-004": (2.0, 0.0, "Alex Rivera", "#EF4444", 18),
        "MBR-JOR-005": (3.0, 0.0, "Jordan Kim", "#DC2626", 18),
    }
    edges = [
        ("MBR-BOB-001", "MBR-SAR-002", "$35", "#94A3B8", "normal"),
        ("MBR-BOB-001", "MBR-MIK-003", "$200", "#3B82F6", "trigger"),
        ("MBR-MIK-003", "MBR-ALE-004", "$180 +28min", "#F59E0B", "flagged"),
        ("MBR-ALE-004", "MBR-JOR-005", "$170 +15min", "#EF4444", "flagged"),
    ]

    fig = go.Figure()

    # Edge traces
    for src, dst, label, color, etype in edges:
        x0, y0 = nodes[src][0], nodes[src][1]
        x1, y1 = nodes[dst][0], nodes[dst][1]
        dash = "dot" if etype == "normal" else "solid"
        width = 2 if etype == "normal" else 3
        fig.add_trace(go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None],
            mode="lines",
            line=dict(color=color, width=width, dash=dash),
            hoverinfo="skip",
            showlegend=False,
        ))
        # Edge label at midpoint
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2 + 0.1
        fig.add_annotation(
            x=mx, y=my, text=f"<b>{label}</b>",
            showarrow=False, font=dict(size=11, color=color),
            bgcolor="rgba(255,255,255,0.85)", borderpad=3,
        )

    # Node traces
    for mid, (x, y, name, color, size) in nodes.items():
        status_map = {
            "MBR-BOB-001": "active", "MBR-SAR-002": "active",
            "MBR-MIK-003": "active", "MBR-ALE-004": "FLAGGED",
            "MBR-JOR-005": "FROZEN",
        }
        hover = f"<b>{name}</b><br>{mid}<br>Status: {status_map[mid]}"
        fig.add_trace(go.Scatter(
            x=[x], y=[y],
            mode="markers+text",
            marker=dict(size=size, color=color, line=dict(color="white", width=2)),
            text=[name],
            textposition="top center",
            textfont=dict(size=11, color="#0F172A"),
            hovertext=[hover],
            hoverinfo="text",
            showlegend=False,
        ))

    fig.update_layout(
        title=dict(
            text="Pay Friends Network - Fraud Chain Detection",
            font=dict(size=14, color="#0F172A"), x=0.5,
        ),
        xaxis=dict(visible=False, range=[-1.3, 3.6]),
        yaxis=dict(visible=False, range=[-0.6, 1.4]),
        plot_bgcolor="#F8FAFC",
        paper_bgcolor="#F8FAFC",
        margin=dict(l=20, r=20, t=50, b=20),
        height=320,
        annotations=[
            dict(x=3.0, y=-0.4, text="&#128274; Frozen account<br>Zero prior history",
                 showarrow=True, arrowhead=2, ax=0, ay=-30,
                 font=dict(size=10, color="#DC2626"),
                 bgcolor="rgba(254,226,226,0.9)", borderpad=4,
                 bordercolor="#EF4444"),
            dict(x=2.1, y=-0.38, text="&#128681; 97% fraud confidence",
                 showarrow=True, arrowhead=2, ax=10, ay=-25,
                 font=dict(size=10, color="#EF4444"),
                 bgcolor="rgba(254,226,226,0.9)", borderpad=4,
                 bordercolor="#F59E0B"),
        ],
    )
    return fig


def _sql_q1(query: str, results: list) -> str:
    fts_sql = (
        "SELECT id, ticket_id, member_id,\n"
        "       content,\n"
        "       FTS_MATCH_WORD(content,\n"
        f"           '{query}') AS bm25_score\n"
        "FROM   fc_support_tickets\n"
        "WHERE  member_id = 'MBR-BOB-001'\n"
        "  AND  FTS_MATCH_WORD(content, '{query}')\n"
        "ORDER  BY bm25_score DESC LIMIT 10"
    )
    vec_sql = (
        "SELECT id, ticket_id, member_id, content,\n"
        "       VEC_COSINE_DISTANCE(\n"
        "           content_vec,\n"
        f"           EMBED_TEXT('{query}')\n"
        "       ) AS vec_distance\n"
        "FROM   fc_support_tickets\n"
        "WHERE  member_id = 'MBR-BOB-001'\n"
        "ORDER  BY vec_distance ASC LIMIT 10"
    )
    rows = "".join(
        f'<div class="result-row">'
        f'<span class="res-tid">{r.get("ticket_id","?")}</span>'
        f'<span class="res-score">RRF {float(r.get("_score") or r.get("_distance") or 0):.4f}</span>'
        f'<div class="res-snip">{str(r.get("content",""))[:130]}...</div></div>'
        for r in (results or [])[:4]
    )
    return f"""
<span class="sql-section-label lbl-fts">&#x2460; Full-Text Search - BM25</span>
<div style="font-family:-apple-system,system-ui,sans-serif;font-size:12.5px;color:#94A3B8;margin:.3rem 0 .4rem">
Not a phrase match. Every word indexed. BM25 scores by rarity - domain terms like <b style="color:#DDD6FE">gas</b>,
<b style="color:#DDD6FE">pump</b>, <b style="color:#DDD6FE">declined</b> score high because they appear in few tickets.
</div>
{_tokenize(query)}
<div class="sql-block">{_highlight_sql(fts_sql)}</div>

<span class="sql-section-label lbl-vec">&#x2461; Vector Search - cosine similarity</span>
<div style="font-family:-apple-system,system-ui,sans-serif;font-size:12.5px;color:#94A3B8;margin:.3rem 0 .4rem">
Raw text goes straight into SQL. <b style="color:#BAE6FD">TiDB calls Amazon Titan server-side</b> -
no embedding client in your application code.
</div>
<div class="sql-block">{_highlight_sql(vec_sql)}</div>

<span class="sql-section-label lbl-rrf">&#x2462; Reciprocal Rank Fusion</span>
<div style="font-family:-apple-system,system-ui,sans-serif;font-size:12.5px;color:#94A3B8;margin:.3rem 0 .6rem">
<span class="rrf-formula">score = 1/(k+rank_fts) + 1/(k+rank_vec)</span>
&nbsp;- strong in both modalities rises to #1. k=60 is standard.
</div>

<span class="sql-section-label lbl-res">Matched tickets</span>
{rows if rows else '<div style="font-family:-apple-system,system-ui,sans-serif;color:#475569;font-size:13px;margin:.5rem 0">Click a question to see live results.</div>'}
"""


def _sql_q2() -> str:
    cte_sql = """WITH RECURSIVE pay_chain AS (
  -- Base: Bob's direct transfers
  SELECT from_member_id, to_member_id,
         amount, transfer_id, created_at,
         0 AS depth,
         CAST(from_member_id AS CHAR(1000)) AS path
  FROM   fc_pay_friends_edges
  WHERE  from_member_id = 'MBR-BOB-001'

  UNION ALL

  -- Recursive: follow the money
  SELECT e.from_member_id, e.to_member_id,
         e.amount, e.transfer_id, e.created_at,
         pc.depth + 1,
         CONCAT(pc.path, ' -> ', e.from_member_id)
  FROM   fc_pay_friends_edges e
  JOIN   pay_chain pc ON e.from_member_id = pc.to_member_id
  WHERE  pc.depth < 3
)
SELECT pc.*, mf.name AS from_name, mt.name AS to_name,
       ff.flag_type, ff.confidence_score, ff.description
FROM   pay_chain pc
LEFT JOIN fc_members mf ON mf.member_id = pc.from_member_id
LEFT JOIN fc_members mt ON mt.member_id = pc.to_member_id
LEFT JOIN fc_fraud_flags ff ON ff.transaction_id = pc.transfer_id
ORDER  BY pc.depth, pc.created_at"""

    recall_sql = (
        "SELECT ticket_id, content,\n"
        "       FTS_MATCH_WORD(content, 'Pay Friends suspicious transfer') AS bm25,\n"
        "       VEC_COSINE_DISTANCE(content_vec,\n"
        "           EMBED_TEXT('Pay Friends suspicious transfer')) AS vec\n"
        "FROM   fc_support_tickets\n"
        "WHERE  member_id = 'MBR-BOB-001'\n"
        "ORDER  BY (RRF rank fusion) LIMIT 3"
    )
    return f"""
<span class="sql-section-label lbl-cte">&#x2460; Recursive CTE - Graph traversal</span>
<div style="font-family:-apple-system,system-ui,sans-serif;font-size:12.5px;color:#94A3B8;margin:.3rem 0 .4rem">
Standard SQL <b style="color:#FDE68A">WITH RECURSIVE</b> walks the Pay Friends graph up to 3 hops.
No graph database needed - TiDB resolves the full chain in a single query.
</div>
<div class="sql-block">{_highlight_sql(cte_sql)}</div>

<span class="sql-section-label lbl-fts">&#x2461; Hybrid Search - past incident context</span>
<div style="font-family:-apple-system,system-ui,sans-serif;font-size:12.5px;color:#94A3B8;margin:.3rem 0 .4rem">
Parallel BM25 + vector search retrieves past Pay Friends support tickets for Bob,
providing the AI with member history to contextualize the fraud chain.
</div>
<div class="sql-block">{_highlight_sql(recall_sql)}</div>

<span class="sql-section-label lbl-rrf">&#x2462; Combined result</span>
<div style="font-family:-apple-system,system-ui,sans-serif;font-size:12.5px;color:#94A3B8;margin:.3rem 0 .6rem">
Graph data (depth, hop amounts, flag scores) + recalled ticket context are merged
and passed to the AI model. <b style="color:#A7F3D0">Deterministic graph + semantic memory = precise fraud narrative.</b>
</div>
"""


def _sql_q3() -> str:
    lookup_sql = (
        "SELECT m.name, m.account_status, m.spotme_limit,\n"
        "       f.flag_type, f.confidence_score,\n"
        "       f.description, f.resolved\n"
        "FROM   fc_members m\n"
        "LEFT JOIN fc_fraud_flags f ON f.member_id = m.member_id\n"
        "WHERE  m.member_id = 'MBR-BOB-001'\n"
        "ORDER  BY f.created_at DESC"
    )
    recall_sql = (
        "SELECT ticket_id, content,\n"
        "       FTS_MATCH_WORD(content, 'fraud alert unusual activity') AS bm25,\n"
        "       VEC_COSINE_DISTANCE(content_vec,\n"
        "           EMBED_TEXT('fraud alert unusual activity')) AS vec\n"
        "FROM   fc_support_tickets\n"
        "WHERE  member_id = 'MBR-BOB-001'\n"
        "ORDER  BY (RRF rank fusion) LIMIT 3"
    )
    return f"""
<span class="sql-section-label lbl-res">&#x2460; Member + Fraud Flags lookup</span>
<div style="font-family:-apple-system,system-ui,sans-serif;font-size:12.5px;color:#94A3B8;margin:.3rem 0 .4rem">
Direct relational join surfaces all active fraud flags for the authenticated member.
Returns account status, SpotMe limit, and each unresolved flag with confidence score.
</div>
<div class="sql-block">{_highlight_sql(lookup_sql)}</div>

<span class="sql-section-label lbl-fts">&#x2461; Hybrid Search - incident history</span>
<div style="font-family:-apple-system,system-ui,sans-serif;font-size:12.5px;color:#94A3B8;margin:.3rem 0 .4rem">
Semantic + keyword search retrieves Bob's prior fraud-related support interactions,
giving the AI context on what was already communicated and resolved.
</div>
<div class="sql-block">{_highlight_sql(recall_sql)}</div>

<span class="sql-section-label lbl-rrf">&#x2462; Response assembly</span>
<div style="font-family:-apple-system,system-ui,sans-serif;font-size:12.5px;color:#94A3B8;margin:.3rem 0 .6rem">
Structured fraud flag data + recalled support history are combined.
<span class="rrf-formula">Relational precision + semantic context = zero repeat explanations.</span>
</div>
"""


@st.cache_data(ttl=60)
def _get_stats():
    return get_db_stats()


@st.cache_data(ttl=60)
def _get_pay_friends():
    return get_all_pay_friends()


@st.cache_data(ttl=60)
def _get_tickets():
    return get_all_tickets()


@st.cache_data(ttl=60)
def _get_fraud():
    return get_all_fraud_flags()


@st.cache_data(ttl=60)
def _get_transactions():
    return get_recent_transactions("MBR-BOB-001", limit=10)


@st.cache_data(ttl=300)
def _get_indexes():
    return get_index_info()


# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="padding:1.25rem 0 .25rem">
  <span style="font-size:22px;font-weight:800;color:#00C49A">FinanceCo</span>
  <span style="font-size:16px;color:#64748B;margin-left:.6rem">AI Member Support Demo</span>
  <span style="font-size:12px;color:#94A3B8;margin-left:1rem">
    Powered by TiDB Cloud &nbsp;&#8226;&nbsp; Hybrid Search + Graph Traversal
  </span>
</div>
""", unsafe_allow_html=True)

tab_setup, tab_app, tab_dash, tab_sql = st.tabs([
    "  &#x2699;&#xFE0F; The Setup  ",
    "  &#x1F4F1; FinanceCo App  ",
    "  &#x1F4CA; Memory Dashboard  ",
    "  &#x1F50D; Backend SQL  ",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 - THE SETUP
# ══════════════════════════════════════════════════════════════════════════════
with tab_setup:
    # Hero header
    st.markdown("""
    <div style="background:linear-gradient(135deg,#022C22 0%,#064E3B 100%);
                border-radius:14px;padding:2.5rem 3rem;margin-bottom:1.5rem;color:#F0FDF4">
      <div style="font-size:11px;font-weight:700;letter-spacing:.15em;text-transform:uppercase;
                  color:#34D399;margin-bottom:.5rem">Demo Scenario</div>
      <div style="font-size:2rem;font-weight:800;line-height:1.2;color:#ECFDF5;margin-bottom:.75rem">
        AI Support Agent with Long-Term Member Memory
      </div>
      <div style="font-size:1rem;color:#A7F3D0;line-height:1.75;max-width:700px">
        FinanceCo's AI agent handles 60% of member calls autonomously.
        Without memory, every interaction starts cold - no context, no personalization, no pattern detection.
        With TiDB Cloud, the agent knows Bob's history, flags fraud chains, and resolves issues in seconds.
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_r = st.columns(2, gap="medium")
    with col_l:
        st.markdown("""
        <div style="background:#1F0A0A;border:1px solid #7F1D1D;border-radius:12px;
                    padding:1.5rem 1.75rem;height:100%">
          <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;
                      color:#FCA5A5;margin-bottom:1rem">Without Memory</div>
          <ul style="font-size:15px;color:#FCA5A5;line-height:2.0;padding-left:1.25rem;margin:0">
            <li>Generic responses - no member context</li>
            <li>Member must re-explain every issue</li>
            <li>Can't detect fraud patterns across interactions</li>
            <li>No awareness of prior incidents or resolutions</li>
            <li>High escalation rate to human agents</li>
          </ul>
        </div>
        """, unsafe_allow_html=True)
    with col_r:
        st.markdown("""
        <div style="background:#052E16;border:1px solid #14532D;border-radius:12px;
                    padding:1.5rem 1.75rem;height:100%">
          <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;
                      color:#86EFAC;margin-bottom:1rem">With TiDB Memory</div>
          <ul style="font-size:15px;color:#86EFAC;line-height:2.0;padding-left:1.25rem;margin:0">
            <li>Personalized responses using member history</li>
            <li>Surfaces past incidents instantly via hybrid search</li>
            <li>Graph traversal detects multi-hop fraud chains</li>
            <li>Cites exact prior ticket IDs and resolutions</li>
            <li>60%+ autonomous resolution - fewer escalations</li>
          </ul>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:1.5rem'></div>", unsafe_allow_html=True)

    # Scenario cards
    st.markdown("""
    <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.12em;
                color:#0369A1;margin-bottom:.75rem">Demo Scenarios - Bob Johnson, FinanceCo Member</div>
    """, unsafe_allow_html=True)

    sc1, sc2, sc3 = st.columns(3, gap="medium")
    with sc1:
        st.markdown("""
        <div style="background:#0C1F3F;border:1px solid #1E40AF;border-radius:12px;padding:1.25rem 1.5rem">
          <div style="font-size:20px;margin-bottom:.5rem">&#x26FD;</div>
          <div style="font-size:13px;font-weight:700;color:#93C5FD;margin-bottom:.5rem">Scenario 1 - Member Support</div>
          <div style="font-size:14px;color:#BFDBFE;line-height:1.65">
            Bob's gas pump was declined. He asks why.<br><br>
            <b style="color:#fff">Engine:</b> Hybrid search (BM25 + vector) on support ticket history retrieves the exact incident record.
          </div>
        </div>
        """, unsafe_allow_html=True)
    with sc2:
        st.markdown("""
        <div style="background:#2D1515;border:1px solid #991B1B;border-radius:12px;padding:1.25rem 1.5rem">
          <div style="font-size:20px;margin-bottom:.5rem">&#x26A0;&#xFE0F;</div>
          <div style="font-size:13px;font-weight:700;color:#FCA5A5;margin-bottom:.5rem">Scenario 2 - Fraud Detection</div>
          <div style="font-size:14px;color:#FECACa;line-height:1.65">
            Bob's Pay Friends transfer triggered a 3-hop money chain.<br><br>
            <b style="color:#fff">Engine:</b> Recursive CTE walks the graph + hybrid search adds context. No graph DB needed.
          </div>
        </div>
        """, unsafe_allow_html=True)
    with sc3:
        st.markdown("""
        <div style="background:#1A1A0A;border:1px solid #854D0E;border-radius:12px;padding:1.25rem 1.5rem">
          <div style="font-size:20px;margin-bottom:.5rem">&#x1F514;</div>
          <div style="font-size:13px;font-weight:700;color:#FDE68A;margin-bottom:.5rem">Scenario 3 - Fraud Alert Summary</div>
          <div style="font-size:14px;color:#FEF3C7;line-height:1.65">
            Bob got a notification and wants to understand both active flags.<br><br>
            <b style="color:#fff">Engine:</b> Relational join on fraud_flags + hybrid search on prior alert history.
          </div>
        </div>
        """, unsafe_allow_html=True)

    # Architecture note
    st.markdown("""
    <div style="background:#0F172A;border:1px solid #334155;border-radius:10px;
                padding:1.25rem 1.75rem;margin-top:1.5rem">
      <div style="font-size:12px;font-weight:700;color:#60A5FA;text-transform:uppercase;
                  letter-spacing:.1em;margin-bottom:.6rem">TiDB Cloud Architecture</div>
      <div style="font-size:13.5px;color:#94A3B8;line-height:1.8">
        <b style="color:#E2E8F0">5 tables, 1 database, 1 connection string.</b>
        &nbsp;OLTP + vector embeddings + full-text BM25 + graph CTE traversal - all in standard SQL.
        No Redis for cache. No Pinecone for vectors. No Neo4j for graphs. No Elasticsearch for search.
        &nbsp;<b style="color:#34D399">PII never leaves your VPC</b> - embeddings generated server-side by TiDB,
        raw text never sent to an external embedding API.
      </div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 - FINANCO APP
# ══════════════════════════════════════════════════════════════════════════════
with tab_app:
    # Bob header
    st.markdown("""
    <div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:10px;
                padding:.9rem 1.25rem;margin-bottom:1.25rem;display:inline-block;width:100%">
      <span style="font-size:22px">&#128100;</span>
      <span style="font-size:16px;font-weight:700;color:#0F172A;margin-left:.5rem">Bob Johnson</span>
      <span style="font-size:13px;color:#64748B;margin-left:.75rem">MBR-BOB-001 &nbsp;&#8226;&nbsp; Active &nbsp;&#8226;&nbsp; SpotMe $200 &nbsp;&#8226;&nbsp; Chicago, IL</span>
    </div>
    """, unsafe_allow_html=True)

    # Question chips
    st.markdown("""
    <div style="font-size:12px;font-weight:700;color:#64748B;text-transform:uppercase;
                letter-spacing:.08em;margin-bottom:.6rem">Ask as Bob:</div>
    """, unsafe_allow_html=True)

    q_cols = st.columns([1, 1.3, 1], gap="small")
    with q_cols[0]:
        q1_click = st.button("⛽ Why was my gas pump declined?", use_container_width=True,
                             type="primary" if st.session_state.active_q == 1 else "secondary")
    with q_cols[1]:
        q2_click = st.button("⚠️ Did my Pay Friends transfer go through? It looks suspicious.",
                             use_container_width=True,
                             type="primary" if st.session_state.active_q == 2 else "secondary")
    with q_cols[2]:
        q3_click = st.button("🔔 I got a fraud notification. What happened?",
                             use_container_width=True,
                             type="primary" if st.session_state.active_q == 3 else "secondary")

    if q1_click:
        st.session_state.active_q = 1
    if q2_click:
        st.session_state.active_q = 2
    if q3_click:
        st.session_state.active_q = 3

    if st.session_state.active_q is None:
        st.markdown("""
        <div style="text-align:center;color:#94A3B8;font-size:15px;margin:3rem 0;line-height:2">
          Select a question above to see how TiDB memory transforms the response.<br>
          Left phone: no memory &nbsp;&#8226;&nbsp; Right phone: with TiDB memory
        </div>
        """, unsafe_allow_html=True)
    else:
        aq = st.session_state.active_q
        q_text = QUESTIONS[aq]

        # Run live recall for real snippets
        with st.spinner("Searching memory..."):
            try:
                if aq not in st.session_state.q_results:
                    live_results = recall_support("MBR-BOB-001", q_text, limit=4)
                    live_sql = get_last_sql(6)
                    st.session_state.q_results[aq] = {
                        "recall": live_results,
                        "sql": live_sql,
                    }
                cached = st.session_state.q_results[aq]
                live_results = cached["recall"]
                live_sql = cached["sql"]

                # Build real snippets from live results
                live_snippets = [
                    f"{r.get('ticket_id','?')} - {str(r.get('content',''))[:60]}... "
                    f"(score {float(r.get('_score') or r.get('_distance') or 0):.3f})"
                    for r in live_results[:2]
                ] if live_results else MEM_SNIPPETS[aq]

            except Exception:
                live_results = []
                live_sql = []
                live_snippets = MEM_SNIPPETS[aq]

        # Side-by-side phones
        phone_left, phone_right = st.columns(2, gap="large")

        with phone_left:
            st.markdown("""
            <div style="text-align:center;font-size:11px;font-weight:700;text-transform:uppercase;
                        letter-spacing:.1em;color:#94A3B8;margin-bottom:.75rem">
              Without Memory
            </div>
            """, unsafe_allow_html=True)
            st.html(
                _phone_frame("No context", q_text, WITHOUT_MEM[aq],
                             header_color="#64748B")
            )

        with phone_right:
            st.markdown("""
            <div style="text-align:center;font-size:11px;font-weight:700;text-transform:uppercase;
                        letter-spacing:.1em;color:#00C49A;margin-bottom:.75rem">
              With TiDB Memory
            </div>
            """, unsafe_allow_html=True)
            st.html(
                _phone_frame("TiDB-powered", q_text, WITH_MEM[aq],
                             mem_snippets=live_snippets)
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 - MEMORY DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
with tab_dash:
    try:
        stats = _get_stats()

        # ── Stat cards ────────────────────────────────────────────────────────
        c1, c2, c3, c4, c5, c6 = st.columns(6, gap="small")
        card_defs = [
            (c1, stats.get("members", 0), "Members", "#0369A1", "#EFF6FF"),
            (c2, stats.get("transactions", 0), "Transactions", "#059669", "#F0FDF4"),
            (c3, stats.get("support_tickets", 0), "Support Tickets", "#7C3AED", "#F5F3FF"),
            (c4, stats.get("fraud_flags", 0), "Fraud Flags", "#DC2626", "#FEF2F2"),
            (c5, stats.get("pay_friends_edges", 0), "Pay Friends Edges", "#D97706", "#FFFBEB"),
            (c6, stats.get("embeddings", 0), "Vector Embeddings", "#0891B2", "#ECFEFF"),
        ]
        for col, val, label, color, bg in card_defs:
            with col:
                st.markdown(
                    f'<div style="background:{bg};border:1px solid {color}33;border-radius:10px;'
                    f'padding:1rem;text-align:center">'
                    f'<div style="font-size:2rem;font-weight:800;color:{color}">{val}</div>'
                    f'<div style="font-size:10px;text-transform:uppercase;letter-spacing:.08em;'
                    f'color:{color};margin-top:.2rem">{label}</div></div>',
                    unsafe_allow_html=True,
                )

        st.markdown("<div style='margin-top:1.25rem'></div>", unsafe_allow_html=True)

        # ── Pay Friends graph ─────────────────────────────────────────────────
        st.plotly_chart(_build_network_graph(), use_container_width=True)

        # ── Index info ────────────────────────────────────────────────────────
        indexes = _get_indexes()
        vec_idx  = [i for i in indexes if i.get("Index_type") == "HNSW" or i.get("Key_name", "").startswith("vec")]
        fts_idx  = [i for i in indexes if i.get("Index_type") == "FULLTEXT"]
        norm_idx = [i for i in indexes if i.get("Index_type") == "BTREE"
                    and i.get("Key_name") not in ("PRIMARY",)]

        idx_cols = st.columns(3, gap="small")
        idx_defs = [
            (idx_cols[0], "HNSW Vector Index", len(vec_idx) > 0, "#7C3AED", "#F5F3FF",
             "fc_support_tickets.content_vec - 1536-dim cosine, HNSW graph"),
            (idx_cols[1], "BM25 Full-Text Index", len(fts_idx) > 0, "#059669", "#F0FDF4",
             "fc_support_tickets.content - MULTILINGUAL parser, inverted index"),
            (idx_cols[2], "B-Tree Indexes", len(norm_idx), "#0369A1", "#EFF6FF",
             "member_id, ticket_id, transaction_id lookups"),
        ]
        for col, label, val, color, bg, note in idx_defs:
            with col:
                display = "✓ Active" if val is True else ("✗ None" if val == 0 else f"{val} active")
                st.markdown(
                    f'<div style="background:{bg};border:1px solid {color}44;border-radius:8px;'
                    f'padding:.9rem 1rem">'
                    f'<div style="font-size:12px;font-weight:700;color:{color}">{label}</div>'
                    f'<div style="font-size:1.3rem;font-weight:800;color:{color};margin:.3rem 0">{display}</div>'
                    f'<div style="font-size:11px;color:#64748B">{note}</div></div>',
                    unsafe_allow_html=True,
                )

        st.markdown("<div style='margin-top:1.25rem'></div>", unsafe_allow_html=True)

        # ── Data tables ───────────────────────────────────────────────────────
        dtab1, dtab2, dtab3 = st.tabs(["Support Tickets", "Fraud Flags", "Bob's Transactions"])

        with dtab1:
            tickets = _get_tickets()
            if tickets:
                import pandas as pd
                df = pd.DataFrame(tickets)
                st.dataframe(
                    df[["ticket_id", "member_id", "vec_dims", "snippet", "created_at"]],
                    use_container_width=True, hide_index=True,
                    column_config={
                        "ticket_id": "Ticket ID",
                        "member_id": "Member",
                        "vec_dims": st.column_config.NumberColumn("Vec Dims", format="%d"),
                        "snippet": "Content (truncated)",
                        "created_at": "Created",
                    },
                )
            else:
                st.info("No tickets found. Run `python seed.py` first.")

        with dtab2:
            flags = _get_fraud()
            if flags:
                import pandas as pd
                df = pd.DataFrame(flags)
                st.dataframe(
                    df[["member_name", "flag_type", "confidence_score", "description", "resolved", "created_at"]],
                    use_container_width=True, hide_index=True,
                    column_config={
                        "member_name": "Member",
                        "flag_type": "Flag Type",
                        "confidence_score": st.column_config.NumberColumn("Confidence", format="%.2f"),
                        "description": "Description",
                        "resolved": "Resolved",
                        "created_at": "Flagged At",
                    },
                )
            else:
                st.info("No fraud flags found.")

        with dtab3:
            txns = _get_transactions()
            if txns:
                import pandas as pd
                df = pd.DataFrame(txns)
                cols = ["transaction_id", "merchant_name", "merchant_category",
                        "amount", "status", "created_at"]
                st.dataframe(
                    df[cols], use_container_width=True, hide_index=True,
                    column_config={
                        "transaction_id": "Txn ID",
                        "merchant_name": "Merchant",
                        "merchant_category": "Category",
                        "amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
                        "status": "Status",
                        "created_at": "Date",
                    },
                )
            else:
                st.info("No transactions found.")

    except Exception as e:
        st.error(f"Dashboard error: {e}")
        st.info("Make sure TIDB_URL is set and `python seed.py` has been run.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 - BACKEND SQL
# ══════════════════════════════════════════════════════════════════════════════
with tab_sql:
    aq = st.session_state.active_q
    cached = st.session_state.q_results.get(aq, {}) if aq else {}
    live_results = cached.get("recall", [])

    sql_l, sql_r = st.columns([3, 2], gap="medium")

    with sql_l:
        with st.expander(
            "**Scenario 1 - Member Support: Hybrid Search**" +
            (" ← active" if aq == 1 else ""),
            expanded=(aq == 1 or aq is None),
        ):
            st.markdown(
                f'<div class="sql-panel">'
                f'{_sql_q1("gas pump declined", live_results if aq == 1 else [])}'
                f'</div>',
                unsafe_allow_html=True,
            )

        with st.expander(
            "**Scenario 2 - Fraud Detection: Recursive CTE + Hybrid Search**" +
            (" ← active" if aq == 2 else ""),
            expanded=(aq == 2),
        ):
            st.markdown(
                f'<div class="sql-panel">{_sql_q2()}</div>',
                unsafe_allow_html=True,
            )

        with st.expander(
            "**Scenario 3 - Fraud Alert: Relational Lookup + Hybrid Search**" +
            (" ← active" if aq == 3 else ""),
            expanded=(aq == 3),
        ):
            st.markdown(
                f'<div class="sql-panel">{_sql_q3()}</div>',
                unsafe_allow_html=True,
            )

    with sql_r:
        st.markdown("""
        <div style="background:#0F172A;border-radius:10px;padding:1.25rem 1.5rem;color:#E2E8F0">
          <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;
                      color:#60A5FA;margin-bottom:.75rem">TiDB Capability Map</div>
          <div style="font-size:12.5px;line-height:1.9">
            <div style="margin-bottom:.6rem">
              <span style="background:#4C1D95;color:#DDD6FE;padding:2px 7px;border-radius:4px;
                           font-size:11px;font-weight:700">BM25</span>
              &nbsp;<span style="color:#94A3B8">Full-text search, MULTILINGUAL parser,
              IDF-weighted scoring, no external search engine</span>
            </div>
            <div style="margin-bottom:.6rem">
              <span style="background:#0C4A6E;color:#BAE6FD;padding:2px 7px;border-radius:4px;
                           font-size:11px;font-weight:700">VECTOR</span>
              &nbsp;<span style="color:#94A3B8">HNSW index, Amazon Titan embeddings called
              server-side, cosine distance, no embedding client needed</span>
            </div>
            <div style="margin-bottom:.6rem">
              <span style="background:#064E3B;color:#A7F3D0;padding:2px 7px;border-radius:4px;
                           font-size:11px;font-weight:700">RRF</span>
              &nbsp;<span style="color:#94A3B8">Python-side Reciprocal Rank Fusion merges
              BM25 + vector rankings into a single ordered result</span>
            </div>
            <div style="margin-bottom:.6rem">
              <span style="background:#78350F;color:#FDE68A;padding:2px 7px;border-radius:4px;
                           font-size:11px;font-weight:700">GRAPH</span>
              &nbsp;<span style="color:#94A3B8">WITH RECURSIVE CTE traverses Pay Friends
              graph up to N hops in standard SQL - no Neo4j</span>
            </div>
            <div>
              <span style="background:#1E1B4B;color:#C7D2FE;padding:2px 7px;border-radius:4px;
                           font-size:11px;font-weight:700">OLTP</span>
              &nbsp;<span style="color:#94A3B8">Row + columnar storage, ACID transactions,
              members / transactions / fraud flags in same DB</span>
            </div>
          </div>
          <div style="border-top:1px solid #1E293B;margin-top:1rem;padding-top:.75rem;
                      font-size:11.5px;color:#475569;line-height:1.8">
            All five capabilities run on a single TiDB Cloud Serverless cluster.
            One connection string. No infrastructure to stitch together.
          </div>
        </div>
        """, unsafe_allow_html=True)

        if aq and live_results:
            st.markdown("""
            <div style="background:#0F172A;border-radius:10px;padding:1.1rem 1.5rem;
                        color:#E2E8F0;margin-top:.75rem;font-family:ui-monospace,monospace;
                        font-size:12px">
              <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                          letter-spacing:.1em;color:#34D399;margin-bottom:.6rem">
                Live Capture - Last Query
              </div>
            """, unsafe_allow_html=True)
            for entry in cached.get("sql", []):
                sql_text = entry.get("sql", "")[:400]
                st.code(sql_text, language="sql")
            st.markdown("</div>", unsafe_allow_html=True)
