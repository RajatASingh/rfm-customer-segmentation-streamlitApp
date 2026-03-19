import io
from datetime import timedelta
import pandas as pd
import numpy as np
import streamlit as st
from streamlit_option_menu import option_menu
import plotly.express as px

# ---------------- PAGE CONFIG (MUST BE FIRST) ----------------
st.set_page_config(page_title="RFM Analyzer", layout="wide")

# ---------------- INJECT CSS (must come AFTER set_page_config) ----------------
with open("styled.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ---------------- TITLE & NAV ----------------
st.title("RFM Analyzer")

selected = option_menu(
    None,
    ["RFM Analyzer", "About"],
    icons=["database-down", "info-circle"],
    orientation="horizontal",
    styles={
        "container": {
            "padding": "4px",
            "background-color": "#13161e",
            "border-radius": "99px",
            "border": "1px solid rgba(255,255,255,0.07)",
        },
        "nav-link": {
            "color": "#8892a4",
            "font-size": "0.875rem",
            "font-weight": "500",
            "border-radius": "99px",
            "padding": "0.5rem 1.4rem",
        },
        "nav-link-selected": {
            "background": "linear-gradient(135deg, #63b3ed, #76e4f7)",
            "color": "#ffffff",
            "font-weight": "600",
            "border-radius": "99px",
            "box-shadow": "0 2px 14px rgba(99,179,237,0.4)",
        },
        "icon": {
            "color": "inherit",
            "font-size": "0.9rem",
        },
    }
)

# ---------------- FILE UPLOAD ----------------
uploaded_file = st.sidebar.file_uploader(
    "Upload Excel or CSV file",
    type=["xlsx", "xls", "csv"]
)

# ---------------- RFM FUNCTIONS ----------------
def compute_rfm(df, date_col, customer_col, amount_col):
    df = df[[date_col, customer_col, amount_col]].copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df[amount_col] = pd.to_numeric(df[amount_col], errors="coerce").fillna(0)
    df.dropna(subset=[date_col, customer_col], inplace=True)

    ref_date = df[date_col].max() + timedelta(days=1)

    rfm = df.groupby(customer_col).agg(
        Recency=(date_col, lambda x: (ref_date - x.max()).days),
        Frequency=(customer_col, "count"),
        Monetary=(amount_col, "sum")
    ).reset_index()

    rfm.columns = ["Customer", "Recency", "Frequency", "Monetary"]

    rfm["R"] = pd.qcut(rfm["Recency"], 5, labels=[5,4,3,2,1]).astype(int)
    rfm["F"] = pd.qcut(rfm["Frequency"].rank(method="first"), 5, labels=[1,2,3,4,5]).astype(int)
    rfm["M"] = pd.qcut(rfm["Monetary"], 5, labels=[1,2,3,4,5]).astype(int)
    rfm["RFM_Score"] = rfm["R"] + rfm["F"] + rfm["M"]

    return rfm, df

def rfm_segment(row):
    score = row["RFM_Score"]
    if score >= 13:   return "Champions"
    elif score >= 11: return "Loyal Customers"
    elif score >= 9:  return "Potential Loyalists"
    elif score >= 8:  return "Recent Customers"
    elif score >= 7:  return "Promising"
    elif score >= 6:  return "Customers Needing Attention"
    elif score == 5:  return "About To Sleep"
    elif score == 4:  return "At Risk"
    elif score == 3:  return "Can't Lose Them"
    elif score == 2:  return "Hibernating"
    else:             return "Lost"

# ---------------- MAIN LOGIC ----------------
if selected == "RFM Analyzer":
    if uploaded_file:
        if uploaded_file.name.endswith(("xls", "xlsx")):
            raw = pd.read_excel(uploaded_file)
        else:
            raw = pd.read_csv(uploaded_file)

        cols = raw.columns.tolist()
        date_col     = st.sidebar.selectbox("Order Date Column", cols)
        customer_col = st.sidebar.selectbox("Customer Column",   cols)
        amount_col   = st.sidebar.selectbox("Amount Column",     cols)

        if st.sidebar.button("Run RFM Analysis"):
            rfm, base_df = compute_rfm(raw, date_col, customer_col, amount_col)
            rfm["Segment"] = rfm.apply(rfm_segment, axis=1)

            # ---- KPI Metrics ----
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Customers", rfm.shape[0])
            col2.metric("Total Sales",     f"{rfm['Monetary'].sum():,.2f}")
            col3.metric("Avg RFM Score",   f"{rfm['RFM_Score'].mean():.2f}")

            # ---- Tabs ----
            tab1, tab2 = st.tabs(["📊 RFM Visuals", "📋 RFM Table"])

            with tab1:
                st.subheader("RFM Insights")
                col1, col2 = st.columns(2)

                with col1:
                    fig1 = px.bar(
                        rfm["Segment"].value_counts().reset_index(name="count"),
                        x="Segment", y="count",
                        labels={"count": "Customers"},
                        color="count",
                        color_continuous_scale="Blues",
                        title="Customers per Segment"
                    )
                    fig1.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font_color="#8892a4",
                        xaxis=dict(tickangle=-30)
                    )
                    st.plotly_chart(fig1, use_container_width=True)

                with col2:
                    fig2 = px.pie(
                        rfm, values="Monetary", names="Segment",
                        hole=0.4, title="Revenue by Segment"
                    )
                    fig2.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        font_color="#8892a4"
                    )
                    st.plotly_chart(fig2, use_container_width=True)

                # Sales over time — use base_df (raw transactional data), NOT rfm
                st.subheader("Sales Over Time")
                sales_over_time = (
                    base_df.groupby(date_col)[amount_col]
                    .sum()
                    .reset_index()
                    .sort_values(date_col)
                )
                fig3 = px.line(
                    sales_over_time,
                    x=date_col, y=amount_col,
                    title="Total Sales Over Time",
                    labels={amount_col: "Sales"}
                )
                fig3.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#8892a4"
                )
                st.plotly_chart(fig3, use_container_width=True)

            with tab2:
                st.subheader("Customer RFM Segmentation")
                st.dataframe(
                    rfm.sort_values("RFM_Score", ascending=False),
                    use_container_width=True
                )
                st.download_button(
                    "⬇ Download RFM Table",
                    rfm.to_csv(index=False),
                    "rfm_results.csv",
                    "text/csv"
                )
    else:
        st.info("Upload a CSV or Excel file from the sidebar to begin.")

# ---------------- ABOUT PAGE ----------------
if selected == "About":
    st.markdown("""
    ### What is RFM?
    RFM stands for **Recency, Frequency, and Monetary value**.  
    It is a proven customer segmentation technique used to identify **high-value customers**,
    **at-risk customers**, and **growth opportunities** based on purchase behavior.

    - **Recency** – How recently a customer purchased  
    - **Frequency** – How often they purchase  
    - **Monetary** – How much money they spend  

    Customers are grouped into **11 meaningful segments**, each requiring a different strategy.
    """)

    st.markdown("---")
    st.subheader("RFM Customer Segments & Recommended Actions")

    rfm_actions = {
        "Champions":                   ("Best customers – recent, frequent, high spenders.",       "Reward loyalty, exclusive deals, early access, referral programs."),
        "Loyal Customers":             ("Consistent buyers who trust your brand.",                  "Upsell premium products, cross-sell, personalized recommendations."),
        "Potential Loyalists":         ("Recent customers with growing engagement.",                "Nurture with targeted offers, loyalty programs, product education."),
        "New Customers":               ("Recently acquired customers.",                             "Strong onboarding, welcome discounts, brand storytelling."),
        "Promising":                   ("Recent buyers but low frequency.",                         "Engagement campaigns, reminders, limited-time offers."),
        "Customers Needing Attention": ("Above average customers losing momentum.",                 "Re-engagement emails, personalized offers, feedback surveys."),
        "About To Sleep":              ("Customers showing signs of inactivity.",                   "Urgent incentives, flash sales, reminder notifications."),
        "At Risk":                     ("High spenders who haven't purchased recently.",            "Win-back campaigns, personalized communication, exclusive discounts."),
        "Can't Lose Them":             ("Previously loyal customers now inactive.",                 "One-to-one outreach, special loyalty offers, relationship rebuilding."),
        "Hibernating":                 ("Inactive, low-spending customers.",                        "Low-cost marketing, awareness campaigns, seasonal promotions."),
        "Lost":                        ("Churned customers with no recent activity.",               "Minimal spend on reactivation; analyze churn reasons instead."),
    }

    for segment, (meaning, action) in rfm_actions.items():
        st.markdown(f"**🔹 {segment}**  \n**Meaning:** {meaning}  \n**Action:** {action}")
        st.markdown("---")