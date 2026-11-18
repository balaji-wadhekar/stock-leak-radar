"""
==============================================================================
Application: app/dashboard.py
Project: Kitchen Ledger Analytics / Restaurant Inventory & Variance Visualization
Description: Streamlit + Plotly Executive Dashboard exposing multi-branch variance,
             Hinjawadi shrinkage, Viman Nagar spoilage, and Baner unmapped recipes.
Launch Command: streamlit run app/dashboard.py
==============================================================================
"""

import os
import sys
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# Add parent path to allow module imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import (
    get_reconciliation_data,
    get_menu_audit_data,
    get_waste_breakdown,
    test_connection
)

# ------------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & CUSTOM CSS STYLING
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Kitchen Ledger Analytics",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Executive BI Styling
st.markdown("""
<style>
    /* Metric Card Styling */
    [data-testid="stMetric"] {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transition: transform 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        color: #64748B !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #0F172A !important;
    }
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        border-radius: 8px 8px 0 0;
        font-weight: 600;
        color: #475569;
    }
    .stTabs [aria-selected="true"] {
        color: #EA580C !important;
        border-bottom-color: #EA580C !important;
    }
    /* Status Badges */
    .badge-critical {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-warning {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-normal {
        background-color: #ECFDF5;
        color: #065F46;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 2. DATA INGESTION & SIDEBAR CONTROLS
# ------------------------------------------------------------------------------
# Load Cached Data
recon_df_raw = get_reconciliation_data()
menu_df_raw = get_menu_audit_data()
waste_df_raw = get_waste_breakdown()

# Sidebar Branding
st.sidebar.markdown("## 🍽️ Kitchen Ledger")
st.sidebar.caption("Restaurant Inventory & Variance Radar (Pune Network)")

# Sidebar Filter 1: Branch Selection
all_branches = sorted(recon_df_raw["branch_name"].unique().tolist())
selected_branches = st.sidebar.multiselect(
    "📍 Select Branches",
    options=all_branches,
    default=all_branches,
    help="Filter multi-branch operations across Pune network"
)

# Sidebar Filter 2: Ingredient Category Selection
all_categories = sorted(recon_df_raw["category"].unique().tolist())
selected_categories = st.sidebar.multiselect(
    "🥗 Ingredient Categories",
    options=all_categories,
    default=all_categories,
    help="Filter by raw ingredient category"
)

# Sidebar Filter 3: Review Status Toggle
review_status_option = st.sidebar.radio(
    "🔍 Audit Status Filter",
    options=["All Items", "Flagged for Review Only"],
    index=0
)

# Refresh Button
if st.sidebar.button("🔄 Refresh Data Cache", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.divider()
st.sidebar.markdown("""
**Planted Story Highlights:**
- 🔴 **Hinjawadi IT Park:** Cheese & Chicken Shrinkage (>24% leak)
- 🟠 **Viman Nagar Hub:** Produce Cooler Breakdown Spoilage
- 🟡 **Baner High Street:** Unmapped Truffle Melt (300+ units)
- 🟢 **Koregaon Park:** Baseline Benchmark (±1.5%)
""")

# ------------------------------------------------------------------------------
# 3. APPLY GLOBAL FILTERS
# ------------------------------------------------------------------------------
# Filter Reconciliation Data
recon_df = recon_df_raw[
    (recon_df_raw["branch_name"].isin(selected_branches)) &
    (recon_df_raw["category"].isin(selected_categories))
].copy()

if review_status_option == "Flagged for Review Only":
    recon_df = recon_df[recon_df["status"] == "Flagged for Review"]

# Filter Menu Audit Data
menu_df = menu_df_raw[menu_df_raw["branch_name"].isin(selected_branches)].copy()

# Filter Waste Data
waste_df = waste_df_raw[
    (waste_df_raw["branch_name"].isin(selected_branches)) &
    (waste_df_raw["category"].isin(selected_categories))
].copy()

# ------------------------------------------------------------------------------
# 4. TOP EXECUTIVE KPI RIBBON
# ------------------------------------------------------------------------------
st.markdown("### 📊 Executive Variance & Inventory Scorecard")

# Compute KPIs
total_purchase_spend = recon_df["total_purchased_cost"].sum()
total_theoretical_usage = recon_df["theoretical_usage_cost"].sum()
total_logged_waste = recon_df["logged_waste_cost"].sum()
total_unexplained_loss = recon_df["unexplained_variance_cost"].sum()

# Compute Ratios
theoretical_pct = (total_theoretical_usage / total_purchase_spend * 100) if total_purchase_spend > 0 else 0
waste_pct = (total_logged_waste / total_purchase_spend * 100) if total_purchase_spend > 0 else 0
unexplained_pct = (total_unexplained_loss / total_theoretical_usage * 100) if total_theoretical_usage > 0 else 0

kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

with kpi_col1:
    st.metric(
        label="Total Purchase Spend",
        value=f"₹{total_purchase_spend:,.0f}",
        help="Total gross invoice expenditure on raw ingredients"
    )

with kpi_col2:
    st.metric(
        label="Theoretical Recipe Usage",
        value=f"₹{total_theoretical_usage:,.0f}",
        delta=f"{theoretical_pct:.1f}% of Spend",
        delta_color="normal",
        help="Ideal ingredient consumption derived from POS sales bill of materials"
    )

with kpi_col3:
    is_viman_selected = ("Viman Nagar Hub" in selected_branches)
    waste_annotation = "Cooler Spoilage Spike" if (is_viman_selected and waste_pct > 3.0) else f"{waste_pct:.1f}% of Spend"
    st.metric(
        label="Logged Kitchen Waste",
        value=f"₹{total_logged_waste:,.0f}",
        delta=waste_annotation,
        delta_color="off",
        help="Known documented kitchen scrap, damage, and cold-storage spoilage"
    )

with kpi_col4:
    st.metric(
        label="Unexplained Variance Loss",
        value=f"₹{total_unexplained_loss:,.0f}",
        delta=f"{unexplained_pct:+.1f}% Shrinkage",
        delta_color="inverse", # Red for positive shrinkage loss!
        help="Unaccounted ingredient loss (Theft, over-pouring, unrecorded prep waste)"
    )

st.markdown("---")

# ------------------------------------------------------------------------------
# 5. THREE STRUCTURED ANALYTICAL TABS
# ------------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs([
    "📈 Tab 1: Branch & Ingredient Variance",
    "🍕 Tab 2: Menu & Recipe Coverage Audit",
    "🚨 Tab 3: Actionable Review Queue & Export"
])

# ==============================================================================
# TAB 1: BRANCH & INGREDIENT VARIANCE (CORE AUDIT)
# ==============================================================================
with tab1:
    st.markdown("#### Multi-Branch Inventory Reconciliation & Shrinkage Detection")

    chart_col1, chart_col2 = st.columns([1.1, 0.9])

    with chart_col1:
        st.markdown("##### 1. Inventory Reconciliation by Branch (₹ Value)")
        st.caption("Compares Ideal Recipe Consumption vs. Logged Waste vs. Unexplained Shrinkage Gap")

        # Group reconciliation by branch
        branch_agg = recon_df.groupby("branch_name", as_index=False).agg({
            "theoretical_usage_cost": "sum",
            "logged_waste_cost": "sum",
            "unexplained_variance_cost": "sum"
        })

        fig_branch = go.Figure()
        fig_branch.add_trace(go.Bar(
            name="Theoretical Usage",
            x=branch_agg["branch_name"],
            y=branch_agg["theoretical_usage_cost"],
            marker_color="#0D9488",
            hovertemplate="Theoretical Usage: ₹%{y:,.0f}<extra></extra>"
        ))
        fig_branch.add_trace(go.Bar(
            name="Logged Waste",
            x=branch_agg["branch_name"],
            y=branch_agg["logged_waste_cost"],
            marker_color="#F59E0B",
            hovertemplate="Logged Waste: ₹%{y:,.0f}<extra></extra>"
        ))
        fig_branch.add_trace(go.Bar(
            name="Unexplained Leakage (Loss)",
            x=branch_agg["branch_name"],
            y=branch_agg["unexplained_variance_cost"],
            marker_color="#EF4444",
            hovertemplate="Unexplained Leakage: ₹%{y:,.0f}<extra></extra>"
        ))

        fig_branch.update_layout(
            barmode="group",
            margin=dict(l=20, r=20, t=30, b=30),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=380,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis=dict(title="Total Amount (₹)", gridcolor="#F1F5F9"),
            xaxis=dict(title="")
        )
        st.plotly_chart(fig_branch, use_container_width=True)

    with chart_col2:
        st.markdown("##### 2. Top Ingredients by Unexplained Financial Loss (₹)")
        st.caption("Ranked by highest unexplained cost drain across selected branches")

        # Top 10 by unexplained variance cost
        top_offenders = recon_df.groupby(["ingredient_name", "category", "probable_cause", "base_unit"], as_index=False).agg({
            "unexplained_variance_cost": "sum",
            "purchased_base_qty": "sum",
            "theoretical_used_qty": "sum",
            "logged_waste_qty": "sum",
            "unexplained_variance_qty": "sum"
        }).sort_values("unexplained_variance_cost", ascending=True).tail(10)

        # Compute aggregate variance %
        top_offenders["variance_pct"] = np.where(
            top_offenders["theoretical_used_qty"] > 0,
            (top_offenders["unexplained_variance_qty"] / top_offenders["theoretical_used_qty"]) * 100,
            0.0
        )

        color_map = {
            "High Unexplained Shrinkage": "#EF4444",
            "Excess Spoilage": "#F59E0B",
            "Within Tolerance": "#0D9488"
        }

        fig_top = px.bar(
            top_offenders,
            x="unexplained_variance_cost",
            y="ingredient_name",
            orientation="h",
            color="probable_cause",
            color_discrete_map=color_map,
            custom_data=["purchased_base_qty", "theoretical_used_qty", "logged_waste_qty", "variance_pct", "base_unit"]
        )

        fig_top.update_traces(
            hovertemplate=(
                "<b>%{y}</b><br>" +
                "Unexplained Loss: ₹%{x:,.0f}<br>" +
                "Variance %%: %{customdata[3]:+.1f}%%<br>" +
                "Purchased: %{customdata[0]:,.1f} %{customdata[4]}<br>" +
                "Theoretical: %{customdata[1]:,.1f} %{customdata[4]}<br>" +
                "Logged Waste: %{customdata[2]:,.1f} %{customdata[4]}<extra></extra>"
            )
        )

        fig_top.update_layout(
            margin=dict(l=20, r=20, t=30, b=30),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=380,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(title="Unexplained Loss (₹)", gridcolor="#F1F5F9"),
            yaxis=dict(title="")
        )
        st.plotly_chart(fig_top, use_container_width=True)

    st.markdown("---")
    st.markdown("##### 3. Variance % Matrix (Branch × Ingredient Heatmap)")
    st.caption("Diverging color scale centered at 0% deviation: Red indicates abnormal shrinkage (>15%), Blue indicates surplus/under-portioning")

    # Pivot table for Heatmap (Branch x Ingredient)
    heatmap_df = recon_df.pivot_table(
        index="branch_name",
        columns="ingredient_name",
        values="variance_pct",
        aggfunc="mean"
    ).fillna(0.0)

    fig_heat = px.imshow(
        heatmap_df,
        labels=dict(x="Raw Ingredient", y="Restaurant Branch", color="Variance %"),
        x=heatmap_df.columns,
        y=heatmap_df.index,
        color_continuous_scale="RdBu_r", # Diverging Red-White-Blue
        color_continuous_midpoint=0.0,
        range_color=[-10.0, 26.0],
        aspect="auto"
    )

    fig_heat.update_traces(
        text=np.round(heatmap_df.values, 1),
        texttemplate="%{text}%",
        hovertemplate="<b>%{y}</b><br>%{x}<br>Variance: %{z:+.1f}%<extra></extra>"
    )

    fig_heat.update_layout(
        margin=dict(l=20, r=20, t=20, b=20),
        height=320,
        paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig_heat, use_container_width=True)


# ==============================================================================
# TAB 2: MENU ITEM & RECIPE COVERAGE AUDIT
# ==============================================================================
with tab2:
    st.markdown("#### Menu Item Bill of Materials (BOM) Coverage & POS Sales Drain")

    # Check for missing recipes in filtered selection
    missing_recipes = menu_df[menu_df["recipe_status"] == "Missing Recipe"]
    total_unmapped_units = missing_recipes["units_sold"].sum()
    total_unmapped_revenue = missing_recipes["total_revenue"].sum()
    unmapped_items_list = ", ".join(missing_recipes["item_name"].unique().tolist())

    if not missing_recipes.empty and total_unmapped_units > 0:
        st.warning(
            f"⚠️ **CRITICAL RECIPE COVERAGE ALERT:** **{total_unmapped_units:,} POS Units** sold "
            f"across selected branches lack Recipe Bill of Materials mappings, creating **₹{total_unmapped_revenue:,.0f}** "
            f"in unallocated inventory drain!\n\n"
            f"**Unmapped Items Requiring Immediate Culinary BOM:** `{unmapped_items_list}`"
        )
    else:
        st.success("✅ All active menu items sold have fully mapped recipe BOMs.")

    menu_col1, menu_col2 = st.columns([1.1, 0.9])

    with menu_col1:
        st.markdown("##### 4. Menu Item Sales Volume vs. Revenue Impact")
        st.caption("Bubble size corresponds to units sold. Coral nodes indicate missing recipe mappings.")

        # Aggregate menu sales across branches for scatter
        menu_agg = menu_df.groupby(["item_name", "category_name", "recipe_status", "selling_price"], as_index=False).agg({
            "units_sold": "sum",
            "total_revenue": "sum"
        })

        fig_scatter = px.scatter(
            menu_agg,
            x="units_sold",
            y="total_revenue",
            size="units_sold",
            color="recipe_status",
            hover_name="item_name",
            color_discrete_map={"Mapped": "#0D9488", "Missing Recipe": "#EF4444"},
            custom_data=["category_name", "selling_price", "recipe_status"]
        )

        fig_scatter.update_traces(
            hovertemplate=(
                "<b>%{hovertext}</b><br>" +
                "Category: %{customdata[0]}<br>" +
                "Recipe Status: <b>%{customdata[2]}</b><br>" +
                "Selling Price: ₹%{customdata[1]:.2f}<br>" +
                "Units Sold: %{x:,}<br>" +
                "Total Revenue: ₹%{y:,.0f}<extra></extra>"
            )
        )

        fig_scatter.update_layout(
            margin=dict(l=20, r=20, t=30, b=30),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=380,
            xaxis=dict(title="POS Units Sold (30 Days)", gridcolor="#F1F5F9"),
            yaxis=dict(title="Gross Sales Revenue (₹)", gridcolor="#F1F5F9"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    with menu_col2:
        st.markdown("##### 5. Category Revenue Breakdown")
        st.caption("Proportion of sales generated across menu categories")

        cat_revenue = menu_df.groupby("category_name", as_index=False)["total_revenue"].sum()
        fig_donut = px.pie(
            cat_revenue,
            names="category_name",
            values="total_revenue",
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Prism
        )
        fig_donut.update_traces(
            textposition="inside",
            textinfo="percent+label",
            hovertemplate="<b>%{label}</b><br>Revenue: ₹%{value:,.0f} (%{percent})<extra></extra>"
        )
        fig_donut.update_layout(
            margin=dict(l=10, r=10, t=20, b=20),
            height=380,
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    st.markdown("##### 📋 Menu Item Audit Breakdown per Branch")
    display_menu_df = menu_df[[
        "item_name", "branch_name", "category_name", "selling_price",
        "units_sold", "total_revenue", "recipe_status", "audit_recommendation"
    ]].sort_values(["recipe_status", "total_revenue"], ascending=[True, False])

    st.dataframe(
        display_menu_df,
        column_config={
            "item_name": "Menu Item",
            "branch_name": "Branch Location",
            "category_name": "Category",
            "selling_price": st.column_config.NumberColumn("Price (₹)", format="₹%.2f"),
            "units_sold": st.column_config.NumberColumn("Units Sold", format="%d"),
            "total_revenue": st.column_config.NumberColumn("Total Revenue (₹)", format="₹%d"),
            "recipe_status": st.column_config.TextColumn("Recipe Status"),
            "audit_recommendation": "Recommendation"
        },
        use_container_width=True,
        hide_index=True
    )


# ==============================================================================
# TAB 3: ACTIONABLE REVIEW QUEUE & EXPORT
# ==============================================================================
with tab3:
    st.markdown("#### 🚨 Actionable Stock Variance Review Queue")
    st.caption("Inventory line items exhibiting severe unexplained leakage or critical operational anomalies requiring management sign-off.")

    # Filter for Flagged / High Attention Items
    flagged_df = recon_df[recon_df["status"] == "Flagged for Review"].sort_values(
        "unexplained_loss_amount", ascending=False
    ).copy()

    if flagged_df.empty:
        st.success("🎉 No items currently flagged for review within selected filters!")
    else:
        st.markdown(f"**Found `{len(flagged_df)} flagged items` requiring physical kitchen audit:**")

        # Format display dataframe
        review_table = flagged_df[[
            "branch_name", "ingredient_name", "category",
            "purchased_base_qty", "theoretical_used_qty", "logged_waste_qty",
            "variance_pct", "unexplained_loss_amount", "base_unit", "probable_cause"
        ]].copy()

        st.dataframe(
            review_table,
            column_config={
                "branch_name": "Branch",
                "ingredient_name": "Ingredient",
                "category": "Category",
                "purchased_base_qty": st.column_config.NumberColumn("Purchased Qty", format="%.1f"),
                "theoretical_used_qty": st.column_config.NumberColumn("Theoretical Usage", format="%.1f"),
                "logged_waste_qty": st.column_config.NumberColumn("Logged Waste", format="%.1f"),
                "variance_pct": st.column_config.NumberColumn("Variance %", format="%+.1f%%"),
                "unexplained_loss_amount": st.column_config.NumberColumn("Unexplained Loss (₹)", format="₹%d"),
                "base_unit": "UOM",
                "probable_cause": "Probable Cause"
            },
            use_container_width=True,
            hide_index=True
        )

        # CSV Export Option
        csv_data = review_table.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Audit Report (inventory_audit_report.csv)",
            data=csv_data,
            file_name="inventory_audit_report.csv",
            mime="text/csv",
            use_container_width=False
        )

    st.markdown("---")
    st.markdown("#### 🛠️ Operational Audit Guidance & Corrective Action Directives")
    st.markdown("""
    1. **Hinjawadi IT Park (Mozzarella Cheese & Chicken Breast):**
       - **Immediate Directive:** Implement daily portion scale verification at pizza assembly and burger grill stations.
       - **Hypothesis:** Reconcile closing prep containers against shift chef handovers to isolate whether variance stems from heavy-handed portioning or off-book shrinkage.
    2. **Viman Nagar Hub (Tomatoes & Fresh Herbs Spoilage):**
       - **Immediate Directive:** Review walk-in cooler temperature loggers and compressor servicing schedule following the documented thermal failure incident.
    3. **Baner High Street (Truffle Mushroom Melt & Caramel Cortado):**
       - **Immediate Directive:** Complete recipe BOM mapping in POS management system to attribute bun, mushroom, dairy, and espresso consumption directly to dish sales.
    """)

# ------------------------------------------------------------------------------
# FOOTER
# ------------------------------------------------------------------------------
st.markdown("---")
st.caption("Kitchen Ledger Analytics v2.1 • PostgreSQL Analytical Engine & Plotly BI Dashboard • Pune Branch Network")
