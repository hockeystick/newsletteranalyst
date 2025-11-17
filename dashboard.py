#!/usr/bin/env python3
"""
Newsletter Analyst Dashboard

Interactive Streamlit dashboard for exploring newsletter onboarding email analysis.

Run with: streamlit run dashboard.py
"""

import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime
from pathlib import Path

from src.database import NewsletterDatabase
from src.reporter import EmailReporter
from src.pattern_detector import PatternDetector


# Page config
st.set_page_config(
    page_title="Newsletter Analyst Dashboard",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .email-detail {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 1px solid #e0e0e0;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data():
    """Load data from database."""
    db_path = 'data/newsletter_emails.db'

    if not Path(db_path).exists():
        return None, None, None

    db = NewsletterDatabase(db_path)

    # Get analyzed emails
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT
            e.id, e.publisher_name, e.country, e.sender, e.subject,
            e.send_date, e.email_sequence_number, e.sequence_confidence,
            e.body_text,
            a.primary_purpose, a.tone, a.effectiveness_score,
            a.effectiveness_reasoning, a.value_propositions,
            a.calls_to_action, a.personalization_elements,
            a.notable_elements, a.key_takeaways,
            a.frequency_expectations, a.analyzed_at
        FROM emails e
        INNER JOIN email_analysis a ON e.id = a.email_id
        ORDER BY e.send_date DESC
    """)

    rows = cursor.fetchall()

    if not rows:
        db.close()
        return None, None, None

    # Convert to DataFrame
    emails_data = []
    for row in rows:
        value_props = json.loads(row[13]) if row[13] else []
        ctas = json.loads(row[14]) if row[14] else []
        personalization = json.loads(row[15]) if row[15] else []
        notable = json.loads(row[16]) if row[16] else []
        takeaways = json.loads(row[17]) if row[17] else []

        emails_data.append({
            'id': row[0],
            'publisher_name': row[1],
            'country': row[2] or 'Unknown',
            'sender': row[3],
            'subject': row[4],
            'send_date': row[5],
            'sequence_number': row[6],
            'sequence_confidence': row[7] or 'N/A',
            'body_text': row[8],
            'body_length': len(row[8]) if row[8] else 0,
            'primary_purpose': row[9],
            'tone': row[10],
            'effectiveness_score': row[11],
            'effectiveness_reasoning': row[12],
            'value_propositions': value_props,
            'value_prop_count': len(value_props),
            'calls_to_action': ctas,
            'cta_count': len(ctas),
            'personalization_elements': personalization,
            'personalization_count': len(personalization),
            'notable_elements': notable,
            'key_takeaways': takeaways,
            'frequency_expectations': row[18],
            'analyzed_at': row[19]
        })

    df = pd.DataFrame(emails_data)

    # Get database stats
    db_stats = db.get_database_stats()

    # Get pattern analysis
    reporter = EmailReporter(db)
    patterns = reporter.get_common_patterns()

    db.close()

    return df, db_stats, patterns


def show_overview(df, db_stats, patterns):
    """Display overview page."""
    st.markdown('<p class="main-header">📧 Newsletter Analyst Dashboard</p>', unsafe_allow_html=True)

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Emails Analyzed",
            value=len(df),
            delta=f"{len(df)/db_stats['total_emails']*100:.0f}% of database"
        )

    with col2:
        st.metric(
            label="Publishers",
            value=df['publisher_name'].nunique()
        )

    with col3:
        st.metric(
            label="Countries",
            value=df['country'].nunique()
        )

    with col4:
        st.metric(
            label="Avg Effectiveness",
            value=f"{df['effectiveness_score'].mean():.1f}/10"
        )

    st.markdown("---")

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Emails by Country")
        country_counts = df['country'].value_counts().head(10)
        fig = px.bar(
            x=country_counts.index,
            y=country_counts.values,
            labels={'x': 'Country', 'y': 'Number of Emails'},
            color=country_counts.values,
            color_continuous_scale='Blues'
        )
        fig.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🎭 Tone Distribution")
        tone_counts = df['tone'].value_counts().head(8)
        fig = px.pie(
            values=tone_counts.values,
            names=tone_counts.index,
            hole=0.4
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    # Effectiveness score distribution
    st.subheader("⭐ Effectiveness Score Distribution")
    score_counts = df['effectiveness_score'].value_counts().sort_index()
    fig = px.bar(
        x=score_counts.index,
        y=score_counts.values,
        labels={'x': 'Effectiveness Score', 'y': 'Number of Emails'},
        color=score_counts.index,
        color_continuous_scale='RdYlGn'
    )
    fig.update_layout(showlegend=False, height=300)
    st.plotly_chart(fig, use_container_width=True)

    # Common patterns
    st.markdown("---")
    st.subheader("🔍 Common Patterns")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Most Common CTAs**")
        for cta, count in patterns['most_common_ctas'][:5]:
            st.write(f"• **{count}x** {cta}")

    with col2:
        st.markdown("**Value Proposition Themes**")
        for keyword, count in patterns['most_common_vp_keywords'][:5]:
            st.write(f"• **{count}x** {keyword}")

    with col3:
        st.markdown("**Personalization Elements**")
        for pers, count in patterns['most_common_personalization'][:5]:
            st.write(f"• **{count}x** {pers}")


def show_emails_table(df):
    """Display filterable emails table."""
    st.markdown('<p class="main-header">📋 Email Analysis Browser</p>', unsafe_allow_html=True)

    # Filters
    st.sidebar.header("🔎 Filters")

    # Publisher filter
    publishers = ['All'] + sorted(df['publisher_name'].unique().tolist())
    selected_publisher = st.sidebar.selectbox("Publisher", publishers)

    # Country filter
    countries = ['All'] + sorted(df['country'].unique().tolist())
    selected_country = st.sidebar.selectbox("Country", countries)

    # Tone filter
    tones = ['All'] + sorted(df['tone'].dropna().unique().tolist())
    selected_tone = st.sidebar.selectbox("Tone", tones)

    # Effectiveness score filter
    min_score, max_score = st.sidebar.slider(
        "Effectiveness Score",
        min_value=int(df['effectiveness_score'].min()),
        max_value=int(df['effectiveness_score'].max()),
        value=(int(df['effectiveness_score'].min()), int(df['effectiveness_score'].max()))
    )

    # Sequence filter
    sequences = ['All'] + sorted([str(s) for s in df['sequence_number'].unique()])
    selected_sequence = st.sidebar.selectbox("Sequence Number", sequences)

    # Apply filters
    filtered_df = df.copy()

    if selected_publisher != 'All':
        filtered_df = filtered_df[filtered_df['publisher_name'] == selected_publisher]

    if selected_country != 'All':
        filtered_df = filtered_df[filtered_df['country'] == selected_country]

    if selected_tone != 'All':
        filtered_df = filtered_df[filtered_df['tone'] == selected_tone]

    filtered_df = filtered_df[
        (filtered_df['effectiveness_score'] >= min_score) &
        (filtered_df['effectiveness_score'] <= max_score)
    ]

    if selected_sequence != 'All':
        filtered_df = filtered_df[filtered_df['sequence_number'] == int(selected_sequence)]

    # Display count
    st.write(f"Showing **{len(filtered_df)}** of **{len(df)}** emails")

    # Export button
    if len(filtered_df) > 0:
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Filtered Results (CSV)",
            data=csv,
            file_name=f"filtered_emails_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

    st.markdown("---")

    # Display table
    display_df = filtered_df[[
        'publisher_name', 'country', 'subject', 'sequence_number',
        'tone', 'effectiveness_score', 'cta_count', 'value_prop_count', 'send_date'
    ]].copy()

    display_df.columns = [
        'Publisher', 'Country', 'Subject', 'Seq#',
        'Tone', 'Score', 'CTAs', 'Value Props', 'Date'
    ]

    # Color code by score
    def highlight_score(row):
        score = row['Score']
        if score >= 8:
            return ['background-color: #d4edda'] * len(row)
        elif score <= 5:
            return ['background-color: #f8d7da'] * len(row)
        else:
            return [''] * len(row)

    st.dataframe(
        display_df.style.apply(highlight_score, axis=1),
        use_container_width=True,
        height=600
    )

    # Detail view
    st.markdown("---")
    st.subheader("📧 Email Detail View")

    email_options = [f"{row['publisher_name']} - {row['subject'][:50]}"
                     for _, row in filtered_df.iterrows()]

    if email_options:
        selected_email_idx = st.selectbox(
            "Select email to view details:",
            range(len(filtered_df)),
            format_func=lambda x: email_options[x]
        )

        show_email_detail(filtered_df.iloc[selected_email_idx])


def show_email_detail(email):
    """Display detailed view of a single email."""
    st.markdown('<div class="email-detail">', unsafe_allow_html=True)

    # Header
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.markdown(f"### {email['subject']}")
        st.write(f"**Publisher:** {email['publisher_name']}")

    with col2:
        st.metric("Effectiveness", f"{email['effectiveness_score']}/10")

    with col3:
        st.metric("Sequence #", email['sequence_number'])

    st.markdown("---")

    # Metadata
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.write(f"**Sender:** {email['sender']}")

    with col2:
        st.write(f"**Country:** {email['country']}")

    with col3:
        st.write(f"**Tone:** {email['tone']}")

    with col4:
        st.write(f"**Date:** {email['send_date'][:10]}")

    st.markdown("---")

    # Analysis
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📝 Primary Purpose:**")
        st.info(email['primary_purpose'])

        st.markdown("**💡 Value Propositions:**")
        for vp in email['value_propositions']:
            st.write(f"• {vp}")

        st.markdown("**🎯 Calls to Action:**")
        for cta in email['calls_to_action']:
            if isinstance(cta, dict):
                st.write(f"• {cta.get('text', '')} _(type: {cta.get('type', 'unknown')})_")
            else:
                st.write(f"• {cta}")

    with col2:
        st.markdown("**⭐ Effectiveness Reasoning:**")
        st.success(email['effectiveness_reasoning'])

        st.markdown("**🔑 Key Takeaways:**")
        for takeaway in email['key_takeaways']:
            st.write(f"• {takeaway}")

        if email['personalization_elements']:
            st.markdown("**👤 Personalization:**")
            for pers in email['personalization_elements']:
                st.write(f"• {pers}")

        if email['notable_elements']:
            st.markdown("**✨ Notable Elements:**")
            for notable in email['notable_elements']:
                st.write(f"• {notable}")

    # Email body (expandable)
    with st.expander("📄 View Email Body"):
        st.text_area(
            "Full email text:",
            value=email['body_text'][:2000] + "..." if len(email['body_text']) > 2000 else email['body_text'],
            height=300,
            disabled=True
        )

    st.markdown('</div>', unsafe_allow_html=True)


def show_comparisons(df):
    """Display comparison views."""
    st.markdown('<p class="main-header">📊 Comparative Analysis</p>', unsafe_allow_html=True)

    # Country comparison
    st.subheader("🌍 Analysis by Country")

    country_stats = df.groupby('country').agg({
        'effectiveness_score': 'mean',
        'cta_count': 'mean',
        'value_prop_count': 'mean',
        'body_length': 'mean',
        'publisher_name': 'count'
    }).round(2)

    country_stats.columns = ['Avg Score', 'Avg CTAs', 'Avg Value Props', 'Avg Length', 'Email Count']
    country_stats = country_stats.sort_values('Email Count', ascending=False)

    st.dataframe(country_stats, use_container_width=True)

    # Visualizations
    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            country_stats.head(10),
            x=country_stats.head(10).index,
            y='Avg Score',
            title="Average Effectiveness by Country (Top 10)",
            labels={'x': 'Country', 'Avg Score': 'Avg Effectiveness Score'},
            color='Avg Score',
            color_continuous_scale='RdYlGn'
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.scatter(
            country_stats,
            x='Avg CTAs',
            y='Avg Score',
            size='Email Count',
            hover_name=country_stats.index,
            title="CTAs vs Effectiveness",
            labels={'Avg CTAs': 'Average CTAs', 'Avg Score': 'Avg Effectiveness Score'}
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Tone comparison
    st.subheader("🎭 Analysis by Tone")

    tone_stats = df.groupby('tone').agg({
        'effectiveness_score': 'mean',
        'cta_count': 'mean',
        'value_prop_count': 'mean',
        'publisher_name': 'count'
    }).round(2)

    tone_stats.columns = ['Avg Score', 'Avg CTAs', 'Avg Value Props', 'Email Count']
    tone_stats = tone_stats.sort_values('Avg Score', ascending=False)

    st.dataframe(tone_stats, use_container_width=True)

    fig = px.bar(
        tone_stats,
        x=tone_stats.index,
        y='Avg Score',
        title="Average Effectiveness by Tone",
        labels={'x': 'Tone', 'Avg Score': 'Avg Effectiveness Score'},
        color='Avg Score',
        color_continuous_scale='RdYlGn'
    )
    st.plotly_chart(fig, use_container_width=True)


def main():
    """Main dashboard function."""
    # Load data
    with st.spinner("Loading data..."):
        df, db_stats, patterns = load_data()

    if df is None:
        st.error("No analyzed emails found in database. Please run analysis first:")
        st.code("python -m src.main analyze-emails --batch-size 10")
        return

    # Sidebar navigation
    st.sidebar.title("📧 Newsletter Analyst")
    page = st.sidebar.radio(
        "Navigation",
        ["Overview", "Browse Emails", "Comparative Analysis"]
    )

    # Show selected page
    if page == "Overview":
        show_overview(df, db_stats, patterns)
    elif page == "Browse Emails":
        show_emails_table(df)
    elif page == "Comparative Analysis":
        show_comparisons(df)

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    st.sidebar.markdown(f"**Total Emails:** {len(df)}")


if __name__ == '__main__':
    main()
