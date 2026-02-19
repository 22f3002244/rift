import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.units import inch
import matplotlib.pyplot as plt
import pandas as pd


def generate_transaction_chart(transactions):
    if not transactions:
        return None

    try:
        data = [{'timestamp': t.timestamp, 'amount': t.amount} for t in transactions if t.timestamp]
        if not data:
            return None

        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)

        duration = (df.index.max() - df.index.min()).total_seconds()
        if duration > 86400 * 2:
            resampled = df.resample('D').sum()
            title = "Daily Transaction Volume"
        else:
            resampled = df.resample('H').sum()
            title = "Hourly Transaction Volume"

        fig, ax = plt.subplots(figsize=(7, 3.5))
        ax.plot(resampled.index, resampled['amount'], marker='o', linestyle='-', color='#1a73e8', linewidth=2, markersize=4)
        ax.set_title(title, fontsize=10, fontweight='bold', color='#3c4043')
        ax.grid(True, linestyle='--', alpha=0.5)

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        fig.tight_layout()

        img_buffer = io.BytesIO()
        fig.savefig(img_buffer, format='png', dpi=100)
        img_buffer.seek(0)
        plt.close(fig)

        return img_buffer
    except Exception as e:
        print(f"Error generating tx chart: {e}")
        return None


def generate_suspicious_bar_chart(transactions, suspicious_accounts):
    if not transactions or not suspicious_accounts:
        return None

    try:
        top_sus = suspicious_accounts[:5]
        ids = [acc.account_id for acc in top_sus]

        volumes = []
        for acc_id in ids:
            vol = sum(t.amount for t in transactions if t.sender_id == acc_id or t.receiver_id == acc_id)
            volumes.append(vol)

        if not volumes:
            return None

        fig, ax = plt.subplots(figsize=(7, 3.5))
        colors_list = ['#d93025' for _ in range(len(ids))]
        ax.bar(ids, volumes, color=colors_list, alpha=0.7)

        ax.set_title("Top 5 Suspicious Accounts - Total Volume", fontsize=10, fontweight='bold', color='#3c4043')
        ax.grid(axis='y', linestyle='--', alpha=0.5)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        fig.tight_layout()

        img_buffer = io.BytesIO()
        fig.savefig(img_buffer, format='png', dpi=100)
        img_buffer.seek(0)
        plt.close(fig)

        return img_buffer
    except Exception as e:
        print(f"Error generating bar chart: {e}")
        return None


def generate_pdf_report(session, fraud_rings, suspicious_accounts, ai_summary, transactions=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=50, leftMargin=50,
                            topMargin=50, bottomMargin=50)

    styles = getSampleStyleSheet()
    story = []

    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=16,
        textColor=colors.HexColor('#2c3e50'),
        alignment=TA_CENTER,
        spaceAfter=6
    )
    story.append(Paragraph("FINFORENSICS AI ENGINE", header_style))

    title_style = ParagraphStyle(
        'Title',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=22,
        textColor=colors.black,
        alignment=TA_CENTER,
        spaceAfter=12
    )
    story.append(Paragraph("CONFIDENTIAL INVESTIGATION REPORT", title_style))

    story.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceAfter=12))

    date_str = datetime.now().strftime("%B %d, %Y")
    meta_data = [
        [f"CASE ID: #{session.id}", f"DATE: {date_str}"],
        [f"SOURCE: {session.filename}", "STATUS: COMPLETED"]
    ]
    meta_table = Table(meta_data, colWidths=[4*inch, 2.5*inch])
    meta_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Times-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 24))

    story.append(Paragraph("1. EXECUTIVE SUMMARY",
        ParagraphStyle('H1', parent=styles['Heading2'], fontName='Times-Bold', fontSize=12, spaceAfter=8)))

    summary_text = ai_summary if ai_summary else "No automated summary generated for this session."

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=11,
        leading=14,
        alignment=TA_JUSTIFY
    )
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 24))

    story.append(Paragraph("2. KEY FINDINGS METRICS",
        ParagraphStyle('H1', parent=styles['Heading2'], fontName='Times-Bold', fontSize=12, spaceAfter=12)))

    stats_data = [
        ["TOTAL ACCOUNTS", "TRANSACTIONS", "SUSPICIOUS ENTITIES", "FRAUD RINGS"],
        [
            str(session.total_accounts),
            str(session.total_transactions),
            str(len(suspicious_accounts)),
            str(len(fraud_rings))
        ]
    ]

    stats_table = Table(stats_data, colWidths=[1.8*inch]*4)
    stats_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, 1), 12),
        ('FONTNAME', (0, 1), (-1, 1), 'Times-Bold'),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(stats_table)
    story.append(Spacer(1, 24))

    if transactions:
        story.append(Paragraph("3. TRANSACTION ACTIVITY OVER TIME",
            ParagraphStyle('H1', parent=styles['Heading2'], fontName='Times-Bold', fontSize=12, spaceAfter=12)))

        chart_buffer = generate_transaction_chart(transactions)
        if chart_buffer:
            im = Image(chart_buffer, width=6*inch, height=3*inch)
            story.append(im)
            story.append(Spacer(1, 24))

    bar_buffer = generate_suspicious_bar_chart(transactions, suspicious_accounts)
    if bar_buffer:
        im2 = Image(bar_buffer, width=6*inch, height=3*inch)
        story.append(im2)
        story.append(Spacer(1, 24))

    if fraud_rings:
        story.append(Paragraph("3. DETECTED FRAUD PATTERNS",
            ParagraphStyle('H1', parent=styles['Heading2'], fontName='Times-Bold', fontSize=12, spaceAfter=12)))

        ring_data = [["RING ID", "PATTERN TYPE", "SIZE", "RISK SCORE"]]
        for ring in fraud_rings[:10]:
            ring_data.append([
                f"#{ring.ring_id}",
                ring.pattern_type.replace('_', ' ').upper(),
                f"{len(ring.member_accounts)} Accounts",
                f"{ring.risk_score}/100"
            ])

        ring_table = Table(ring_data, colWidths=[1.2*inch, 2.5*inch, 1.5*inch, 1.2*inch])
        ring_table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#444')),
            ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(ring_table)
        story.append(Spacer(1, 24))

    if suspicious_accounts:
        story.append(Paragraph("4. HIGH RISK ACCOUNTS (TOP 15)",
            ParagraphStyle('H1', parent=styles['Heading2'], fontName='Times-Bold', fontSize=12, spaceAfter=12)))

        acc_data = [["ACCOUNT ID", "RISK SCORE", "DETECTED INDICATORS"]]
        for acc in suspicious_accounts[:15]:
            patterns = ", ".join([p.replace('_', ' ').upper() for p in acc.detected_patterns])
            acc_data.append([
                acc.account_id,
                str(acc.suspicion_score),
                patterns
            ])

        acc_table = Table(acc_data, colWidths=[2*inch, 1*inch, 3.5*inch])
        acc_table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ]))
        story.append(acc_table)

    story.append(Spacer(1, 40))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.gray, spaceAfter=6))

    disclaimer = "This report is generated automatically by the FinForensics AI Engine for investigative purposes only. " \
                 "The findings herein are probabilistic indications of risk and should be verified by a human analyst. " \
                 "Confidential - Do Not Distribute."

    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontName='Times-Italic',
        fontSize=8,
        textColor=colors.gray,
        alignment=TA_CENTER
    )
    story.append(Paragraph(disclaimer, footer_style))

    doc.build(story)
    buffer.seek(0)
    return buffer
