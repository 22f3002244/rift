import networkx as nx
import pandas as pd
from collections import defaultdict
import time


def build_graph(df: pd.DataFrame):
    G = nx.DiGraph()
    for _, row in df.iterrows():
        s, r, amt, ts = row['sender_id'], row['receiver_id'], row['amount'], row['timestamp']
        if G.has_edge(s, r):
            G[s][r]['amount'] += amt
            G[s][r]['count'] += 1
            G[s][r]['timestamps'].append(ts)
        else:
            G.add_edge(s, r, amount=amt, count=1, timestamps=[ts])
    return G


def detect_cycles(G: nx.DiGraph):
    rings = []
    ring_counter = 1
    seen_cycles = set()

    try:
        sccs = list(nx.strongly_connected_components(G))

        for scc in sccs:
            if len(scc) < 3:
                continue

            subgraph = G.subgraph(scc)

            cycle_gen = nx.simple_cycles(subgraph)

            cycles_found_in_scc = 0
            MAX_CYCLES_PER_SCC = 500

            for cycle in cycle_gen:
                if cycles_found_in_scc >= MAX_CYCLES_PER_SCC:
                    break

                length = len(cycle)
                if 3 <= length <= 5:
                    key = frozenset(cycle)
                    if key in seen_cycles:
                        continue
                    seen_cycles.add(key)
                    cycles_found_in_scc += 1

                    total_amount = sum(
                        G[cycle[i]][cycle[(i+1) % length]].get('amount', 0)
                        for i in range(length)
                    )
                    risk_score = min(100, 60 + (5 - length) * 5 + min(total_amount / 10000, 20))

                    rings.append({
                        'ring_id': f'RING_{ring_counter:03d}',
                        'pattern_type': f'cycle_length_{length}',
                        'member_accounts': cycle,
                        'risk_score': round(risk_score, 2)
                    })
                    ring_counter += 1

    except Exception:
        return rings

    return rings


def detect_smurfing(G: nx.DiGraph, df: pd.DataFrame, fan_threshold=10, time_window_hours=72):
    rings = []
    ring_counter = 1

    for node in G.nodes():
        predecessors = list(G.predecessors(node))
        if len(predecessors) >= fan_threshold:
            timestamps = []
            for pred in predecessors:
                timestamps.extend(G[pred][node].get('timestamps', []))

            if timestamps:
                timestamps.sort()
                window_count = 0
                for i in range(len(timestamps)):
                    for j in range(i+1, len(timestamps)):
                        try:
                            diff = abs((timestamps[j] - timestamps[i]).total_seconds() / 3600)
                            if diff <= time_window_hours:
                                window_count += 1
                        except Exception:
                            pass

                temporal_boost = min(20, window_count * 2)
            else:
                temporal_boost = 0

            risk_score = min(100, 55 + len(predecessors) * 2 + temporal_boost)
            members = predecessors + [node]

            rings.append({
                'ring_id': f'SMURF_{ring_counter:03d}',
                'pattern_type': 'smurfing_fan_in',
                'member_accounts': members,
                'risk_score': round(risk_score, 2)
            })
            ring_counter += 1

    for node in G.nodes():
        successors = list(G.successors(node))
        if len(successors) >= fan_threshold:
            risk_score = min(100, 55 + len(successors) * 2)
            members = [node] + successors

            rings.append({
                'ring_id': f'SMURF_{ring_counter:03d}',
                'pattern_type': 'smurfing_fan_out',
                'member_accounts': members,
                'risk_score': round(risk_score, 2)
            })
            ring_counter += 1

    return rings


def detect_shell_chains(G: nx.DiGraph, min_hops=3, max_tx_count=3):
    rings = []
    ring_counter = 1
    seen_chains = set()

    node_tx_count = defaultdict(int)
    for u, v, data in G.edges(data=True):
        node_tx_count[u] += data.get('count', 1)
        node_tx_count[v] += data.get('count', 1)

    shell_nodes = {n for n, cnt in node_tx_count.items() if cnt <= max_tx_count}

    for source in G.nodes():
        if source in shell_nodes:
            continue

        def dfs(current, path, depth):
            if depth > min_hops + 2:
                return
            for neighbor in G.successors(current):
                if neighbor in path:
                    continue
                new_path = path + [neighbor]
                if neighbor in shell_nodes and depth >= min_hops - 1:
                    chain_key = tuple(new_path)
                    if chain_key not in seen_chains and len(new_path) >= min_hops:
                        seen_chains.add(chain_key)
                        risk_score = min(100, 50 + len(new_path) * 5)
                        rings.append({
                            'ring_id': f'SHELL_{ring_counter:03d}',
                            'pattern_type': 'shell_chain',
                            'member_accounts': new_path,
                            'risk_score': round(risk_score, 2)
                        })
                if neighbor in shell_nodes:
                    dfs(neighbor, new_path, depth + 1)

        dfs(source, [source], 1)

    return rings[:50]


def calculate_suspicion_scores(fraud_rings, all_accounts):
    account_patterns = defaultdict(list)
    account_rings = defaultdict(str)
    account_scores = defaultdict(float)

    for ring in fraud_rings:
        for acc in ring['member_accounts']:
            account_patterns[acc].append(ring['pattern_type'])
            account_rings[acc] = ring['ring_id']
            account_scores[acc] = min(100, account_scores[acc] + ring['risk_score'] * 0.6)

    suspicious = []
    for acc, score in account_scores.items():
        if score > 0:
            suspicious.append({
                'account_id': acc,
                'suspicion_score': round(score, 2),
                'detected_patterns': list(set(account_patterns[acc])),
                'ring_id': account_rings[acc]
            })

    suspicious.sort(key=lambda x: x['suspicion_score'], reverse=True)
    return suspicious


def run_detection(df: pd.DataFrame):
    """Main detection pipeline — returns fraud_rings and suspicious_accounts"""
    start = time.time()

    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df = df.dropna(subset=['sender_id', 'receiver_id'])

    G = build_graph(df)
    all_accounts = list(G.nodes())

    cycle_rings = detect_cycles(G)
    smurf_rings = detect_smurfing(G, df)
    shell_rings = detect_shell_chains(G)

    all_rings = cycle_rings + smurf_rings + shell_rings

    suspicious_accounts = calculate_suspicion_scores(all_rings, all_accounts)

    elapsed = round(time.time() - start, 2)

    nodes = []
    suspicious_ids = {a['account_id'] for a in suspicious_accounts}
    ring_member_map = {}
    for ring in all_rings:
        for acc in ring['member_accounts']:
            ring_member_map[acc] = ring['pattern_type']

    for acc in all_accounts:
        nodes.append({
            'id': acc,
            'suspicious': acc in suspicious_ids,
            'pattern': ring_member_map.get(acc, 'normal'),
            'tx_count': G.degree(acc)
        })

    edges = []
    for u, v, data in G.edges(data=True):
        edges.append({
            'source': u,
            'target': v,
            'amount': data.get('amount', 0),
            'count': data.get('count', 1),
            'suspicious': u in suspicious_ids or v in suspicious_ids
        })

    return {
        'fraud_rings': all_rings,
        'suspicious_accounts': suspicious_accounts,
        'graph': {'nodes': nodes, 'edges': edges},
        'summary': {
            'total_accounts_analyzed': len(all_accounts),
            'suspicious_accounts_flagged': len(suspicious_accounts),
            'fraud_rings_detected': len(all_rings),
            'processing_time_seconds': elapsed
        }
    }
