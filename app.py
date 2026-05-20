"""FinanceCo AI Demo — TiDB Cloud: hybrid search + graph fraud detection."""
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

st.set_page_config(
    page_title="FinanceCo AI Demo",
    page_icon="💚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

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

st.markdown("""
<style>
html,body,[class*="css"]{font-family:-apple-system,system-ui,BlinkMacSystemFont,sans-serif}
.block-container{padding:1.25rem 1.75rem 1rem;max-width:100%}
div[data-testid="stTabs"] button[data-baseweb="tab"]{
  font-size:14px;font-weight:600;padding:.45rem 1.5rem}
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

# ── Helpers ───────────────────────────────────────────────────────────────────
STOP_WORDS = {
    "a","an","the","is","it","in","on","at","to","for","of","and","or","but",
    "why","how","what","when","where","who","my","your","i","did","was","were",
    "got","looks","through","go","get","this","that","have",
}

def _tokenize(query: str) -> str:
    words = re.findall(r"[a-zA-Z0-9]+", query)
    parts, signals = [], []
    for w in words:
        if w.lower() in STOP_WORDS:
            parts.append(f'<span style="color:#475569;text-decoration:line-through;'
                         f'font-size:13px">{w}</span>')
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
            padding:16px 14px 20px;max-width:310px;margin:0 auto;min-height:540px">
  <div style="text-align:center;margin-bottom:10px">
    <div style="background:#2D3D5A;width:70px;height:16px;border-radius:8px;
                display:inline-block"></div>
  </div>
  <div style="background:{header_color};padding:10px 14px;border-radius:14px 14px 0 0;
              text-align:center">
    <span style="color:white;font-weight:700;font-size:15px">&#128154; FinanceCo</span>
    <div style="color:rgba(255,255,255,.8);font-size:10px;margin-top:1px">{label}</div>
  </div>
  <div style="background:#F5F7FA;padding:14px 12px;border-radius:0 0 14px 14px;min-height:450px">
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


# ── Flow diagrams ─────────────────────────────────────────────────────────────
def _flow_q1() -> str:
    return """
<div style="background:#0F172A;border-radius:10px;padding:1.1rem 1.25rem;margin-bottom:.75rem">
  <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.12em;
              color:#60A5FA;margin-bottom:.85rem">How TiDB Finds the Answer</div>

  <div style="text-align:center;margin-bottom:.6rem">
    <div style="display:inline-block;background:#1E293B;border:1px solid #334155;
                border-radius:6px;padding:.35rem .9rem;color:#E2E8F0;font-size:12px">
      &#128221; <em>"Why was my gas pump declined?"</em>
    </div>
  </div>
  <div style="text-align:center;color:#334155;font-size:13px;margin-bottom:.5rem">&#8595; runs two parallel searches</div>

  <div style="display:flex;gap:.75rem;margin-bottom:.55rem">
    <div style="flex:1;background:#1E0D3F;border:1px solid #4C1D95;border-radius:8px;padding:.65rem .85rem">
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:#DDD6FE;letter-spacing:.1em;margin-bottom:.25rem">&#9312; BM25 Full-Text</div>
      <div style="font-size:11px;color:#C4B5FD;font-family:monospace;margin-bottom:.2rem">FTS_MATCH_WORD()</div>
      <div style="font-size:11px;color:#94A3B8;line-height:1.5">
        Scores <b style="color:#DDD6FE">gas</b>, <b style="color:#DDD6FE">pump</b>,
        <b style="color:#DDD6FE">declined</b> by IDF rarity. Rare domain terms float to top.
      </div>
    </div>
    <div style="display:flex;align-items:center;color:#475569;font-size:18px;padding:0 .15rem">+</div>
    <div style="flex:1;background:#0A1F33;border:1px solid #0C4A6E;border-radius:8px;padding:.65rem .85rem">
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:#BAE6FD;letter-spacing:.1em;margin-bottom:.25rem">&#9313; Vector Semantic</div>
      <div style="font-size:11px;color:#7DD3FC;font-family:monospace;margin-bottom:.2rem">VEC_COSINE_DISTANCE()</div>
      <div style="font-size:11px;color:#94A3B8;line-height:1.5">
        Amazon Titan server-side. 1536-dim cosine. No embedding client in your app code.
      </div>
    </div>
  </div>

  <div style="text-align:center;color:#334155;font-size:13px;margin-bottom:.5rem">&#8595; merge rankings</div>

  <div style="background:#071E15;border:1px solid #064E3B;border-radius:8px;padding:.65rem .85rem;margin-bottom:.55rem">
    <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:#A7F3D0;letter-spacing:.1em;margin-bottom:.25rem">&#9314; RRF Fusion (Python-side)</div>
    <div style="font-size:12px;color:#6EE7B7;font-family:monospace">score = 1/(60 + rank_bm25) + 1/(60 + rank_vec)</div>
    <div style="font-size:11px;color:#94A3B8;margin-top:.2rem">Strong in both signals rises to #1. k=60 dampens outliers.</div>
  </div>

  <div style="text-align:center;color:#334155;font-size:13px;margin-bottom:.5rem">&#8595;</div>

  <div style="background:#071A12;border:1px solid #065F46;border-left:3px solid #00C49A;border-radius:8px;padding:.65rem .85rem">
    <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:#34D399;margin-bottom:.2rem">&#10003; Top Result: TKT-BOB-001</div>
    <div style="font-size:11.5px;color:#A7F3D0;line-height:1.5">"Shell Houston TX — Chicago account, no travel alert set"</div>
  </div>
</div>
"""


def _flow_q2_cte() -> str:
    return """
<div style="background:#0F172A;border-radius:10px;padding:1.1rem 1.25rem;margin-bottom:.75rem">
  <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.12em;
              color:#FDE68A;margin-bottom:.85rem">WITH RECURSIVE — How the CTE Walks the Graph</div>

  <div style="display:flex;flex-direction:column;gap:.45rem">

    <div style="display:flex;align-items:flex-start;gap:.7rem">
      <div style="background:#78350F;color:#FDE68A;border-radius:50%;min-width:22px;height:22px;
                  display:flex;align-items:center;justify-content:center;font-size:11px;
                  font-weight:700;margin-top:2px">1</div>
      <div style="background:#1A1200;border:1px solid #78350F;border-radius:8px;padding:.55rem .85rem;flex:1">
        <div style="font-size:11px;font-weight:700;color:#FDE68A;margin-bottom:.2rem">Anchor — Bob's direct transfers</div>
        <div style="font-size:11px;color:#94A3B8;line-height:1.5">
          WHERE from_member_id = 'MBR-BOB-001' at depth=0.<br>
          Returns: Bob&#8594;Sarah ($35) and Bob&#8594;Mike ($200).
        </div>
      </div>
    </div>

    <div style="text-align:center;color:#334155;font-size:13px;padding-left:32px">&#8595; recurse</div>

    <div style="display:flex;align-items:flex-start;gap:.7rem">
      <div style="background:#78350F;color:#FDE68A;border-radius:50%;min-width:22px;height:22px;
                  display:flex;align-items:center;justify-content:center;font-size:11px;
                  font-weight:700;margin-top:2px">2</div>
      <div style="background:#1A1200;border:1px solid #78350F;border-radius:8px;padding:.55rem .85rem;flex:1">
        <div style="font-size:11px;font-weight:700;color:#FDE68A;margin-bottom:.2rem">Recurse — follow each recipient (depth &lt; 3)</div>
        <div style="font-size:11px;color:#94A3B8;line-height:1.5">
          JOIN where e.from_member_id = pc.to_member_id, depth+1.<br>
          depth=1: Mike&#8594;Alex ($180, +28 min)<br>
          depth=2: Alex&#8594;Jordan ($170, +15 min)
        </div>
      </div>
    </div>

    <div style="text-align:center;color:#334155;font-size:13px;padding-left:32px">&#8595; enrich</div>

    <div style="display:flex;align-items:flex-start;gap:.7rem">
      <div style="background:#78350F;color:#FDE68A;border-radius:50%;min-width:22px;height:22px;
                  display:flex;align-items:center;justify-content:center;font-size:11px;
                  font-weight:700;margin-top:2px">3</div>
      <div style="background:#1A1200;border:1px solid #78350F;border-radius:8px;padding:.55rem .85rem;flex:1">
        <div style="font-size:11px;font-weight:700;color:#FDE68A;margin-bottom:.2rem">Enrich — LEFT JOIN fraud_flags at each hop</div>
        <div style="font-size:11px;color:#94A3B8;line-height:1.5">
          Attaches flag_type + confidence_score per transfer_id.<br>
          Surfaces money_mule_pattern (0.97) on the Alex&#8594;Jordan edge.
        </div>
      </div>
    </div>

    <div style="text-align:center;color:#334155;font-size:13px;padding-left:32px">&#8595;</div>

    <div style="background:#071A12;border:1px solid #065F46;border-left:3px solid #F59E0B;
                border-radius:8px;padding:.65rem .85rem;margin-left:32px">
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:#34D399;margin-bottom:.2rem">&#10003; 4-row result — full chain</div>
      <div style="font-size:11px;color:#A7F3D0;font-family:monospace;line-height:1.75">
        depth=0: Bob&#8594;Sarah ($35, normal)<br>
        depth=0: Bob&#8594;Mike ($200, trigger)<br>
        depth=1: Mike&#8594;Alex ($180, &#9888; 0.91)<br>
        depth=2: Alex&#8594;Jordan ($170, &#128680; 0.97)
      </div>
    </div>
  </div>
</div>
"""


def _flow_q3() -> str:
    return """
<div style="background:#0F172A;border-radius:10px;padding:1.1rem 1.25rem;margin-bottom:.75rem">
  <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.12em;
              color:#60A5FA;margin-bottom:.85rem">How TiDB Assembles the Alert</div>

  <div style="display:flex;gap:.75rem;margin-bottom:.55rem">
    <div style="flex:1;background:#1A0A0A;border:1px solid #7F1D1D;border-radius:8px;padding:.65rem .85rem">
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:#FCA5A5;letter-spacing:.1em;margin-bottom:.25rem">&#9312; Relational JOIN</div>
      <div style="font-size:11px;color:#F87171;font-family:monospace;margin-bottom:.2rem">fc_members &#8904; fc_fraud_flags</div>
      <div style="font-size:11px;color:#94A3B8;line-height:1.5">
        2 active flags returned:<br>
        out_of_state: <b style="color:#FCA5A5">0.82</b><br>
        money_mule: <b style="color:#FCA5A5">0.97</b>
      </div>
    </div>
    <div style="display:flex;align-items:center;color:#475569;font-size:18px;padding:0 .15rem">+</div>
    <div style="flex:1;background:#0A1F33;border:1px solid #0C4A6E;border-radius:8px;padding:.65rem .85rem">
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:#BAE6FD;letter-spacing:.1em;margin-bottom:.25rem">&#9313; Hybrid Search</div>
      <div style="font-size:11px;color:#7DD3FC;font-family:monospace;margin-bottom:.2rem">BM25 + Vector on tickets</div>
      <div style="font-size:11px;color:#94A3B8;line-height:1.5">
        "fraud alert unusual activity"<br>
        Pulls prior support history so the AI doesn't repeat itself.
      </div>
    </div>
  </div>

  <div style="text-align:center;color:#334155;font-size:13px;margin-bottom:.5rem">&#8595; combine</div>

  <div style="background:#1A0D00;border:1px solid #92400E;border-left:3px solid #F59E0B;
              border-radius:8px;padding:.65rem .85rem">
    <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:#FDE68A;margin-bottom:.2rem">&#10003; Full Alert Context</div>
    <div style="font-size:11.5px;color:#FEF3C7;line-height:1.5">
      Structured flags (exact scores) + recalled ticket history = precise, non-repetitive summary
    </div>
  </div>
</div>
"""


# ── SQL panel builders ────────────────────────────────────────────────────────
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
{rows if rows else '<div style="font-family:-apple-system,system-ui,sans-serif;color:#475569;font-size:13px;margin:.5rem 0">Live results load on first render.</div>'}
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


# ── Network graph ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def _build_network_graph() -> go.Figure:
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
    for src, dst, label, color, etype in edges:
        x0, y0 = nodes[src][0], nodes[src][1]
        x1, y1 = nodes[dst][0], nodes[dst][1]
        fig.add_trace(go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None], mode="lines",
            line=dict(color=color, width=2 if etype == "normal" else 3,
                      dash="dot" if etype == "normal" else "solid"),
            hoverinfo="skip", showlegend=False,
        ))
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2 + 0.1
        fig.add_annotation(x=mx, y=my, text=f"<b>{label}</b>", showarrow=False,
                           font=dict(size=11, color=color),
                           bgcolor="rgba(255,255,255,0.85)", borderpad=3)
    status_map = {"MBR-BOB-001": "active", "MBR-SAR-002": "active",
                  "MBR-MIK-003": "active", "MBR-ALE-004": "FLAGGED", "MBR-JOR-005": "FROZEN"}
    for mid, (x, y, name, color, size) in nodes.items():
        fig.add_trace(go.Scatter(
            x=[x], y=[y], mode="markers+text",
            marker=dict(size=size, color=color, line=dict(color="white", width=2)),
            text=[name], textposition="top center",
            textfont=dict(size=11, color="#0F172A"),
            hovertext=[f"<b>{name}</b><br>{mid}<br>Status: {status_map[mid]}"],
            hoverinfo="text", showlegend=False,
        ))
    fig.update_layout(
        title=dict(text="Pay Friends Network - Fraud Chain", font=dict(size=14, color="#0F172A"), x=0.5),
        xaxis=dict(visible=False, range=[-1.3, 3.6]),
        yaxis=dict(visible=False, range=[-0.6, 1.4]),
        plot_bgcolor="#F8FAFC", paper_bgcolor="#F8FAFC",
        margin=dict(l=20, r=20, t=45, b=20), height=270,
        annotations=[
            dict(x=3.0, y=-0.4, text="&#128274; Frozen<br>Zero history",
                 showarrow=True, arrowhead=2, ax=0, ay=-28,
                 font=dict(size=10, color="#DC2626"),
                 bgcolor="rgba(254,226,226,0.9)", borderpad=4, bordercolor="#EF4444"),
            dict(x=2.1, y=-0.35, text="&#128680; 97% fraud",
                 showarrow=True, arrowhead=2, ax=10, ay=-22,
                 font=dict(size=10, color="#EF4444"),
                 bgcolor="rgba(254,226,226,0.9)", borderpad=4, bordercolor="#F59E0B"),
        ],
    )
    return fig


# ── Cached data loaders ───────────────────────────────────────────────────────
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


# ── Shared sub-components ─────────────────────────────────────────────────────
def _render_stat_cards(keys: list):
    defs = {
        "support_tickets": ("Support Tickets", "#7C3AED", "#F5F3FF"),
        "embeddings":      ("Vector Embeddings", "#0891B2", "#ECFEFF"),
        "fraud_flags":     ("Fraud Flags", "#DC2626", "#FEF2F2"),
        "pay_friends_edges": ("Pay Friends Edges", "#D97706", "#FFFBEB"),
        "members":         ("Members", "#0369A1", "#EFF6FF"),
        "transactions":    ("Transactions", "#059669", "#F0FDF4"),
    }
    try:
        stats = _get_stats()
        cols = st.columns(len(keys), gap="small")
        for col, k in zip(cols, keys):
            label, color, bg = defs[k]
            with col:
                st.markdown(
                    f'<div style="background:{bg};border:1px solid {color}33;border-radius:8px;'
                    f'padding:.75rem 1rem;text-align:center">'
                    f'<div style="font-size:1.75rem;font-weight:800;color:{color}">{stats.get(k,0)}</div>'
                    f'<div style="font-size:10px;text-transform:uppercase;letter-spacing:.08em;'
                    f'color:{color};margin-top:.15rem">{label}</div></div>',
                    unsafe_allow_html=True)
    except Exception:
        pass


def _render_index_cards():
    try:
        indexes = _get_indexes()
        vec_ok = any(i.get("Index_type") == "HNSW" or i.get("Key_name", "").startswith("vec")
                     for i in indexes)
        fts_ok = any(i.get("Index_type") == "FULLTEXT" for i in indexes)
        ic1, ic2 = st.columns(2, gap="small")
        with ic1:
            st.markdown(
                f'<div style="background:#F5F3FF;border:1px solid #7C3AED44;border-radius:8px;padding:.65rem .9rem">'
                f'<div style="font-size:11px;font-weight:700;color:#7C3AED">HNSW Vector Index</div>'
                f'<div style="font-size:1.1rem;font-weight:800;color:#7C3AED;margin:.15rem 0">{"&#10003; Active" if vec_ok else "&#10007; None"}</div>'
                f'<div style="font-size:11px;color:#64748B">content_vec — 1536-dim cosine, HNSW graph</div></div>',
                unsafe_allow_html=True)
        with ic2:
            st.markdown(
                f'<div style="background:#F0FDF4;border:1px solid #05996944;border-radius:8px;padding:.65rem .9rem">'
                f'<div style="font-size:11px;font-weight:700;color:#059669">BM25 Full-Text Index</div>'
                f'<div style="font-size:1.1rem;font-weight:800;color:#059669;margin:.15rem 0">{"&#10003; Active" if fts_ok else "&#10007; None"}</div>'
                f'<div style="font-size:11px;color:#64748B">content — MULTILINGUAL parser, inverted index</div></div>',
                unsafe_allow_html=True)
    except Exception:
        pass


def _phone_labels():
    lc, rc = st.columns(2)
    with lc:
        st.markdown('<div style="text-align:center;font-size:11px;font-weight:700;'
                    'text-transform:uppercase;letter-spacing:.1em;color:#94A3B8;'
                    'margin-bottom:.5rem">Without Memory</div>', unsafe_allow_html=True)
    with rc:
        st.markdown('<div style="text-align:center;font-size:11px;font-weight:700;'
                    'text-transform:uppercase;letter-spacing:.1em;color:#00C49A;'
                    'margin-bottom:.5rem">With TiDB Memory</div>', unsafe_allow_html=True)


def _build_snippets(results: list, fallback_key: int) -> list:
    if results:
        return [
            f"{r.get('ticket_id','?')} - {str(r.get('content',''))[:55]}... "
            f"(score {float(r.get('_score') or r.get('_distance') or 0):.3f})"
            for r in results[:2]
        ]
    return MEM_SNIPPETS[fallback_key]


# ── Load all scenario results once ───────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner="Querying TiDB memory...")
def _load_all_results() -> dict:
    out = {}
    for num, query in QUESTIONS.items():
        try:
            out[num] = recall_support("MBR-BOB-001", query, limit=4)
        except Exception:
            out[num] = []
    return out

_data = _load_all_results()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="padding:1rem 0 .25rem;display:flex;align-items:center;justify-content:space-between">
  <div>
    <span style="font-size:22px;font-weight:800;color:#00C49A">FinanceCo</span>
    <span style="font-size:16px;color:#64748B;margin-left:.6rem">AI Member Support Demo</span>
    <span style="font-size:12px;color:#94A3B8;margin-left:1rem">
      Powered by TiDB Cloud &nbsp;&#8226;&nbsp; Hybrid Search + Graph Traversal
    </span>
  </div>
  <div style="font-size:12px;background:#F0FDF4;color:#059669;padding:4px 12px;
              border-radius:12px;border:1px solid #BBF7D0">
    Bob Johnson &nbsp;&#8226;&nbsp; MBR-BOB-001 &nbsp;&#8226;&nbsp; Chicago, IL
  </div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    "  &#x26FD;  Scenario 1 — Gas Pump Declined  ",
    "  &#x26A0;&#xFE0F;  Scenario 2 — Pay Friends Fraud  ",
    "  &#x1F514;  Scenario 3 — Fraud Alert  ",
])


# ══════════════════════════════════════════════════════════════════════════════
# SCENARIO 1 — Hybrid Search (BM25 + Vector + RRF)
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    s1 = _data.get(1, [])
    s1_snippets = _build_snippets(s1, 1)

    st.markdown("""
    <div style="background:linear-gradient(135deg,#022C22 0%,#064E3B 100%);
                border-radius:12px;padding:1.1rem 1.75rem;margin-bottom:1rem">
      <div style="font-size:10px;letter-spacing:.15em;color:#34D399;text-transform:uppercase;
                  font-weight:700;margin-bottom:.3rem">
        Scenario 1 of 3 &nbsp;&#8226;&nbsp; Hybrid Search (BM25 + Vector + RRF)
      </div>
      <div style="font-size:1.4rem;font-weight:800;color:#ECFDF5">
        &#x26FD; "Why was my gas pump declined?"
      </div>
      <div style="font-size:13px;color:#A7F3D0;margin-top:.4rem;max-width:960px;line-height:1.65">
        Bob's Shell charge was blocked in Houston TX — his account is Chicago IL-based with no travel alert.
        Without memory: generic troubleshooting. With TiDB: hybrid search pinpoints the exact prior
        incident record in milliseconds. BM25 catches the domain keywords. Vector catches the semantic meaning.
        RRF merges both into a single ranked result.
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_ph, col_rt = st.columns([5, 7], gap="medium")

    with col_ph:
        _phone_labels()
        pl, pr = st.columns(2, gap="small")
        with pl:
            st.html(_phone_frame("No context", QUESTIONS[1], WITHOUT_MEM[1], header_color="#64748B"))
        with pr:
            st.html(_phone_frame("TiDB-powered", QUESTIONS[1], WITH_MEM[1], mem_snippets=s1_snippets))

    with col_rt:
        st.html(_flow_q1())
        st.markdown(f'<div class="sql-panel">{_sql_q1(QUESTIONS[1], s1)}</div>',
                    unsafe_allow_html=True)

    st.markdown("<div style='height:1.25rem'></div>", unsafe_allow_html=True)
    st.markdown('<div style="font-size:11px;font-weight:700;text-transform:uppercase;'
                'letter-spacing:.1em;color:#7C3AED;margin-bottom:.6rem">'
                'Memory Layer</div>', unsafe_allow_html=True)
    _render_stat_cards(["support_tickets", "embeddings", "members", "transactions"])
    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
    _render_index_cards()
    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
    try:
        import pandas as pd
        tickets = _get_tickets()
        if tickets:
            df = pd.DataFrame(tickets)
            st.dataframe(
                df[["ticket_id", "member_id", "vec_dims", "snippet", "created_at"]],
                use_container_width=True, hide_index=True,
                column_config={
                    "ticket_id": "Ticket ID", "member_id": "Member",
                    "vec_dims": st.column_config.NumberColumn("Vec Dims", format="%d"),
                    "snippet": "Content Preview", "created_at": "Created",
                },
            )
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# SCENARIO 2 — Recursive CTE + Hybrid Search
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    s2 = _data.get(2, [])
    s2_snippets = _build_snippets(s2, 2)

    st.markdown("""
    <div style="background:linear-gradient(135deg,#2D0808 0%,#7F1D1D 100%);
                border-radius:12px;padding:1.1rem 1.75rem;margin-bottom:1rem">
      <div style="font-size:10px;letter-spacing:.15em;color:#FCA5A5;text-transform:uppercase;
                  font-weight:700;margin-bottom:.3rem">
        Scenario 2 of 3 &nbsp;&#8226;&nbsp; Recursive CTE Graph Traversal + Hybrid Search
      </div>
      <div style="font-size:1.4rem;font-weight:800;color:#FEF2F2">
        &#x26A0;&#xFE0F; "Did my Pay Friends transfer go through? It looks suspicious."
      </div>
      <div style="font-size:13px;color:#FECACA;margin-top:.4rem;max-width:960px;line-height:1.65">
        Bob sent $200 to Mike. That triggered a 3-hop forwarding chain ending at a frozen account.
        No graph database needed &mdash; a single <code style="background:rgba(0,0,0,.35);
        padding:1px 6px;border-radius:4px;color:#FDE68A">WITH RECURSIVE</code> CTE walks
        Bob&rarr;Mike&rarr;Alex&rarr;Jordan and attaches fraud flags at each hop. Standard SQL.
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_ph, col_rt = st.columns([5, 7], gap="medium")

    with col_ph:
        _phone_labels()
        pl, pr = st.columns(2, gap="small")
        with pl:
            st.html(_phone_frame("No context", QUESTIONS[2], WITHOUT_MEM[2], header_color="#64748B"))
        with pr:
            st.html(_phone_frame("TiDB-powered", QUESTIONS[2], WITH_MEM[2], mem_snippets=s2_snippets))

    with col_rt:
        st.plotly_chart(_build_network_graph(), use_container_width=True)
        st.html(_flow_q2_cte())
        st.markdown(f'<div class="sql-panel">{_sql_q2()}</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:1.25rem'></div>", unsafe_allow_html=True)
    st.markdown('<div style="font-size:11px;font-weight:700;text-transform:uppercase;'
                'letter-spacing:.1em;color:#DC2626;margin-bottom:.6rem">'
                'Graph + Fraud Data</div>', unsafe_allow_html=True)
    _render_stat_cards(["pay_friends_edges", "fraud_flags", "members", "transactions"])
    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
    try:
        import pandas as pd
        flags = _get_fraud()
        if flags:
            df = pd.DataFrame(flags)
            st.dataframe(
                df[["member_name", "flag_type", "confidence_score", "description",
                    "resolved", "created_at"]],
                use_container_width=True, hide_index=True,
                column_config={
                    "member_name": "Member", "flag_type": "Flag Type",
                    "confidence_score": st.column_config.NumberColumn("Confidence", format="%.2f"),
                    "description": "Description", "resolved": "Resolved",
                    "created_at": "Flagged At",
                },
            )
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# SCENARIO 3 — Relational JOIN + Hybrid Search
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    s3 = _data.get(3, [])
    s3_snippets = _build_snippets(s3, 3)

    st.markdown("""
    <div style="background:linear-gradient(135deg,#1A0D00 0%,#78350F 100%);
                border-radius:12px;padding:1.1rem 1.75rem;margin-bottom:1rem">
      <div style="font-size:10px;letter-spacing:.15em;color:#FDE68A;text-transform:uppercase;
                  font-weight:700;margin-bottom:.3rem">
        Scenario 3 of 3 &nbsp;&#8226;&nbsp; Relational JOIN + Hybrid Search
      </div>
      <div style="font-size:1.4rem;font-weight:800;color:#FFFBEB">
        &#x1F514; "I got a fraud notification. What happened?"
      </div>
      <div style="font-size:13px;color:#FEF3C7;margin-top:.4rem;max-width:960px;line-height:1.65">
        Bob has 2 active flags. TiDB runs a relational JOIN on fc_fraud_flags for exact confidence
        scores, while simultaneously hybrid-searching his support ticket history so the AI
        doesn't repeat what was already explained. All from one cluster, one connection string.
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_ph, col_rt = st.columns([5, 7], gap="medium")

    with col_ph:
        _phone_labels()
        pl, pr = st.columns(2, gap="small")
        with pl:
            st.html(_phone_frame("No context", QUESTIONS[3], WITHOUT_MEM[3], header_color="#64748B"))
        with pr:
            st.html(_phone_frame("TiDB-powered", QUESTIONS[3], WITH_MEM[3], mem_snippets=s3_snippets))

    with col_rt:
        st.html(_flow_q3())
        st.markdown(f'<div class="sql-panel">{_sql_q3()}</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:1.25rem'></div>", unsafe_allow_html=True)
    st.markdown('<div style="font-size:11px;font-weight:700;text-transform:uppercase;'
                'letter-spacing:.1em;color:#D97706;margin-bottom:.6rem">'
                'Fraud Data + Incident History</div>', unsafe_allow_html=True)
    _render_stat_cards(["fraud_flags", "support_tickets", "embeddings", "members"])
    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
    _render_index_cards()
    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
    try:
        import pandas as pd
        txns = _get_transactions()
        if txns:
            df = pd.DataFrame(txns)
            st.dataframe(
                df[["transaction_id", "merchant_name", "merchant_category",
                    "amount", "status", "created_at"]],
                use_container_width=True, hide_index=True,
                column_config={
                    "transaction_id": "Txn ID", "merchant_name": "Merchant",
                    "merchant_category": "Category",
                    "amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
                    "status": "Status", "created_at": "Date",
                },
            )
    except Exception:
        pass
