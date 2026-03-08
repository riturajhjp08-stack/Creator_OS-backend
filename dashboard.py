import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from io import StringIO

# --- Page Config ---
st.set_page_config(
    page_title="Business Insight Dashboard",
    page_icon="📊",
    layout="wide",
)

# --- Home description ---
st.markdown("""
<div style="text-align: center; padding: 3rem 0; background: linear-gradient(135deg, #667eea10 0%, #764ba210 100%); border-radius: 12px; margin-bottom: 2rem;">
  <h1 style="margin: 0; color: #333; font-size: 2.5rem; font-weight: 700;">📊 Business Insights</h1>
  <p style="margin: 0.5rem 0 0 0; color: #666; font-size: 1.1rem;">Analyze your data in seconds</p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

st.markdown("""
<div style="text-align: center; padding: 2rem; color: #666;">
  <p><strong>👈 Use the sidebar to upload data, filter, and explore.</strong></p>
  <p style="font-size: 0.95rem; margin-top: 1rem;">Upload a CSV file to get started, or use the sample dataset.</p>
</div>
""", unsafe_allow_html=True)
)

# --- Custom CSS ---
st.markdown("""
<style>
    * { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    body { background: #f8f9fa; }
    .block-container { 
        padding-top: 1rem; 
        padding-bottom: 1rem; 
        padding-left: 2rem;
        padding-right: 2rem;
    }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px 25px;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 15px rgba(102,126,234,0.2);
        border: 1px solid rgba(102,126,234,0.3);
    }
    [data-testid="stMetric"] label { color: rgba(255,255,255,0.85) !important; font-size: 0.85rem !important; font-weight: 600; }
    [data-testid="stMetric"] [data-testid="stMetricValue"] { color: white !important; font-size: 2rem !important; font-weight: 700; }
    div[data-testid="stSidebar"] { 
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
        backdrop-filter: blur(10px);
    }
    div[data-testid="stSidebar"] * { color: white !important; }
    .main { background: #ffffff; }
    hr { border: 1px solid #e0e0e0 !important; }
    h1, h2, h3 { color: #1a1a2e; }
    .chart-container {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        border: 1px solid #f0f0f0;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# --- Load Data ---
@st.cache_data
# Make the loader flexible: either use the built-in sample file or accept an uploaded CSV
# Returns a cleaned DataFrame with parsed dates and additional columns used by the dashboard.
def load_data(uploaded_file=None):
    if uploaded_file is not None:
        try:
            # streamlit provides a BytesIO-like object
            df = pd.read_csv(uploaded_file, encoding='latin1')
        except Exception:
            st.error("Could not read the uploaded file. Please make sure it's a valid CSV with the same structure as the sample.")
            return pd.DataFrame()
    else:
        df = pd.read_csv('Sample - Superstore.csv', encoding='latin1')

    # Ensure expected columns exist before converting datatypes
    for col in ['Order Date', 'Ship Date']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    if 'Order Date' in df.columns:
        df['Year'] = df['Order Date'].dt.year
        df['Month'] = df['Order Date'].dt.to_period('M').astype(str)
    return df

# allow the user to upload their own dataset; falls back to sample
uploaded = st.sidebar.file_uploader("Upload CSV (optional)", type=["csv"])
df = load_data(uploaded)

if df.empty:
    st.error("No data available. Please upload a valid CSV or check the sample file.")
    st.stop()

# Ensure essential columns exist before proceeding. We prefer Sales/Profit/Order ID
required = ['Sales', 'Profit', 'Order ID']
missing = [c for c in required if c not in df.columns]
generic_mode = False
column_mapping = {}
if missing:
    st.warning(f"Dataset is missing preferred columns: {', '.join(missing)}.")
    st.markdown("#### Map your columns to the dashboard (optional)")
    # let user map their columns to the expected names
    cols_options = ["(none)"] + df.columns.tolist()
    for req in required:
        if req in df.columns:
            # already present, no mapping needed
            column_mapping[req] = req
        else:
            sel = st.selectbox(f"Map '{req}' to", options=cols_options, key=f"map_{req}")
            if sel and sel != "(none)":
                column_mapping[req] = sel

    # if the user mapped all required fields, create/alias them and use specialised dashboard
    if all(k in column_mapping for k in required):
        for req, colname in column_mapping.items():
            # copy or rename the column into the expected name
            try:
                df[req] = df[colname]
            except Exception:
                # if assignment fails, leave as-is and fall back to generic
                st.warning(f"Could not map {colname} to {req} - will use generic explorer.")
                generic_mode = True
                break
        else:
            st.success("All required fields mapped — switching to specialised dashboard.")
            generic_mode = False
    else:
        st.info("Not all required fields mapped — continuing in generic explorer mode.")
        generic_mode = True

# --- Sidebar Filters & Instructions ---
with st.sidebar:
    st.markdown("## 📘 Quick Guide")
    with st.expander("How to use this dashboard", expanded=True):
        st.markdown(
            """
            1. **Upload your own file** or use the built-in sample dataset.
            2. Choose filters below; you can select multiple values for each attribute.
            3. Pick a view and explore interactive charts. Hover and click for details.
            4. Beginners: start with the **Overview** tab before diving deeper.
            5. If your file doesn’t fit the expected schema, the app will switch
               to a generic explorer mode with basic summaries and histograms.
            """
        )
    st.markdown("---")

    if generic_mode:
        st.markdown("## 🔧 Generic filters")
        # allow the user to pick a column to filter on and values for that column
        filter_col = st.selectbox("Pick a column to filter (optional)", options=[""] + df.columns.tolist())
        selected_values = []
        if filter_col and filter_col in df.columns:
            unique = sorted(df[filter_col].dropna().unique().tolist())
            selected_values = st.multiselect(f"Values for {filter_col}", options=unique)
        # store generic filter choices for later use
        generic_filter = (filter_col, selected_values)

        # still allow choosing a view, though it will be ignored in generic mode
        view_option = st.radio("📊 Choose a view", options=["Overview"])
    else:
        st.markdown("## 🎛️ Filters")

    # use multiselect so beginners can select multiple or keep "All" automatically
    # Some uploaded files might not have these columns; handle missing keys gracefully.
    if 'Year' in df.columns:
        years = sorted(df['Year'].dropna().unique().tolist())
    else:
        years = []
        st.warning("Dataset does not contain a 'Year' column; year filtering will be skipped.")
    selected_year = st.multiselect(
        "📅 Year (pick one or more, blank = all)",
        options=years,
        default=years if len(years) <= 3 else []
    )

    if 'Region' in df.columns:
        regions = sorted(df['Region'].dropna().unique().tolist())
    else:
        regions = []
        st.warning("Dataset does not contain a 'Region' column; region filtering will be skipped.")
    selected_region = st.multiselect(
        "🌍 Region (pick one or more)",
        options=regions,
    )

    if 'Category' in df.columns:
        categories = sorted(df['Category'].dropna().unique().tolist())
    else:
        categories = []
        st.warning("Dataset does not contain a 'Category' column; category filtering will be skipped.")
    selected_category = st.multiselect(
        "📦 Category (pick one or more)",
        options=categories,
    )

    if 'Segment' in df.columns:
        segments = sorted(df['Segment'].dropna().unique().tolist())
    else:
        segments = []
        st.warning("Dataset does not contain a 'Segment' column; segment filtering will be skipped.")
    selected_segment = st.multiselect(
        "👥 Segment (pick one or more)",
        options=segments,
    )

    st.markdown("---")

    view_option = st.radio(
        "📊 Choose a view",  # radio makes it easier to see all options
        options=[
            "Overview",
            "Top Products",
            "Sales Trends",
            "Profit Analysis",
            "Regional Breakdown",
        ],
    )

    # feedback after view selector
    with st.sidebar.expander("💬 Feedback", expanded=False):
        with st.form("feedback_form", clear_on_submit=True):
            rating = st.slider("Rate this dashboard", 1, 5, 3)
            comments = st.text_area("Comments (optional)")
            submitted = st.form_submit_button("Submit")
            if submitted:
                try:
                    import datetime
                    fb = pd.DataFrame([{"timestamp": datetime.datetime.now(),
                                        "rating": rating,
                                        "comments": comments}])
                    fb.to_csv("feedback.csv", mode="a", header=not pd.io.common.file_exists("feedback.csv"), index=False)
                    st.success("Thanks for your feedback!")
                except Exception:
                    st.error("Could not save feedback.")

# --- Apply Filters ---
filtered = df.copy()
if generic_mode:
    # apply simple generic filter if requested
    col, vals = generic_filter
    if col and vals:
        filtered = filtered[filtered[col].isin(vals)]
else:
    # each selection is a list; if it's non-empty, keep only those values,
    # but only if the underlying column exists in the dataframe.
    if selected_year and 'Year' in filtered.columns:
        filtered = filtered[filtered['Year'].isin(selected_year)]
    if selected_region and 'Region' in filtered.columns:
        filtered = filtered[filtered['Region'].isin(selected_region)]
    if selected_category and 'Category' in filtered.columns:
        filtered = filtered[filtered['Category'].isin(selected_category)]
    if selected_segment and 'Segment' in filtered.columns:
        filtered = filtered[filtered['Segment'].isin(selected_segment)]

# warn if no rows after filtering
if filtered.empty:
    st.warning("No records match the selected filters. Please adjust the year/region/category/segment selections or upload a different dataset.")

# if generic_mode, provide a friendly, visual explorer and stop
if generic_mode:
    st.markdown("### Dataset Explorer")

    # Basic KPIs (show product-focused metrics if a product-like column exists)
    n_rows, n_cols = filtered.shape
    num_cols = filtered.select_dtypes(include=['number']).columns.tolist()
    cat_cols = filtered.select_dtypes(exclude=['number']).columns.tolist()

    # detect a product-like column
    prod_col = None
    for c in filtered.columns:
        cl = c.lower()
        if any(k in cl for k in ['product', 'item', 'sku']):
            prod_col = c
            break

    k1, k2, k3, k4 = st.columns(4)
    if prod_col:
        # product-focused KPIs
        prod_count = int(filtered[prod_col].nunique())
        try:
            top_prod = filtered[prod_col].mode(dropna=True)[0]
        except Exception:
            top_prod = "-"
        k1.metric("Unique products", f"{prod_count}")
        k2.metric("Top product", f"{top_prod}")
        k3.metric("Rows", f"{n_rows:,}")
        k4.metric("Columns", f"{n_cols}")
    else:
        # generic KPIs
        k1.metric("Rows", f"{n_rows:,}")
        k2.metric("Columns", f"{n_cols}")
        k3.metric("Numeric fields", f"{len(num_cols)}")
        k4.metric("Categorical fields", f"{len(cat_cols)}")

    st.markdown("---")

    # Show a small sample for quick inspection
    st.subheader("Sample rows")
    st.dataframe(filtered.head(8))

    st.markdown("---")

    # Color palette for charts
    palette = ['#667eea', '#764ba2', '#f093fb', '#a8edea', '#ffb86b']

    # Show histograms for up to 3 numeric columns (most informative)
    if num_cols:
        st.subheader("Numeric distributions")
        # pick up to 3 numeric cols with most non-null values
        sorted_num = sorted(num_cols, key=lambda c: filtered[c].count(), reverse=True)[:3]
        for col in sorted_num:
            fig = px.histogram(filtered, x=col, nbins=30, title=f"Distribution of {col}", color_discrete_sequence=[palette[0]])
            fig.update_layout(template='plotly_white')
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No numeric columns found to show distributions.")

    # Show bar/pie charts for up to 3 categorical columns
    if cat_cols:
        st.subheader("Top categories (by frequency)")
        # choose categorical columns that have reasonable cardinality (not too many distinct)
        cand = [c for c in cat_cols if filtered[c].nunique() <= 20]
        cand = cand[:3]
        for col in cand:
            df_top = filtered[col].fillna("(missing)").value_counts().reset_index()
            df_top.columns = [col, 'count']
            # bar chart
            fig_bar = px.bar(df_top.head(10), x='count', y=col, orientation='h', title=f'Top values in {col}', color_discrete_sequence=palette)
            fig_bar.update_layout(template='plotly_white', yaxis={'autorange': 'reversed'})
            st.plotly_chart(fig_bar, use_container_width=True)
            # pie chart of top 6
            fig_pie = px.pie(df_top.head(6), values='count', names=col, title=f'{col} composition (top 6)', color_discrete_sequence=palette)
            fig_pie.update_layout(template='plotly_white')
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No categorical columns found to show category breakdowns.")

    st.markdown('---')
    st.caption('Tip: Upload a dataset with numeric columns for histograms and categorical columns with limited unique values for bars and pies.')
    st.stop()

# allow user to download the current filtered data
try:
    csv = filtered.to_csv(index=False)
    st.download_button("📥 Download filtered data", data=csv, file_name="filtered_data.csv", mime="text/csv")
except Exception:
    # filtered may not exist yet if upload failed
    pass

# provide an expandable raw table for beginners who want to peek at the rows
with st.expander("🔍 View raw data (filtered)", expanded=False):
    st.dataframe(filtered)


# ======================= OVERVIEW =======================
if view_option == "Overview":
    st.markdown("### Overview")
    if 'Sales' not in filtered.columns:
        st.error("Cannot display overview: 'Sales' column missing.")
    else:
        total_sales = filtered['Sales'].sum() if 'Sales' in filtered.columns else 0
        total_profit = filtered['Profit'].sum() if 'Profit' in filtered.columns else 0
        total_orders = filtered['Order ID'].nunique() if 'Order ID' in filtered.columns else len(filtered)
        avg_discount = (filtered['Discount'].mean() * 100) if 'Discount' in filtered.columns else None
        profit_margin = (total_profit / total_sales * 100) if total_sales else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Sales", f"${total_sales:,.0f}")
    c2.metric("Total Profit", f"${total_profit:,.0f}")
    c3.metric("Orders", f"{total_orders:,}")
    c4.metric("Profit Margin", f"{profit_margin:.1f}%")
    if avg_discount is None:
        c5.metric("Avg Discount", "N/A")
    else:
        c5.metric("Avg Discount", f"{avg_discount:.1f}%")

    st.markdown("####")

    col1, col2 = st.columns(2)

    with col1:
        if 'Category' in filtered.columns:
            cat_sales = filtered.groupby('Category')[['Sales', 'Profit']].sum().reset_index()
            fig = px.bar(
                cat_sales, x='Category', y=['Sales', 'Profit'],
                barmode='group', title='Sales & Profit by Category',
                color_discrete_sequence=['#667eea', '#764ba2'],
            )
            fig.update_layout(template='plotly_white', legend_title_text='', height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Category column not available; skipping category breakdown.")

    with col2:
        if 'Segment' in filtered.columns:
            seg_sales = filtered.groupby('Segment')['Sales'].sum().reset_index()
            fig = px.pie(
                seg_sales, values='Sales', names='Segment',
                title='Sales Distribution by Segment',
                color_discrete_sequence=['#667eea', '#764ba2', '#f093fb'],
                hole=0.4,
            )
            fig.update_layout(template='plotly_white', height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Segment column not available; skipping segment distribution.")

    col3, col4 = st.columns(2)

    with col3:
        if 'Region' in filtered.columns:
            region_data = filtered.groupby('Region')[['Sales', 'Profit']].sum().reset_index()
            fig = px.bar(
                region_data, x='Region', y=['Sales', 'Profit'],
                barmode='group', title='Sales & Profit by Region',
                color_discrete_sequence=['#667eea', '#764ba2'],
            )
            fig.update_layout(template='plotly_white', height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Region column not available; skipping regional breakdown.")

    with col4:
        if 'Ship Mode' in filtered.columns:
            ship_data = filtered.groupby('Ship Mode')['Sales'].sum().reset_index()
            fig = px.pie(
                ship_data, values='Sales', names='Ship Mode',
                title='Sales by Ship Mode',
                color_discrete_sequence=['#667eea', '#764ba2', '#f093fb', '#a8edea'],
                hole=0.4,
            )
            fig.update_layout(template='plotly_white', height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Ship Mode column not available; skipping shipping analysis.")


# ======================= TOP PRODUCTS =======================
elif view_option == "Top Products":
    st.markdown("### Top Products")
    # require Sales and Profit columns
    if 'Sales' not in filtered.columns:
        st.error("Cannot show top products: 'Sales' column missing.")
    else:
        n = st.slider("Number of products to display", 5, 20, 10)

    col1, col2 = st.columns(2)

    with col1:
        top_sales = (
            filtered.groupby('Product Name')['Sales'].sum()
            .sort_values(ascending=False).head(n).reset_index()
        )
        fig = px.bar(
            top_sales, x='Sales', y='Product Name',
            orientation='h', title=f'Top {n} Products by Sales',
            color='Sales', color_continuous_scale='Purples',
        )
        fig.update_layout(template='plotly_white', yaxis={'autorange': 'reversed'}, height=500, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        top_profit = (
            filtered.groupby('Product Name')['Profit'].sum()
            .sort_values(ascending=False).head(n).reset_index()
        )
        fig = px.bar(
            top_profit, x='Profit', y='Product Name',
            orientation='h', title=f'Top {n} Products by Profit',
            color='Profit', color_continuous_scale='Greens',
        )
        fig.update_layout(template='plotly_white', yaxis={'autorange': 'reversed'}, height=500, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Sub-Category Performance")

    subcat = filtered.groupby('Sub-Category')[['Sales', 'Profit']].sum().reset_index()
    subcat = subcat.sort_values('Sales', ascending=False)
    fig = px.bar(
        subcat, x='Sub-Category', y=['Sales', 'Profit'],
        barmode='group', title='Sales & Profit by Sub-Category',
        color_discrete_sequence=['#667eea', '#764ba2'],
    )
    fig.update_layout(template='plotly_white', height=450, xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)


# ======================= SALES TRENDS =======================
elif view_option == "Sales Trends":
    st.markdown("### Sales Trends")
    if 'Order Date' not in filtered.columns or 'Sales' not in filtered.columns:
        st.error("Cannot show sales trends: 'Order Date' or 'Sales' column missing.")
    else:
        monthly = filtered.set_index('Order Date').resample('M')[['Sales', 'Profit']].sum().reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly['Order Date'], y=monthly['Sales'],
        mode='lines+markers', name='Sales',
        line=dict(color='#667eea', width=2.5),
        marker=dict(size=5),
    ))
    fig.add_trace(go.Scatter(
        x=monthly['Order Date'], y=monthly['Profit'],
        mode='lines+markers', name='Profit',
        line=dict(color='#764ba2', width=2.5),
        marker=dict(size=5),
    ))
    fig.update_layout(
        title='Monthly Sales & Profit Trend',
        template='plotly_white', height=450,
        xaxis_title='Date', yaxis_title='Amount ($)',
    )
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        yearly = filtered.set_index('Order Date').resample('Y')[['Sales']].sum().reset_index()
        yearly['Year'] = yearly['Order Date'].dt.year
        fig = px.bar(
            yearly, x='Year', y='Sales', title='Yearly Sales',
            color='Sales', color_continuous_scale='Purples', text_auto=',.0f',
        )
        fig.update_layout(template='plotly_white', height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        yearly_p = filtered.set_index('Order Date').resample('Y')[['Profit']].sum().reset_index()
        yearly_p['Year'] = yearly_p['Order Date'].dt.year
        fig = px.bar(
            yearly_p, x='Year', y='Profit', title='Yearly Profit',
            color='Profit', color_continuous_scale='Greens', text_auto=',.0f',
        )
        fig.update_layout(template='plotly_white', height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Quarterly Breakdown")
    quarterly = filtered.set_index('Order Date').resample('Q')[['Sales', 'Profit']].sum().reset_index()
    quarterly['Quarter'] = quarterly['Order Date'].dt.to_period('Q').astype(str)
    fig = px.bar(
        quarterly, x='Quarter', y=['Sales', 'Profit'],
        barmode='group', title='Quarterly Sales & Profit',
        color_discrete_sequence=['#667eea', '#764ba2'],
    )
    fig.update_layout(template='plotly_white', height=400, xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)


# ======================= PROFIT ANALYSIS =======================
elif view_option == "Profit Analysis":
    st.markdown("### Profit Analysis")
    if 'Profit' not in filtered.columns:
        st.error("Cannot show profit analysis: 'Profit' column missing.")
    else:
        col1, col2 = st.columns(2)

    with col1:
        fig = px.scatter(
            filtered, x='Sales', y='Profit', color='Category',
            title='Sales vs Profit',
            color_discrete_sequence=['#667eea', '#764ba2', '#f093fb'],
            opacity=0.6, hover_data=['Product Name'],
        )
        fig.update_layout(template='plotly_white', height=450)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.scatter(
            filtered, x='Discount', y='Profit', color='Category',
            title='Discount vs Profit',
            color_discrete_sequence=['#667eea', '#764ba2', '#f093fb'],
            opacity=0.6,
        )
        fig.update_layout(template='plotly_white', height=450)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    loss_products = (
        filtered.groupby('Product Name')['Profit'].sum()
        .sort_values().head(10).reset_index()
    )
    fig = px.bar(
        loss_products, x='Profit', y='Product Name',
        orientation='h', title='Top 10 Loss-Making Products',
        color='Profit', color_continuous_scale='Reds_r',
    )
    fig.update_layout(template='plotly_white', yaxis={'autorange': 'reversed'}, height=450, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Profit Margin by Sub-Category")
    subcat_pm = filtered.groupby('Sub-Category')[['Sales', 'Profit']].sum().reset_index()
    subcat_pm['Profit Margin %'] = (subcat_pm['Profit'] / subcat_pm['Sales'] * 100).round(1)
    subcat_pm = subcat_pm.sort_values('Profit Margin %', ascending=True)
    colors = ['#e74c3c' if v < 0 else '#667eea' for v in subcat_pm['Profit Margin %']]
    fig = go.Figure(go.Bar(
        x=subcat_pm['Profit Margin %'], y=subcat_pm['Sub-Category'],
        orientation='h', marker_color=colors,
        text=subcat_pm['Profit Margin %'].apply(lambda x: f'{x:.1f}%'),
        textposition='outside',
    ))
    fig.update_layout(
        title='Profit Margin % by Sub-Category',
        template='plotly_white', height=450,
        xaxis_title='Profit Margin %',
    )
    st.plotly_chart(fig, use_container_width=True)


# ======================= REGIONAL BREAKDOWN =======================
elif view_option == "Regional Breakdown":
    st.markdown("### Geography view\nCompare performance across regions, states, and cities. The data table at the bottom gives an exact summary.")
    if 'Region' not in filtered.columns or 'Sales' not in filtered.columns:
        st.error("Cannot show regional breakdown: required columns missing.")
    else:
        region_summary = filtered.groupby('Region').agg(
        Sales=('Sales', 'sum'),
        Profit=('Profit', 'sum'),
        Orders=('Order ID', 'nunique'),
        Quantity=('Quantity', 'sum'),
    ).reset_index()

    fig = px.bar(
        region_summary, x='Region', y=['Sales', 'Profit'],
        barmode='group', title='Sales & Profit by Region',
        color_discrete_sequence=['#667eea', '#764ba2'],
        text_auto=',.0f',
    )
    fig.update_layout(template='plotly_white', height=400)
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        state_sales = filtered.groupby('State')['Sales'].sum().sort_values(ascending=False).head(10).reset_index()
        fig = px.bar(
            state_sales, x='Sales', y='State',
            orientation='h', title='Top 10 States by Sales',
            color='Sales', color_continuous_scale='Purples',
        )
        fig.update_layout(template='plotly_white', yaxis={'autorange': 'reversed'}, height=450, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        city_sales = filtered.groupby('City')['Sales'].sum().sort_values(ascending=False).head(10).reset_index()
        fig = px.bar(
            city_sales, x='Sales', y='City',
            orientation='h', title='Top 10 Cities by Sales',
            color='Sales', color_continuous_scale='Purples',
        )
        fig.update_layout(template='plotly_white', yaxis={'autorange': 'reversed'}, height=450, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Regional Details")
    st.dataframe(
        region_summary.style.format({'Sales': '${:,.0f}', 'Profit': '${:,.0f}', 'Orders': '{:,}', 'Quantity': '{:,}'}),
        use_container_width=True,
    )
