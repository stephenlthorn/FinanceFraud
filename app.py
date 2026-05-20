"""FinanceCo AI Demo — TiDB Cloud: hybrid search + graph fraud detection."""
import re
import os
from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import plotly.graph_objects as go

from memory import recall_support
from backend import (
    get_db_stats, get_index_info, get_all_tickets,
    get_all_fraud_flags, get_recent_transactions,
)

st.set_page_config(
    page_title="FinanceCo AI Demo",
    page_icon="💚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
html,body,[class*="css"]{font-family:-apple-system,system-ui,BlinkMacSystemFont,sans-serif}
.block-container{padding:1.25rem 2.5rem 2rem;max-width:100%}

/* Scenario pills */
div[data-testid="stButton"]>button{border-radius:20px;font-weight:600;font-size:13px}

/* Search input */
div[data-testid="stTextInput"] input{
  font-size:16px;border-radius:10px;padding:10px 16px;
  border:2px solid #E2E8F0;background:#F8FAFC;
}
div[data-testid="stTextInput"] input:focus{border-color:#00C49A;background:white}

/* Tech pipeline badge */
.pipeline{
  display:flex;align-items:center;gap:.5rem;flex-wrap:wrap;
  background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;
  padding:.65rem 1.25rem;margin:.5rem 0 .25rem;font-size:13px
}
.p-bm25{color:#7C3AED;font-weight:700;background:#EDE9FE;padding:2px 9px;border-radius:5px}
.p-vec {color:#0891B2;font-weight:700;background:#CFFAFE;padding:2px 9px;border-radius:5px}
.p-rrf {color:#059669;font-weight:700;background:#D1FAE5;padding:2px 9px;border-radius:5px}
.p-cte {color:#B45309;font-weight:700;background:#FEF3C7;padding:2px 9px;border-radius:5px}
.p-jn  {color:#DC2626;font-weight:700;background:#FEE2E2;padding:2px 9px;border-radius:5px}
.p-arr {color:#94A3B8;font-size:15px;padding:0 2px}
.p-hit {
  color:#059669;font-weight:700;background:#F0FDF4;
  border:1px solid #BBF7D0;padding:2px 10px;border-radius:14px;font-size:12px
}

/* SQL panel */
.sql-panel{background:#0F172A;border-radius:10px;padding:1.1rem 1.4rem;
           color:#E2E8F0;font-family:ui-monospace,monospace;font-size:12px;line-height:1.7}
.lbl{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;
     padding:2px 8px;border-radius:4px;display:inline-block;margin:.8rem 0 .35rem}
.lbl-f{background:#4C1D95;color:#DDD6FE}
.lbl-v{background:#0C4A6E;color:#BAE6FD}
.lbl-r{background:#064E3B;color:#A7F3D0}
.lbl-c{background:#78350F;color:#FDE68A}
.lbl-j{background:#7F1D1D;color:#FCA5A5}
.sql-block{background:#1E293B;border-radius:6px;padding:.6rem .9rem;
           margin:.3rem 0 .7rem;white-space:pre;overflow-x:auto}
.kw{color:#93C5FD}.fn{color:#6EE7B7}.str{color:#FCD34D}
.dim{color:#475569}.cte-kw{color:#FDE68A}
.note{font-family:-apple-system,system-ui,sans-serif;font-size:12px;
      color:#94A3B8;margin:.2rem 0 .4rem;line-height:1.5}
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
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
        "&bull; Network connectivity issue<br>"
        "&bull; Security hold on new card<br><br>"
        "Please check your balance and try again. For help call <b>1-800-FINANCE</b>."
    ),
    2: (
        "Pay Friends transfers typically complete in 1-3 minutes.<br><br>"
        "To check status: <b>Home &rarr; Pay Friends &rarr; History</b><br><br>"
        "If still pending after 24 hours, contact support with your confirmation number."
    ),
    3: (
        "Fraud notifications are sent when we detect unusual activity.<br><br>"
        "To review: <b>Settings &rarr; Security &rarr; Recent Alerts</b><br><br>"
        "If you see a charge you don&#39;t recognize, tap <b>Dispute</b> and "
        "we&#39;ll investigate within 24 hours."
    ),
}

WITH_MEM = {
    1: (
        "Hi Bob! Found it. &#x1F50D;<br><br>"
        "Your <b>Shell Gas Station</b> charge (Jan&nbsp;15, $45.00) was blocked "
        "by fraud detection.<br><br>"
        "<b>Why:</b> Account is Chicago,&nbsp;IL but the pump was "
        "<b>Houston,&nbsp;TX</b> &mdash; no travel alert on file.<br><br>"
        "Was this you? I can approve the location so you can retry now."
    ),
    2: (
        "Hi Bob! Your $200 to <b>Mike Torres</b> (Jan&nbsp;13) completed. &#x2705;<br><br>"
        "<b>&#x26A0;&#xFE0F; Suspicious chain detected:</b><br>"
        "Bob &rarr; Mike ($200) &rarr; Alex Rivera ($180, +28&nbsp;min) "
        "&rarr; Jordan Kim ($170, +15&nbsp;min)<br><br>"
        "Jordan Kim has <b>zero prior</b> FinanceCo history. "
        "Fraud model: <b>97% confidence</b>. Want to dispute?"
    ),
    3: (
        "Hi Bob! You have <b>2 active flags</b>:<br><br>"
        "<b>1. &#x1F534; Gas Decline (Jan&nbsp;15)</b><br>"
        "Shell Houston TX &mdash; Chicago account, no travel alert. Score: 82%<br><br>"
        "<b>2. &#x1F534; Pay Friends Chain (Jan&nbsp;13)</b><br>"
        "$200 to Mike triggered 3-hop forwarding to Jordan Kim (new account). Score: 97%<br><br>"
        "Both pending your review. Walk through each?"
    ),
}

MEM_FALLBACK = {
    1: ["TKT-BOB-001 &mdash; Gas pump declined Houston TX (0.94)",
        "TKT-BOB-006 &mdash; Rapid gas station fraud alert (0.67)"],
    2: ["TKT-BOB-005 &mdash; Pay Friends transfer failed (0.81)",
        "TKT-BOB-001 &mdash; Out-of-state decline context (0.58)"],
    3: ["TKT-BOB-006 &mdash; Multiple rapid gas fraud alert (0.88)",
        "TKT-BOB-001 &mdash; Out-of-state card decline (0.72)"],
}


# ── Helpers ───────────────────────────────────────────────────────────────────
def _hl(sql: str) -> str:
    sql = re.sub(
        r'\b(SELECT|FROM|WHERE|ORDER\s+BY|LIMIT|AND|OR|AS|ASC|DESC|'
        r'INSERT|INTO|VALUES|NOT|JOIN|LEFT|ON|UNION|ALL|CONCAT|CAST)\b',
        r'<span class="kw">\1</span>', sql)
    sql = re.sub(r'\b(WITH\s+RECURSIVE|WITH|RECURSIVE)\b',
                 r'<span class="cte-kw">\1</span>', sql)
    sql = re.sub(
        r'\b(FTS_MATCH_WORD|VEC_COSINE_DISTANCE|VEC_DIMS|EMBED_TEXT|MATCH|AGAINST)\b',
        r'<span class="fn">\1</span>', sql)
    sql = re.sub(r"'([^']*)'", r'<span class="str">\'\1\'</span>', sql)
    return sql


def _phone(label: str, q: str, resp: str, snippets: list | None = None,
           hcolor: str = "#00C49A") -> str:
    mem = ""
    if snippets:
        rows = "".join(
            f'<div style="font-size:11px;color:#005F47;margin:2px 0">&#128206; {s}</div>'
            for s in snippets
        )
        mem = (
            '<div style="background:#E6FAF5;border-left:3px solid #00C49A;'
            'padding:7px 10px;border-radius:4px;margin:8px 0">'
            '<div style="font-size:10px;font-weight:700;color:#007A57;'
            'text-transform:uppercase;letter-spacing:.5px;margin-bottom:3px">'
            'Memory Retrieved</div>' + rows + '</div>'
        )
    return f"""
<div style="border:5px solid #1B2B4A;border-radius:36px;background:#0A0E1A;
            padding:18px 16px 22px;margin:0 auto;min-height:500px">
  <div style="text-align:center;margin-bottom:10px">
    <div style="background:#2D3D5A;width:70px;height:14px;
                border-radius:8px;display:inline-block"></div>
  </div>
  <div style="background:{hcolor};padding:10px 14px;border-radius:14px 14px 0 0;
              text-align:center">
    <span style="color:white;font-weight:700;font-size:15px">&#128154; FinanceCo</span>
    <div style="color:rgba(255,255,255,.8);font-size:10px;margin-top:1px">{label}</div>
  </div>
  <div style="background:#F5F7FA;padding:14px 12px;border-radius:0 0 14px 14px;
              min-height:420px">
    <div style="text-align:right;margin-bottom:10px">
      <div style="display:inline-block;background:#00C49A;color:white;
                  padding:8px 12px;border-radius:16px 16px 4px 16px;
                  max-width:85%;font-size:12px;line-height:1.5">{q}</div>
    </div>
    {mem}
    <div style="margin-top:8px">
      <div style="display:inline-block;background:white;color:#1a2035;
                  padding:10px 13px;border-radius:4px 16px 16px 16px;
                  max-width:92%;font-size:12px;border:1px solid #E2E8F0;
                  line-height:1.6">{resp}</div>
    </div>
  </div>
</div>"""


def _snippets(results: list, scenario: int) -> list:
    if results:
        return [
            f"{r.get('ticket_id','?')} &mdash; "
            f"{str(r.get('content',''))[:55]}... "
            f"({float(r.get('_score') or r.get('_distance') or 0):.3f})"
            for r in results[:2]
        ]
    return MEM_FALLBACK.get(scenario, MEM_FALLBACK[1])


# ── Cached data ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def _search(query: str) -> list:
    try:
        return recall_support("MBR-BOB-001", query, limit=4)
    except Exception:
        return []

@st.cache_data(ttl=60)
def _get_stats(): return get_db_stats()

@st.cache_data(ttl=60)
def _get_tickets(): return get_all_tickets()

@st.cache_data(ttl=60)
def _get_fraud(): return get_all_fraud_flags()

@st.cache_data(ttl=60)
def _get_transactions(): return get_recent_transactions("MBR-BOB-001", limit=10)

@st.cache_data(ttl=300)
def _get_indexes(): return get_index_info()


@st.cache_data(ttl=300)
def _network_graph() -> go.Figure:
    nodes = {
        "MBR-BOB-001": (0.0,  0.0, "Bob Johnson", "#00C49A", 22),
        "MBR-SAR-002": (-0.8, 0.9, "Sarah Chen",  "#00C49A", 18),
        "MBR-MIK-003": (1.0,  0.0, "Mike Torres", "#F59E0B", 18),
        "MBR-ALE-004": (2.0,  0.0, "Alex Rivera", "#EF4444", 18),
        "MBR-JOR-005": (3.0,  0.0, "Jordan Kim",  "#DC2626", 18),
    }
    edges = [
        ("MBR-BOB-001","MBR-SAR-002","$35",        "#94A3B8","normal"),
        ("MBR-BOB-001","MBR-MIK-003","$200",        "#3B82F6","trigger"),
        ("MBR-MIK-003","MBR-ALE-004","$180 +28min","#F59E0B","flagged"),
        ("MBR-ALE-004","MBR-JOR-005","$170 +15min","#EF4444","flagged"),
    ]
    fig = go.Figure()
    for src, dst, lbl, color, etype in edges:
        x0,y0 = nodes[src][0],nodes[src][1]
        x1,y1 = nodes[dst][0],nodes[dst][1]
        fig.add_trace(go.Scatter(
            x=[x0,x1,None], y=[y0,y1,None], mode="lines",
            line=dict(color=color, width=2 if etype=="normal" else 3,
                      dash="dot" if etype=="normal" else "solid"),
            hoverinfo="skip", showlegend=False))
        mx,my = (x0+x1)/2,(y0+y1)/2+0.1
        fig.add_annotation(x=mx,y=my,text=f"<b>{lbl}</b>",showarrow=False,
                           font=dict(size=11,color=color),
                           bgcolor="rgba(255,255,255,0.85)",borderpad=3)
    status = {"MBR-BOB-001":"active","MBR-SAR-002":"active",
              "MBR-MIK-003":"active","MBR-ALE-004":"FLAGGED","MBR-JOR-005":"FROZEN"}
    for mid,(x,y,name,color,sz) in nodes.items():
        fig.add_trace(go.Scatter(
            x=[x],y=[y],mode="markers+text",
            marker=dict(size=sz,color=color,line=dict(color="white",width=2)),
            text=[name],textposition="top center",
            textfont=dict(size=11,color="#0F172A"),
            hovertext=[f"<b>{name}</b><br>{mid}<br>Status: {status[mid]}"],
            hoverinfo="text",showlegend=False))
    fig.update_layout(
        title=dict(text="Pay Friends Network - Fraud Chain",
                   font=dict(size=13,color="#0F172A"),x=0.5),
        xaxis=dict(visible=False,range=[-1.3,3.6]),
        yaxis=dict(visible=False,range=[-0.6,1.4]),
        plot_bgcolor="#F8FAFC",paper_bgcolor="#F8FAFC",
        margin=dict(l=20,r=20,t=40,b=10),height=260,
        annotations=[
            dict(x=3.0,y=-0.4,text="&#128274; Frozen<br>Zero history",
                 showarrow=True,arrowhead=2,ax=0,ay=-28,
                 font=dict(size=10,color="#DC2626"),
                 bgcolor="rgba(254,226,226,0.9)",borderpad=4,bordercolor="#EF4444"),
            dict(x=2.1,y=-0.35,text="&#128680; 97% fraud",
                 showarrow=True,arrowhead=2,ax=10,ay=-22,
                 font=dict(size=10,color="#EF4444"),
                 bgcolor="rgba(254,226,226,0.9)",borderpad=4,bordercolor="#F59E0B"),
        ])
    return fig


# ── SQL panels ────────────────────────────────────────────────────────────────
def _sql1(q: str, results: list) -> str:
    fts = (
        "SELECT ticket_id, content,\n"
        f"       FTS_MATCH_WORD(content, '{q}') AS bm25_score\n"
        "FROM   fc_support_tickets\n"
        "WHERE  member_id = 'MBR-BOB-001'\n"
        "  AND  FTS_MATCH_WORD(content, '{q}')\n"
        "ORDER  BY bm25_score DESC  LIMIT 10"
    )
    vec = (
        "SELECT ticket_id, content,\n"
        "       VEC_COSINE_DISTANCE(\n"
        "           content_vec,\n"
        f"           EMBED_TEXT('{q}')\n"
        "       ) AS distance\n"
        "FROM   fc_support_tickets\n"
        "WHERE  member_id = 'MBR-BOB-001'\n"
        "ORDER  BY distance ASC  LIMIT 10"
    )
    rows = "".join(
        f'<div style="background:#1E293B;border-radius:5px;padding:.35rem .75rem;margin:.2rem 0">'
        f'<span style="color:#60A5FA;font-weight:700;font-size:11.5px">{r.get("ticket_id","?")}</span>'
        f'<span style="float:right;color:#64748B;font-size:11px">'
        f'RRF {float(r.get("_score") or r.get("_distance") or 0):.4f}</span>'
        f'<div style="color:#94A3B8;font-size:11px;margin-top:.15rem;'
        f'font-family:-apple-system,system-ui,sans-serif">'
        f'{str(r.get("content",""))[:110]}...</div></div>'
        for r in (results or [])[:4]
    ) or '<div style="color:#475569;font-size:12px;font-family:sans-serif">No live results yet.</div>'

    return f"""
<span class="lbl lbl-f">&#9312; BM25 Full-Text</span>
<div class="note">Every word indexed. Domain terms like <b style="color:#DDD6FE">gas</b>, <b style="color:#DDD6FE">pump</b>, <b style="color:#DDD6FE">declined</b> score high by IDF rarity.</div>
<div class="sql-block">{_hl(fts)}</div>

<span class="lbl lbl-v">&#9313; Vector Search</span>
<div class="note">Raw text in SQL &mdash; TiDB calls <b style="color:#BAE6FD">Amazon Titan server-side</b>. No embedding client in your app.</div>
<div class="sql-block">{_hl(vec)}</div>

<span class="lbl lbl-r">&#9314; RRF Fusion (Python-side)</span>
<div class="note" style="font-family:ui-monospace,monospace;color:#6EE7B7">score = 1/(60 + rank_bm25) + 1/(60 + rank_vec)</div>
{rows}
"""


def _sql2() -> str:
    cte = """WITH RECURSIVE pay_chain AS (
  SELECT from_member_id, to_member_id,
         amount, transfer_id, created_at,
         0 AS depth,
         CAST(from_member_id AS CHAR(1000)) AS path
  FROM   fc_pay_friends_edges
  WHERE  from_member_id = 'MBR-BOB-001'

  UNION ALL

  SELECT e.from_member_id, e.to_member_id,
         e.amount, e.transfer_id, e.created_at,
         pc.depth + 1,
         CONCAT(pc.path, ' -> ', e.from_member_id)
  FROM   fc_pay_friends_edges e
  JOIN   pay_chain pc
    ON   e.from_member_id = pc.to_member_id
  WHERE  pc.depth < 3
)
SELECT pc.*, mf.name AS from_name, mt.name AS to_name,
       ff.flag_type, ff.confidence_score
FROM   pay_chain pc
LEFT JOIN fc_members mf ON mf.member_id = pc.from_member_id
LEFT JOIN fc_members mt ON mt.member_id = pc.to_member_id
LEFT JOIN fc_fraud_flags ff ON ff.transaction_id = pc.transfer_id
ORDER  BY pc.depth, pc.created_at"""
    recall = (
        "SELECT ticket_id, content,\n"
        "       FTS_MATCH_WORD(content, 'Pay Friends suspicious') AS bm25,\n"
        "       VEC_COSINE_DISTANCE(content_vec,\n"
        "           EMBED_TEXT('Pay Friends suspicious')) AS vec\n"
        "FROM   fc_support_tickets\n"
        "WHERE  member_id = 'MBR-BOB-001'\n"
        "ORDER  BY (RRF rank fusion)  LIMIT 3"
    )
    return f"""
<span class="lbl lbl-c">&#9312; Recursive CTE &mdash; Graph Traversal</span>
<div class="note">Standard SQL <b style="color:#FDE68A">WITH RECURSIVE</b> walks the Pay Friends graph up to 3 hops. No graph DB needed.</div>
<div class="sql-block">{_hl(cte)}</div>

<span class="lbl lbl-f">&#9313; Hybrid Search &mdash; Past Context</span>
<div class="note">BM25 + Vector retrieves prior Pay Friends tickets to give the AI member history.</div>
<div class="sql-block">{_hl(recall)}</div>
"""


def _sql3() -> str:
    lookup = (
        "SELECT m.name, m.account_status, m.spotme_limit,\n"
        "       f.flag_type, f.confidence_score, f.resolved\n"
        "FROM   fc_members m\n"
        "LEFT JOIN fc_fraud_flags f ON f.member_id = m.member_id\n"
        "WHERE  m.member_id = 'MBR-BOB-001'\n"
        "ORDER  BY f.created_at DESC"
    )
    recall = (
        "SELECT ticket_id, content,\n"
        "       FTS_MATCH_WORD(content, 'fraud alert unusual activity') AS bm25,\n"
        "       VEC_COSINE_DISTANCE(content_vec,\n"
        "           EMBED_TEXT('fraud alert unusual activity')) AS vec\n"
        "FROM   fc_support_tickets\n"
        "WHERE  member_id = 'MBR-BOB-001'\n"
        "ORDER  BY (RRF rank fusion)  LIMIT 3"
    )
    return f"""
<span class="lbl lbl-j">&#9312; Relational JOIN &mdash; Fraud Flags</span>
<div class="note">Direct join surfaces all active flags with exact confidence scores for the authenticated member.</div>
<div class="sql-block">{_hl(lookup)}</div>

<span class="lbl lbl-f">&#9313; Hybrid Search &mdash; Incident History</span>
<div class="note">Semantic + keyword search retrieves prior fraud interactions so the AI doesn&#39;t repeat itself.</div>
<div class="sql-block">{_hl(recall)}</div>
"""


# ── Memory store render ───────────────────────────────────────────────────────
def _memory_store(scenario: int):
    import pandas as pd

    defs = {
        "support_tickets":   ("Support Tickets",    "#7C3AED","#F5F3FF"),
        "embeddings":        ("Vector Embeddings",  "#0891B2","#ECFEFF"),
        "fraud_flags":       ("Fraud Flags",        "#DC2626","#FEF2F2"),
        "pay_friends_edges": ("Pay Friends Edges",  "#D97706","#FFFBEB"),
        "members":           ("Members",            "#0369A1","#EFF6FF"),
        "transactions":      ("Transactions",       "#059669","#F0FDF4"),
    }
    keys_map = {
        1: ["support_tickets","embeddings","members","transactions"],
        2: ["pay_friends_edges","fraud_flags","members","transactions"],
        3: ["fraud_flags","support_tickets","embeddings","members"],
    }
    keys = keys_map.get(scenario, keys_map[1])

    try:
        stats = _get_stats()
        cols = st.columns(len(keys), gap="small")
        for col, k in zip(cols, keys):
            lbl, color, bg = defs[k]
            with col:
                st.markdown(
                    f'<div style="background:{bg};border:1px solid {color}33;'
                    f'border-radius:8px;padding:.65rem .9rem;text-align:center">'
                    f'<div style="font-size:1.6rem;font-weight:800;color:{color}">'
                    f'{stats.get(k,0)}</div>'
                    f'<div style="font-size:10px;text-transform:uppercase;'
                    f'letter-spacing:.08em;color:{color};margin-top:.1rem">{lbl}</div>'
                    f'</div>', unsafe_allow_html=True)
    except Exception:
        pass

    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

    try:
        indexes = _get_indexes()
        vec_ok = any(i.get("Index_type")=="HNSW" or
                     i.get("Key_name","").startswith("vec") for i in indexes)
        fts_ok = any(i.get("Index_type")=="FULLTEXT" for i in indexes)
        ic1, ic2 = st.columns(2, gap="small")
        with ic1:
            st.markdown(
                f'<div style="background:#F5F3FF;border:1px solid #7C3AED44;'
                f'border-radius:8px;padding:.6rem .9rem">'
                f'<div style="font-size:11px;font-weight:700;color:#7C3AED">HNSW Vector Index</div>'
                f'<div style="font-size:1.1rem;font-weight:800;color:#7C3AED;margin:.1rem 0">'
                f'{"&#10003; Active" if vec_ok else "&#10007; None"}</div>'
                f'<div style="font-size:11px;color:#64748B">content_vec &mdash; '
                f'1536-dim cosine</div></div>', unsafe_allow_html=True)
        with ic2:
            st.markdown(
                f'<div style="background:#F0FDF4;border:1px solid #05996944;'
                f'border-radius:8px;padding:.6rem .9rem">'
                f'<div style="font-size:11px;font-weight:700;color:#059669">BM25 Full-Text Index</div>'
                f'<div style="font-size:1.1rem;font-weight:800;color:#059669;margin:.1rem 0">'
                f'{"&#10003; Active" if fts_ok else "&#10007; None"}</div>'
                f'<div style="font-size:11px;color:#64748B">content &mdash; '
                f'MULTILINGUAL inverted index</div></div>', unsafe_allow_html=True)
    except Exception:
        pass

    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

    try:
        if scenario == 2:
            flags = _get_fraud()
            if flags:
                df = pd.DataFrame(flags)
                st.dataframe(
                    df[["member_name","flag_type","confidence_score","description","resolved","created_at"]],
                    use_container_width=True, hide_index=True,
                    column_config={
                        "member_name":"Member","flag_type":"Flag",
                        "confidence_score":st.column_config.NumberColumn("Confidence",format="%.2f"),
                        "description":"Description","resolved":"Resolved","created_at":"Flagged At",
                    })
        elif scenario == 3:
            txns = _get_transactions()
            if txns:
                df = pd.DataFrame(txns)
                st.dataframe(
                    df[["transaction_id","merchant_name","merchant_category","amount","status","created_at"]],
                    use_container_width=True, hide_index=True,
                    column_config={
                        "transaction_id":"Txn ID","merchant_name":"Merchant",
                        "merchant_category":"Category",
                        "amount":st.column_config.NumberColumn("Amount",format="$%.2f"),
                        "status":"Status","created_at":"Date",
                    })
        else:
            tickets = _get_tickets()
            if tickets:
                df = pd.DataFrame(tickets)
                st.dataframe(
                    df[["ticket_id","member_id","vec_dims","snippet","created_at"]],
                    use_container_width=True, hide_index=True,
                    column_config={
                        "ticket_id":"Ticket ID","member_id":"Member",
                        "vec_dims":st.column_config.NumberColumn("Vec Dims",format="%d"),
                        "snippet":"Content Preview","created_at":"Created",
                    })
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# LAYOUT
# ══════════════════════════════════════════════════════════════════════════════

# Session state
if "scenario" not in st.session_state:
    st.session_state.scenario = 1

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;justify-content:space-between;
            padding:.5rem 0 1rem">
  <div style="display:flex;align-items:center;gap:.75rem">
    <span style="font-size:22px;font-weight:800;color:#00C49A">FinanceCo</span>
    <span style="font-size:14px;color:#64748B">AI Member Support Demo</span>
    <span style="font-size:11px;color:#94A3B8;background:#F1F5F9;
                 padding:3px 10px;border-radius:10px">
      Powered by TiDB Cloud &nbsp;&#8226;&nbsp; Hybrid Search + Graph Traversal
    </span>
  </div>
  <div style="font-size:12px;background:#F0FDF4;color:#059669;
              padding:5px 14px;border-radius:12px;border:1px solid #BBF7D0">
    Bob Johnson &nbsp;&#8226;&nbsp; MBR-BOB-001 &nbsp;&#8226;&nbsp; Chicago, IL
  </div>
</div>
""", unsafe_allow_html=True)

# ── Scenario pills ────────────────────────────────────────────────────────────
sc = st.session_state.scenario
SCENARIOS = [
    (1, "⛽  Gas Pump Declined"),
    (2, "⚠️  Pay Friends Fraud"),
    (3, "🔔  Fraud Alert"),
]
pill_cols = st.columns([1, 1, 1, 3])
for col, (n, label) in zip(pill_cols, SCENARIOS):
    with col:
        if st.button(label, use_container_width=True,
                     type="primary" if sc == n else "secondary",
                     key=f"pill_{n}"):
            st.session_state.scenario = n
            st.rerun()

st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)

# ── Live search ───────────────────────────────────────────────────────────────
query = st.text_input(
    "search",
    value=QUESTIONS[st.session_state.scenario],
    key=f"q_{st.session_state.scenario}",
    placeholder="Type any member question...",
    label_visibility="collapsed",
)

results = _search(query) if query.strip() else []

st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)

# ── Phone comparison ──────────────────────────────────────────────────────────
col_l, col_r = st.columns(2, gap="large")

scenario = st.session_state.scenario
snips = _snippets(results, scenario)
with_resp = WITH_MEM.get(scenario, WITH_MEM[1])

# For custom queries not matching a preset scenario, build response from results
def _custom_response(q: str, res: list) -> str:
    if res:
        top = res[0]
        snip = str(top.get("content", ""))[:200]
        tid  = top.get("ticket_id", "")
        return (
            f"Based on your account history, I found a relevant prior incident "
            f"(<b>{tid}</b>):<br><br>{snip}..."
        )
    return (
        "I searched your account history but didn't find an exact match. "
        "Let me connect you with a specialist who can review your full account."
    )

preset_queries = set(QUESTIONS.values())
if query.strip() not in preset_queries:
    with_resp = _custom_response(query, results)

without_resp = WITHOUT_MEM.get(scenario, WITHOUT_MEM[1])

with col_l:
    st.markdown(
        '<div style="text-align:center;font-size:11px;font-weight:700;'
        'text-transform:uppercase;letter-spacing:.1em;color:#94A3B8;'
        'margin-bottom:.65rem">Without Memory</div>',
        unsafe_allow_html=True)
    st.html(_phone("No context", query, without_resp, hcolor="#475569"))

with col_r:
    st.markdown(
        '<div style="text-align:center;font-size:11px;font-weight:700;'
        'text-transform:uppercase;letter-spacing:.1em;color:#00C49A;'
        'margin-bottom:.65rem">With TiDB Memory</div>',
        unsafe_allow_html=True)
    st.html(_phone("TiDB-powered", query, with_resp, snippets=snips))

# ── Network graph (scenario 2 only) ──────────────────────────────────────────
if scenario == 2:
    st.markdown("<div style='height:.25rem'></div>", unsafe_allow_html=True)
    gc1, gc2, gc3 = st.columns([1, 3, 1])
    with gc2:
        st.plotly_chart(_network_graph(), use_container_width=True)

# ── Tech pipeline badge ───────────────────────────────────────────────────────
top_hit = results[0] if results else None
hit_chip = ""
if top_hit:
    tid   = top_hit.get("ticket_id", "?")
    score = float(top_hit.get("_score") or top_hit.get("_distance") or 0)
    hit_chip = f'<span class="p-hit">&#10003; {tid} &nbsp; {score:.3f}</span>'

pipeline_html = {
    1: f'<span class="p-bm25">BM25 Full-Text</span>'
       f'<span class="p-arr">+</span>'
       f'<span class="p-vec">Vector Search</span>'
       f'<span class="p-arr">&#8594;</span>'
       f'<span class="p-rrf">RRF Fusion</span>'
       f'<span class="p-arr">&#8594;</span> {hit_chip}',
    2: f'<span class="p-cte">Recursive CTE</span>'
       f'<span class="p-arr">+</span>'
       f'<span class="p-bm25">BM25</span>'
       f'<span class="p-arr">+</span>'
       f'<span class="p-vec">Vector</span>'
       f'<span class="p-arr">&#8594;</span>'
       f'<span class="p-rrf">RRF</span>'
       f'<span class="p-arr">&#8594;</span> {hit_chip}',
    3: f'<span class="p-jn">Relational JOIN</span>'
       f'<span class="p-arr">+</span>'
       f'<span class="p-bm25">BM25</span>'
       f'<span class="p-arr">+</span>'
       f'<span class="p-vec">Vector</span>'
       f'<span class="p-arr">&#8594;</span>'
       f'<span class="p-rrf">RRF</span>'
       f'<span class="p-arr">&#8594;</span> {hit_chip}',
}

st.markdown(
    f'<div class="pipeline">'
    f'<span style="color:#475569;font-size:12px;margin-right:.25rem">How TiDB found this:</span>'
    f'{pipeline_html[scenario]}</div>',
    unsafe_allow_html=True)

# ── Expanders ─────────────────────────────────────────────────────────────────
with st.expander("🔍  SQL & Query Flow", expanded=False):
    sql_map = {1: _sql1(query, results), 2: _sql2(), 3: _sql3()}
    st.markdown(f'<div class="sql-panel">{sql_map[scenario]}</div>',
                unsafe_allow_html=True)

with st.expander("🧠  Memory Store", expanded=False):
    _memory_store(scenario)
