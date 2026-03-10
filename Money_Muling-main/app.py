print("NEW MULTI-FACTOR ENGINE LOADED")
from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import networkx as nx
import json
import io
import time
import numpy as np
from datetime import timedelta

app = Flask(__name__)

analysis_result = {}

@app.route('/')
def home():
    return render_template("index.html")


@app.route('/upload', methods=['POST'])
def upload():
    global analysis_result

    start_time = time.time()

    file = request.files['file']
    df = pd.read_csv(file)

    # Convert timestamp
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # =========================
    # Build Directed Graph
    # =========================
    G = nx.DiGraph()

    for _, row in df.iterrows():
        G.add_edge(row['sender_id'], row['receiver_id'])

    suspicious_accounts = []
    fraud_rings = []
    ring_counter = 1

    # =========================
    # 1️⃣ Cycle Detection (3–5)
    # =========================
    cycles = list(nx.simple_cycles(G))
    cycle_nodes = set()

    for cycle in cycles:
        if 3 <= len(cycle) <= 5:
            ring_id = f"RING_{ring_counter:03d}"
            ring_counter += 1

            fraud_rings.append({
                "ring_id": ring_id,
                "member_accounts": cycle,
                "pattern_type": "cycle",
                "risk_score": 95.0
            })

            for node in cycle:
                cycle_nodes.add(node)

    # =========================
    # Pre-group for Performance
    # =========================
    in_group = df.groupby('receiver_id')
    out_group = df.groupby('sender_id')

    scores = {}

    # =========================
    # 2️⃣ Multi-Factor Scoring
    # =========================
    for node in G.nodes():

        score = 0
        patterns = []

        in_tx = in_group.get_group(node) if node in in_group.groups else pd.DataFrame()
        out_tx = out_group.get_group(node) if node in out_group.groups else pd.DataFrame()

        total_in = in_tx['amount'].sum() if not in_tx.empty else 0
        total_out = out_tx['amount'].sum() if not out_tx.empty else 0

        # ---- A. Cycle Participation ----
        if node in cycle_nodes:
            score += 40
            patterns.append("cycle_participation")

        # ---- B. Rapid Relay Detection ----
        if not in_tx.empty and not out_tx.empty:
            first_in = in_tx['timestamp'].min()
            first_out = out_tx['timestamp'].min()

            if first_out > first_in:
                delta_hours = (first_out - first_in).total_seconds() / 3600
                if delta_hours <= 6:
                    score += 25
                    patterns.append("rapid_relay")

        # ---- C. Smurfing (Low Variance Deposits) ----
        if len(in_tx) >= 5:
            variance = in_tx['amount'].var()
            if variance is not None and variance < 50:
                score += 15
                patterns.append("low_amount_variance")

        # ---- D. High Forward Ratio (Layering) ----
        if total_in > 0:
            ratio = total_out / total_in
            if 0.8 <= ratio <= 1.2:
                score += 20
                patterns.append("high_forward_ratio")

        # ---- E. Short Burst Activity ----
        if len(in_tx) >= 5:
            span_hours = (
                (in_tx['timestamp'].max() - in_tx['timestamp'].min())
                .total_seconds() / 3600
            )
            if span_hours <= 24:
                score += 15
                patterns.append("short_activity_burst")

        # =========================
        # Merchant / Payroll Protection
        # =========================
        if len(in_tx) >= 10:

            variance = in_tx['amount'].var()
            span_days = (
                (in_tx['timestamp'].max() - in_tx['timestamp'].min())
                .total_seconds() / (3600 * 24)
            )

            # Legit merchant characteristics:
            # - High variance
            # - Long stable span
            # - No rapid relay
            # - Not part of cycle
            if (
                variance is not None and variance > 500
                and span_days >= 5
                and "rapid_relay" not in patterns
                and node not in cycle_nodes
            ):
                score -= 30
                patterns.append("merchant_protection")

        # Clamp score
        score = max(0, min(score, 100))
        scores[node] = (score, patterns)

    # =========================
    # 3️⃣ Layered Shell Detection
    # =========================
    for node in G.nodes():
        if G.degree(node) <= 2:
            successors = list(G.successors(node))
            if len(successors) == 1:
                next_node = successors[0]
                if G.degree(next_node) <= 2:
                    score, patterns = scores[node]
                    score += 20
                    patterns.append("shell_layer_node")
                    scores[node] = (min(score, 100), patterns)

    # =========================
    # 4️⃣ Final Suspicious Accounts
    # =========================
    for node, (score, patterns) in scores.items():
        if score >= 70:
            suspicious_accounts.append({
                "account_id": node,
                "suspicion_score": float(score),
                "detected_patterns": patterns,
                "ring_id": "MULTI_FACTOR"
            })

    suspicious_accounts = sorted(
        suspicious_accounts,
        key=lambda x: x["suspicion_score"],
        reverse=True
    )

    processing_time = round(time.time() - start_time, 2)

    analysis_result = {
        "suspicious_accounts": suspicious_accounts,
        "fraud_rings": fraud_rings,
        "summary": {
            "total_accounts_analyzed": len(G.nodes()),
            "suspicious_accounts_flagged": len(suspicious_accounts),
            "fraud_rings_detected": len(fraud_rings),
            "processing_time_seconds": processing_time
        }
    }

    suspicious_ids = {a["account_id"] for a in suspicious_accounts}

    graph_data = {
        "nodes": [
            {
                "id": n,
                "label": n,
                "color": "red" if n in suspicious_ids else "#3498db"
            }
            for n in G.nodes()
        ],
        "edges": [{"from": u, "to": v} for u, v in G.edges()]
    }

    return jsonify({
        "analysis": analysis_result,
        "graph": graph_data
    })


@app.route('/download')
def download():
    global analysis_result

    if not analysis_result:
        return "No data available"

    json_data = json.dumps(analysis_result, indent=4)

    buffer = io.BytesIO()
    buffer.write(json_data.encode())
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="fraud_detection_output.json",
        mimetype="application/json"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)