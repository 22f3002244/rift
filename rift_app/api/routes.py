"""API routes for the FinForensics application."""

import os
import json
import io
from datetime import datetime
import pandas as pd
from flask import Blueprint, render_template, request, jsonify, send_file, redirect, url_for, flash, make_response, current_app

from rift_app.models import db, UploadSession, Transaction, FraudRing, SuspiciousAccount
from rift_app.services.detection import run_detection
from rift_app.services.ai import explain_suspicious_account, generate_investigation_summary, chat_with_data
from rift_app.services.reporting import generate_pdf_report

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    sessions = UploadSession.query.order_by(UploadSession.upload_time.desc()).limit(10).all()
    return render_template('index.html', sessions=sessions)


@main_bp.route('/upload', methods=['POST'])
def upload_csv():
    if 'csv_file' not in request.files:
        flash('No file selected', 'danger')
        return redirect(url_for('main.index'))

    file = request.files['csv_file']
    if file.filename == '' or not file.filename.endswith('.csv'):
        flash('Please upload a valid CSV file', 'danger')
        return redirect(url_for('main.index'))

    try:
        df = pd.read_csv(file)

        required = ['transaction_id', 'sender_id', 'receiver_id', 'amount', 'timestamp']
        missing = [col for col in required if col not in df.columns]
        if missing:
            flash(f'Missing columns: {", ".join(missing)}', 'danger')
            return redirect(url_for('main.index'))

        session = UploadSession(
            filename=file.filename,
            total_transactions=len(df),
            status='processing'
        )
        db.session.add(session)
        db.session.commit()

        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        transactions = []
        for _, row in df.iterrows():
            tx = Transaction(
                session_id=session.id,
                transaction_id=str(row.get('transaction_id', '')),
                sender_id=str(row['sender_id']),
                receiver_id=str(row['receiver_id']),
                amount=float(row.get('amount', 0)),
                timestamp=row['timestamp'] if pd.notna(row['timestamp']) else None
            )
            transactions.append(tx)
        db.session.bulk_save_objects(transactions)
        db.session.commit()

        results = run_detection(df)

        rings_to_save = []
        for ring_data in results['fraud_rings']:
            ring = FraudRing(
                session_id=session.id,
                ring_id=ring_data['ring_id'],
                pattern_type=ring_data['pattern_type'],
                risk_score=ring_data['risk_score'],
            )
            ring.member_accounts = ring_data['member_accounts']
            rings_to_save.append(ring)
        db.session.bulk_save_objects(rings_to_save)

        accounts_to_save = []
        for i, acc_data in enumerate(results['suspicious_accounts']):
            ai_note = None
            if i < 20:
                ai_note = explain_suspicious_account(
                    acc_data['account_id'],
                    acc_data['suspicion_score'],
                    acc_data['detected_patterns'],
                    acc_data['ring_id']
                )
            acc = SuspiciousAccount(
                session_id=session.id,
                account_id=acc_data['account_id'],
                suspicion_score=acc_data['suspicion_score'],
                ring_id=acc_data['ring_id'],
                ai_explanation=ai_note
            )
            acc.detected_patterns = acc_data['detected_patterns']
            accounts_to_save.append(acc)
        db.session.bulk_save_objects(accounts_to_save)

        session.total_accounts = results['summary']['total_accounts_analyzed']
        session.processing_time = results['summary']['processing_time_seconds']
        session.status = 'done'
        db.session.commit()

        ai_summary = generate_investigation_summary(
            results['summary'],
            results['fraud_rings'][:5]
        )

        return redirect(url_for('main.results', session_id=session.id, ai_summary=ai_summary))

    except Exception as e:
        flash(f'Processing error: {str(e)}', 'danger')
        return redirect(url_for('main.index'))


@main_bp.route('/results/<int:session_id>')
def results(session_id):
    session = UploadSession.query.get_or_404(session_id)
    fraud_rings = FraudRing.query.filter_by(session_id=session_id).order_by(FraudRing.risk_score.desc()).all()
    suspicious_accounts = SuspiciousAccount.query.filter_by(session_id=session_id)\
        .order_by(SuspiciousAccount.suspicion_score.desc()).all()

    ai_summary = request.args.get('ai_summary', '')

    transactions = Transaction.query.filter_by(session_id=session_id).all()
    suspicious_ids = {a.account_id for a in suspicious_accounts}
    ring_member_map = {}
    for ring in fraud_rings:
        for acc in ring.member_accounts:
            ring_member_map[acc] = ring.pattern_type

    nodes_set = set()
    for tx in transactions:
        nodes_set.add(tx.sender_id)
        nodes_set.add(tx.receiver_id)

    graph_nodes = [{'id': n, 'suspicious': n in suspicious_ids,
                    'pattern': ring_member_map.get(n, 'normal')} for n in nodes_set]

    edge_map = {}
    for tx in transactions:
        key = (tx.sender_id, tx.receiver_id)
        if key not in edge_map:
            edge_map[key] = {'source': tx.sender_id, 'target': tx.receiver_id, 'amount': 0, 'count': 0,
                             'suspicious': tx.sender_id in suspicious_ids or tx.receiver_id in suspicious_ids}
        edge_map[key]['amount'] += tx.amount or 0
        edge_map[key]['count'] += 1

    graph_data = {
        'nodes': graph_nodes,
        'edges': list(edge_map.values())
    }

    return render_template('results.html',
                           session=session,
                           fraud_rings=fraud_rings,
                           suspicious_accounts=suspicious_accounts,
                           ai_summary=ai_summary,
                           graph_data=json.dumps(graph_data))


@main_bp.route('/api/download-json/<int:session_id>')
def download_json(session_id):
    session = UploadSession.query.get_or_404(session_id)
    fraud_rings = FraudRing.query.filter_by(session_id=session_id).order_by(FraudRing.risk_score.desc()).all()
    suspicious_accounts = SuspiciousAccount.query.filter_by(session_id=session_id)\
        .order_by(SuspiciousAccount.suspicion_score.desc()).all()

    output = {
        'suspicious_accounts': [
            {
                'account_id': a.account_id,
                'suspicion_score': a.suspicion_score,
                'detected_patterns': a.detected_patterns,
                'ring_id': a.ring_id
            } for a in suspicious_accounts
        ],
        'fraud_rings': [
            {
                'ring_id': r.ring_id,
                'member_accounts': r.member_accounts,
                'pattern_type': r.pattern_type,
                'risk_score': r.risk_score
            } for r in fraud_rings
        ],
        'summary': {
            'total_accounts_analyzed': session.total_accounts,
            'suspicious_accounts_flagged': len(suspicious_accounts),
            'fraud_rings_detected': len(fraud_rings),
            'processing_time_seconds': session.processing_time
        }
    }

    buf = io.BytesIO()
    buf.write(json.dumps(output, indent=2).encode('utf-8'))
    buf.seek(0)

    return send_file(buf, mimetype='application/json',
                     as_attachment=True, download_name=f'fraud_report_{session_id}.json')


@main_bp.route('/api/download-pdf/<int:session_id>')
def download_pdf(session_id):
    session = UploadSession.query.get_or_404(session_id)
    fraud_rings = FraudRing.query.filter_by(session_id=session_id).order_by(FraudRing.risk_score.desc()).all()
    suspicious_accounts = SuspiciousAccount.query.filter_by(session_id=session_id)\
        .order_by(SuspiciousAccount.suspicion_score.desc()).all()

    ai_summary = request.args.get('ai_summary', '')

    transactions = Transaction.query.filter_by(session_id=session_id).order_by(Transaction.timestamp).all()

    pdf_buffer = generate_pdf_report(session, fraud_rings, suspicious_accounts, ai_summary, transactions)

    return send_file(pdf_buffer, mimetype='application/pdf',
                     as_attachment=True, download_name=f'investigation_report_{session_id}.pdf')


@main_bp.route('/api/graph-data/<int:session_id>')
def graph_data_api(session_id):
    transactions = Transaction.query.filter_by(session_id=session_id).all()
    suspicious_accounts = SuspiciousAccount.query.filter_by(session_id=session_id).all()
    fraud_rings = FraudRing.query.filter_by(session_id=session_id).all()

    suspicious_ids = {a.account_id for a in suspicious_accounts}
    ring_member_map = {}
    for ring in fraud_rings:
        for acc in ring.member_accounts:
            ring_member_map[acc] = ring.pattern_type

    nodes_set = set()
    for tx in transactions:
        nodes_set.add(tx.sender_id)
        nodes_set.add(tx.receiver_id)

    nodes = [{'id': n, 'suspicious': n in suspicious_ids,
              'pattern': ring_member_map.get(n, 'normal')} for n in nodes_set]

    edge_map = {}
    for tx in transactions:
        key = (tx.sender_id, tx.receiver_id)
        if key not in edge_map:
            edge_map[key] = {'source': tx.sender_id, 'target': tx.receiver_id,
                             'amount': 0, 'count': 0,
                             'suspicious': tx.sender_id in suspicious_ids or tx.receiver_id in suspicious_ids}
        edge_map[key]['amount'] += tx.amount or 0
        edge_map[key]['count'] += 1

    return jsonify({'nodes': nodes, 'edges': list(edge_map.values())})


@main_bp.route('/api/ai-chat', methods=['POST'])
def ai_chat():
    data = request.get_json()
    question = data.get('question', '')
    session_id = data.get('session_id')

    if not question or not session_id:
        return jsonify({'error': 'Missing question or session_id'}), 400

    session = UploadSession.query.get(session_id)
    fraud_rings = FraudRing.query.filter_by(session_id=session_id).all()
    suspicious_accounts = SuspiciousAccount.query.filter_by(session_id=session_id).limit(10).all()

    context = f"""
Session: {session.filename} uploaded on {session.upload_time}
Total transactions: {session.total_transactions}
Total accounts: {session.total_accounts}
Fraud rings detected: {len(fraud_rings)}
Top suspicious accounts: {', '.join([a.account_id for a in suspicious_accounts[:5]])}
Ring types: {', '.join(set([r.pattern_type for r in fraud_rings]))}
"""

    answer = chat_with_data(question, context)
    return jsonify({'answer': answer})


@main_bp.route('/api/account-detail/<int:session_id>/<account_id>')
def account_detail(session_id, account_id):
    acc = SuspiciousAccount.query.filter_by(session_id=session_id, account_id=account_id).first()
    if not acc:
        return jsonify({'account_id': account_id, 'suspicious': False})

    sent = Transaction.query.filter_by(session_id=session_id, sender_id=account_id).count()
    received = Transaction.query.filter_by(session_id=session_id, receiver_id=account_id).count()

    return jsonify({
        'account_id': acc.account_id,
        'suspicion_score': acc.suspicion_score,
        'detected_patterns': acc.detected_patterns,
        'ring_id': acc.ring_id,
        'ai_explanation': acc.ai_explanation,
        'transactions_sent': sent,
        'transactions_received': received,
        'suspicious': True
    })

