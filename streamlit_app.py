import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import numpy as np

# Page configuration
st.set_page_config(
    page_title="SEC Earnings Growth Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# Load data
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("sec_quarterly_raw_data.csv")
        df['quarter'] = df['fy'].astype(str) + '-' + df['fq']
        df['date'] = pd.to_datetime(df['fy'].astype(str) + '-' + 
                                     df['fq'].str.replace('Q', '').astype(int).mul(3).astype(str) + '-01')
        return df
    except FileNotFoundError:
        st.error("Data file not found. Please run sec_data_extractor.py first.")
        return None

# Main app
def main():
    # Header
    st.markdown('<p class="main-header">📊 SEC Earnings Growth Analyzer</p>', unsafe_allow_html=True)
    st.markdown("**Quantitative Analysis of Quarterly Financial Data from SEC EDGAR Filings**")
    st.markdown("---")
    
    # Load data
    df = load_data()
    if df is None:
        return
    
    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    
    # Ticker selection
    all_tickers = sorted(df['ticker'].unique())
    selected_tickers = st.sidebar.multiselect(
        "Select Companies",
        options=all_tickers,
        default=all_tickers[:5] if len(all_tickers) > 5 else all_tickers
    )
    
    # Year range
    min_year, max_year = int(df['fy'].min()), int(df['fy'].max())
    year_range = st.sidebar.slider(
        "Year Range",
        min_value=min_year,
        max_value=max_year,
        value=(max_year-3, max_year)
    )
    
    # Filter data
    filtered_df = df[
        (df['ticker'].isin(selected_tickers)) &
        (df['fy'] >= year_range[0]) &
        (df['fy'] <= year_range[1])
    ]
    
    if filtered_df.empty:
        st.warning("No data available for the selected filters.")
        return
    
    # Overview metrics
    st.header("📈 Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Companies",
            len(filtered_df['ticker'].unique()),
            delta=None
        )
    
    with col2:
        st.metric(
            "Total Quarters",
            len(filtered_df),
            delta=None
        )
    
    with col3:
        avg_growth = filtered_df['earning_growth'].replace([np.inf, -np.inf], np.nan).mean()
        st.metric(
            "Avg Earnings Growth",
            f"{avg_growth:.2%}",
            delta=None
        )
    
    with col4:
        total_revenue = filtered_df['revenue'].sum() / 1e9
        st.metric(
            "Total Revenue",
            f"${total_revenue:.1f}B",
            delta=None
        )
    
    st.markdown("---")
    
    # Tabs for different analyses
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Earnings Growth", 
        "💰 Profitability", 
        "🔄 Efficiency", 
        "💵 Cash Flow",
        "📋 Raw Data"
    ])
    
    # Tab 1: Earnings Growth
    with tab1:
        st.subheader("Quarterly Earnings Growth Over Time")
        
        fig = go.Figure()
        for ticker in selected_tickers:
            ticker_data = filtered_df[filtered_df['ticker'] == ticker].sort_values('date')
            fig.add_trace(go.Scatter(
                x=ticker_data['date'],
                y=ticker_data['earning_growth'] * 100,
                mode='lines+markers',
                name=ticker,
                hovertemplate='%{y:.2f}%<extra></extra>'
            ))
        
        fig.update_layout(
            xaxis_title="Quarter",
            yaxis_title="Earnings Growth (QoQ %)",
            hovermode='x unified',
            height=500,
            showlegend=True,
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Earnings growth distribution
        st.subheader("Earnings Growth Distribution")
        col1, col2 = st.columns(2)
        
        with col1:
            fig_hist = px.histogram(
                filtered_df[filtered_df['earning_growth'].between(-1, 1)],
                x='earning_growth',
                nbins=50,
                title="Distribution (Winsorized at ±100%)",
                labels={'earning_growth': 'Earnings Growth (QoQ)'}
            )
            fig_hist.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig_hist, use_container_width=True)
        
        with col2:
            # Summary statistics
            st.markdown("**Summary Statistics**")
            growth_stats = filtered_df['earning_growth'].replace([np.inf, -np.inf], np.nan).describe()
            stats_df = pd.DataFrame({
                'Metric': ['Mean', 'Median', 'Std Dev', 'Min', 'Max'],
                'Value': [
                    f"{growth_stats['mean']:.2%}",
                    f"{growth_stats['50%']:.2%}",
                    f"{growth_stats['std']:.2%}",
                    f"{growth_stats['min']:.2%}",
                    f"{growth_stats['max']:.2%}"
                ]
            })
            st.dataframe(stats_df, hide_index=True, use_container_width=True)
    
    # Tab 2: Profitability
    with tab2:
        st.subheader("Profitability Metrics Over Time")
        
        metric_options = {
            'Gross Margin': 'gross_margin',
            'Operating Margin': 'op_margin',
            'Net Margin': 'net_margin',
            'EBITDA Margin': 'ebitda_margin',
            'ROE': 'roe'
        }
        
        selected_metric = st.selectbox("Select Metric", list(metric_options.keys()))
        metric_col = metric_options[selected_metric]
        
        fig = go.Figure()
        for ticker in selected_tickers:
            ticker_data = filtered_df[filtered_df['ticker'] == ticker].sort_values('date')
            fig.add_trace(go.Scatter(
                x=ticker_data['date'],
                y=ticker_data[metric_col] * 100,
                mode='lines+markers',
                name=ticker,
                hovertemplate='%{y:.2f}%<extra></extra>'
            ))
        
        fig.update_layout(
            xaxis_title="Quarter",
            yaxis_title=f"{selected_metric} (%)",
            hovermode='x unified',
            height=500,
            showlegend=True,
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Margin comparison
        st.subheader("Latest Quarter Margin Comparison")
        latest_quarter = filtered_df['date'].max()
        latest_data = filtered_df[filtered_df['date'] == latest_quarter]
        
        margin_cols = ['gross_margin', 'op_margin', 'net_margin', 'ebitda_margin']
        margin_data = latest_data[['ticker'] + margin_cols].melt(
            id_vars='ticker',
            var_name='Margin Type',
            value_name='Value'
        )
        margin_data['Value'] = margin_data['Value'] * 100
        
        fig_bar = px.bar(
            margin_data,
            x='ticker',
            y='Value',
            color='Margin Type',
            barmode='group',
            title=f"Margin Comparison - {latest_quarter.strftime('%Y-%m-%d')}",
            labels={'Value': 'Margin (%)', 'ticker': 'Company'}
        )
        fig_bar.update_layout(height=400)
        st.plotly_chart(fig_bar, use_container_width=True)
    
    # Tab 3: Efficiency
    with tab3:
        st.subheader("Working Capital Efficiency")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Cash Conversion Cycle
            st.markdown("**Cash Conversion Cycle (Days)**")
            fig_ccc = go.Figure()
            for ticker in selected_tickers:
                ticker_data = filtered_df[filtered_df['ticker'] == ticker].sort_values('date')
                fig_ccc.add_trace(go.Scatter(
                    x=ticker_data['date'],
                    y=ticker_data['ccc'],
                    mode='lines+markers',
                    name=ticker
                ))
            
            fig_ccc.update_layout(
                xaxis_title="Quarter",
                yaxis_title="CCC (Days)",
                hovermode='x unified',
                height=400,
                showlegend=True,
                template="plotly_white"
            )
            st.plotly_chart(fig_ccc, use_container_width=True)
        
        with col2:
            # Asset Turnover
            st.markdown("**Asset Turnover Ratio**")
            fig_turnover = go.Figure()
            for ticker in selected_tickers:
                ticker_data = filtered_df[filtered_df['ticker'] == ticker].sort_values('date')
                fig_turnover.add_trace(go.Scatter(
                    x=ticker_data['date'],
                    y=ticker_data['asset_turnover'],
                    mode='lines+markers',
                    name=ticker
                ))
            
            fig_turnover.update_layout(
                xaxis_title="Quarter",
                yaxis_title="Asset Turnover",
                hovermode='x unified',
                height=400,
                showlegend=True,
                template="plotly_white"
            )
            st.plotly_chart(fig_turnover, use_container_width=True)
        
        # DIO, DSO, DPO breakdown
        st.subheader("Working Capital Components")
        component_options = ['dio', 'dso', 'dpo']
        selected_component = st.selectbox(
            "Select Component",
            ['Days Inventory Outstanding (DIO)', 
             'Days Sales Outstanding (DSO)', 
             'Days Payable Outstanding (DPO)']
        )
        component_map = dict(zip(
            ['Days Inventory Outstanding (DIO)', 
             'Days Sales Outstanding (DSO)', 
             'Days Payable Outstanding (DPO)'],
            component_options
        ))
        
        fig_component = go.Figure()
        for ticker in selected_tickers:
            ticker_data = filtered_df[filtered_df['ticker'] == ticker].sort_values('date')
            fig_component.add_trace(go.Scatter(
                x=ticker_data['date'],
                y=ticker_data[component_map[selected_component]],
                mode='lines+markers',
                name=ticker
            ))
        
        fig_component.update_layout(
            xaxis_title="Quarter",
            yaxis_title=f"{selected_component} (Days)",
            hovermode='x unified',
            height=400,
            showlegend=True,
            template="plotly_white"
        )
        st.plotly_chart(fig_component, use_container_width=True)
    
    # Tab 4: Cash Flow
    with tab4:
        st.subheader("Cash Flow Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Free Cash Flow Margin**")
            fig_fcf = go.Figure()
            for ticker in selected_tickers:
                ticker_data = filtered_df[filtered_df['ticker'] == ticker].sort_values('date')
                fig_fcf.add_trace(go.Scatter(
                    x=ticker_data['date'],
                    y=ticker_data['fcf_margin'] * 100,
                    mode='lines+markers',
                    name=ticker,
                    hovertemplate='%{y:.2f}%<extra></extra>'
                ))
            
            fig_fcf.update_layout(
                xaxis_title="Quarter",
                yaxis_title="FCF Margin (%)",
                hovermode='x unified',
                height=400,
                showlegend=True,
                template="plotly_white"
            )
            st.plotly_chart(fig_fcf, use_container_width=True)
        
        with col2:
            st.markdown("**Cash Flow to Net Income**")
            fig_cf_ni = go.Figure()
            for ticker in selected_tickers:
                ticker_data = filtered_df[filtered_df['ticker'] == ticker].sort_values('date')
                # Cap at reasonable values for visualization
                cf_ni_capped = ticker_data['cf_to_ni'].clip(-2, 5)
                fig_cf_ni.add_trace(go.Scatter(
                    x=ticker_data['date'],
                    y=cf_ni_capped,
                    mode='lines+markers',
                    name=ticker
                ))
            
            fig_cf_ni.update_layout(
                xaxis_title="Quarter",
                yaxis_title="CF/NI Ratio",
                hovermode='x unified',
                height=400,
                showlegend=True,
                template="plotly_white"
            )
            st.plotly_chart(fig_cf_ni, use_container_width=True)
        
        # Cash flow waterfall for selected company
        st.subheader("Cash Flow Breakdown (Latest Quarter)")
        selected_company = st.selectbox("Select Company", selected_tickers)
        
        latest_company_data = filtered_df[
            (filtered_df['ticker'] == selected_company) & 
            (filtered_df['date'] == filtered_df['date'].max())
        ].iloc[0]
        
        fig_waterfall = go.Figure(go.Waterfall(
            name="Cash Flow",
            orientation="v",
            measure=["relative", "relative", "relative", "total"],
            x=["Operating CF", "Investing CF", "Financing CF", "Net Change"],
            y=[
                latest_company_data['cfo'],
                latest_company_data['cfi'],
                latest_company_data['cff'],
                latest_company_data['cfo'] + latest_company_data['cfi'] + latest_company_data['cff']
            ],
            connector={"line": {"color": "rgb(63, 63, 63)"}},
        ))
        
        fig_waterfall.update_layout(
            title=f"{selected_company} - {latest_quarter.strftime('%Y Q%q')}",
            showlegend=False,
            height=400
        )
        st.plotly_chart(fig_waterfall, use_container_width=True)
    
    # Tab 5: Raw Data
    with tab5:
        st.subheader("Filtered Dataset")
        
        # Column selector
        display_cols = st.multiselect(
            "Select Columns to Display",
            options=filtered_df.columns.tolist(),
            default=['ticker', 'fy', 'fq', 'revenue', 'net_income', 'earning_growth', 
                     'gross_margin', 'op_margin', 'net_margin', 'roe']
        )
        
        if display_cols:
            st.dataframe(
                filtered_df[display_cols].sort_values(['ticker', 'fy', 'fq'], ascending=[True, False, False]),
                hide_index=True,
                use_container_width=True
            )
            
            # Download button
            csv = filtered_df[display_cols].to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Filtered Data (CSV)",
                data=csv,
                file_name=f"filtered_financial_data_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("Please select at least one column to display.")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>Data Source: SEC EDGAR XBRL Filings | Built with Streamlit & Plotly</p>
        <p>Created by Gopal Jamnal | <a href='mailto:gopal.jamnal@gmail.com'>gopal.jamnal@gmail.com</a></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
