import os
from groq import Groq

client = None

def get_client():
    global client
    if client is None:
        api_key = os.environ.get('GROQ_API_KEY')
        if api_key:
            client = Groq(api_key=api_key)
    return client


def explain_suspicious_account(account_id, suspicion_score, detected_patterns, ring_id):
    groq = get_client()
    if not groq:
        return "AI explanation unavailable — Groq API key not configured."

    pattern_descriptions = {
        'cycle_length_3': 'a 3-hop circular fund routing (A→B→C→A)',
        'cycle_length_4': 'a 4-hop circular fund routing cycle',
        'cycle_length_5': 'a 5-hop circular fund routing cycle',
        'smurfing_fan_in': 'structuring/smurfing (many small deposits aggregated)',
        'smurfing_fan_out': 'rapid fund dispersal (fan-out to many receivers)',
        'shell_chain': 'layered shell network (money through low-activity shell accounts)',
    }

    pattern_text = ', '.join([pattern_descriptions.get(p, p) for p in detected_patterns])

    prompt = f"""You are a financial forensics expert analyzing a suspicious bank account flagged by an automated money laundering detection system.

Account ID: {account_id}
Suspicion Score: {suspicion_score}/100
Detected Patterns: {pattern_text}
Associated Ring: {ring_id}

Write a concise 2-3 sentence forensic analyst note explaining:
1. Why this account is suspicious based on the patterns
2. What money laundering technique this likely represents
3. What investigators should look for next

Keep it professional, factual, and under 80 words."""

    try:
        response = groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"AI analysis error: {str(e)}"


def generate_investigation_summary(summary_stats, top_rings):
    groq = get_client()
    if not groq:
        return "AI summary unavailable — configure GROQ_API_KEY in .env"

    rings_text = '\n'.join([
        f"- {r['ring_id']}: {r['pattern_type']} with {len(r['member_accounts'])} members, risk score {r['risk_score']}"
        for r in top_rings[:5]
    ])

    prompt = f"""You are a senior financial crimes investigator. Summarize the following automated money muling detection results for an executive report.

Statistics:
- Total accounts analyzed: {summary_stats['total_accounts_analyzed']}
- Suspicious accounts flagged: {summary_stats['suspicious_accounts_flagged']}
- Fraud rings detected: {summary_stats['fraud_rings_detected']}
- Processing time: {summary_stats['processing_time_seconds']}s

Top detected fraud rings:
{rings_text}

Write a 3-4 sentence executive summary covering: overall risk level, primary patterns found, and recommended immediate actions. Keep it professional and under 100 words."""

    try:
        response = groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"AI summary error: {str(e)}"


def chat_with_data(user_question, context_summary):
    groq = get_client()
    if not groq:
        return "AI chat unavailable — configure GROQ_API_KEY in .env"

    prompt = f"""You are a financial forensics AI assistant. Answer questions about a money muling investigation dataset.

Dataset Context:
{context_summary}

Investigator Question: {user_question}

Answer concisely and factually based only on the provided context. If the answer isn't in the context, say so."""

    try:
        response = groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {str(e)}"
