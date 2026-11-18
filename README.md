# 🍽️ Kitchen Ledger Analytics

**Multi-Branch Restaurant Inventory Reconciliation, Unit Normalization & Variance Visualization**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14%2B-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Plotly](https://img.shields.io/badge/Plotly-Interactive_BI-3F4F75?logo=plotly&logoColor=white)](https://plotly.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📌 Project Overview

**Kitchen Ledger Analytics** is an enterprise-grade data engineering and business intelligence visualization system built to solve a critical operational problem in multi-branch restaurant chains: **unexplained inventory shrinkage and food-cost leakage**.

Raw restaurant operational data arrives in mismatched measurement units (`kg`, `lb`, `oz`, `L`, `tbsp`, `tsp`, `dozen`, `pcs`) across procurement invoices, kitchen recipes, point-of-sale (POS) tickets, and daily waste sheets. This project normalizes all operational quantities into standardized base units (`g`, `ml`, `pcs`) directly inside **PostgreSQL**, calculates theoretical ingredient consumption from POS sales and recipe Bills of Materials (BOM), reconciles purchases against physical counts and logged waste, and surfaces actionable anomalies in an interactive **Streamlit + Plotly** dashboard.

### Core Capabilities
* **Automated Unit Normalization:** SQL-driven conversion lookup engine (`unit_conversions`) standardizing weight, volume, and count metrics across operational tables with zero `NULL` multipliers.
* **Theoretical vs. Actual Reconciliation:** Joins POS sales volume with recipe BOMs to quantify expected ingredient draw and isolate unexplained variance:
  $$\text{Unexplained Variance} = \text{Actual Depletion} - (\text{Theoretical Usage} + \text{Logged Waste})$$
* **Graceful Missing-Recipe Auditing:** Preserves unmapped POS menu items via `LEFT JOIN` auditing so high-selling items without recipe definitions are flagged rather than silently dropped.
* **Root-Cause Anomaly Classification:** Automatically categorizes branch-ingredient outliers into *High Unexplained Shrinkage / Over-portioning*, *Excess Spoilage*, or *Within Tolerance*.
* **Zero-Config Instant Demo Mode:** Fallback simulation engine in `app/db.py` allows instantaneous testing of the Streamlit dashboard even without an active PostgreSQL instance.

---

## 🏗️ System Architecture

All heavy unit-conversion math, BOM explosions, and variance aggregations are executed inside **PostgreSQL analytical views**, keeping the **Streamlit + Plotly** visualization frontend fast, modular, and stateless.

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                        RAW OPERATIONAL DATA (30 Days)                   │
│  Purchases (kg, lb, L) │ Recipes (oz, tbsp, g) │ POS Sales │ Waste Logs │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     POSTGRESQL ANALYTICAL LAYER                         │
│  • 01_schema.sql         : Normalized star-like schema + unit lookups   │
│  • 02_seed_data.sql      : 4 Pune branches + planted anomaly scenarios  │
│  • 03_variance_views.sql :                                              │
│      ├── vw_normalized_purchases & vw_normalized_waste                  │
│      ├── vw_theoretical_usage (BOM explosion + missing recipe flags)    │
│      ├── vw_menu_item_audit (POS revenue vs. recipe coverage)           │
│      └── vw_inventory_reconciliation (Variance %, ₹ Loss & Root Cause)  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ SQLAlchemy + Cached Queries (@st.cache_data)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  STREAMLIT + PLOTLY VISUALIZATION UI                    │
│  • Executive KPI Ribbon (Spend, Theoretical Usage, Waste, Shrinkage ₹)  │
│  • Tab 1: Branch Comparison Bars, Top 10 Leaks & Variance % Heatmap     │
│  • Tab 2: Menu Item Sales vs. Recipe Coverage Bubble Audit              │
│  • Tab 3: Prioritized Action Queue & One-Click CSV Audit Export         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🗄️ Database Schema & Data Modeling

The relational model separates **Master Dimensions**, **Operational Logs**, and **Analytical Reconciliation Views**:

```mermaid
erDiagram
    BRANCHES ||--o{ PURCHASES : receives
    BRANCHES ||--o{ SALES : rings
    BRANCHES ||--o{ WASTE_LOGS : records
    BRANCHES ||--o{ INVENTORY_COUNTS : audits
    
    CATEGORIES ||--o{ INGREDIENTS : classifies
    UNITS_OF_MEASURE ||--o{ INGREDIENTS : base_unit
    UNITS_OF_MEASURE ||--o{ UNIT_CONVERSIONS : "from/to"
    
    INGREDIENTS ||--o{ RECIPE_INGREDIENTS : "BOM component"
    INGREDIENTS ||--o{ PURCHASES : received
    INGREDIENTS ||--o{ WASTE_LOGS : scrapped
    INGREDIENTS ||--o{ INVENTORY_COUNTS : counted
    
    MENU_CATEGORIES ||--o{ MENU_ITEMS : groups
    MENU_ITEMS ||--o| RECIPES : "1:1 recipe"
    MENU_ITEMS ||--o{ SALES : sold
    RECIPES ||--o{ RECIPE_INGREDIENTS : contains
    
    SUPPLIERS ||--o{ PURCHASES : supplies
    WASTE_REASONS ||--o{ WASTE_LOGS : categorizes
```

### Key Relational Tables:
| Table Name | Description | Key Columns |
| :--- | :--- | :--- |
| `branches` | 4 Pune operating restaurant locations | `branch_id`, `branch_code`, `branch_name`, `city`, `region` |
| `categories` | Classification of raw materials | `category_id`, `category_name`, `target_food_cost_pct` |
| `units_of_measure` | Physical measurement units across mass, volume, and count | `uom_code`, `uom_name`, `dimension`, `is_base_unit` |
| `unit_conversions` | Explicit conversion multipliers to dimension base units | `from_unit`, `to_unit`, `multiplier`, `dimension` |
| `ingredients` | Raw ingredient master catalog with INR unit costs per base unit | `ingredient_id`, `sku`, `ingredient_name`, `base_unit`, `cost_per_base_unit`, `yield_pct` |
| `menu_items` | Sellable POS menu items | `menu_item_id`, `sku`, `item_name`, `selling_price` |
| `recipes` & `recipe_ingredients` | Bill of Materials (BOM) linking menu dishes to raw ingredients | `recipe_id`, `menu_item_id`, `gross_quantity`, `unit`, `prep_waste_pct` |
| `purchases` | Supplier receiving shipments in bulk units | `purchase_id`, `branch_id`, `ingredient_id`, `quantity`, `unit`, `total_cost` |
| `sales` | Daily POS sales transactions per branch | `sale_id`, `branch_id`, `menu_item_id`, `sale_date`, `quantity`, `total_amount` |
| `waste_logs` | Documented scrap, line spills, and spoilage logs | `waste_id`, `branch_id`, `ingredient_id`, `reason`, `quantity`, `estimated_cost` |
| `inventory_counts` | Physical stock takes at start and end of audit periods | `count_id`, `branch_id`, `ingredient_id`, `quantity`, `unit`, `count_type` |

---

## ⚖️ Unit Normalization Engine

Restaurant supply chains mix imperial and metric units across procurement and line cooking. Our unit conversion engine maps all measurements to standard base units:
- **Mass Base:** `g` (Grams)
- **Volume Base:** `ml` (Milliliters)
- **Count Base:** `pcs` (Pieces)

### Standard Conversion Lookups (`unit_conversions`):
```sql
-- Convert any quantity Q in unit U to an ingredient's base unit B:
SELECT Q * COALESCE(uc.multiplier, 1.0) AS quantity_in_base
FROM unit_conversions uc
WHERE uc.from_unit = U AND uc.to_unit = B;
```
* **Supported Mappings:**
  - `kg` $\rightarrow$ `g` (`× 1,000.0`)
  - `oz` $\rightarrow$ `g` (`× 28.34952`)
  - `lb` $\rightarrow$ `g` (`× 453.59237`)
  - `L` / `l` $\rightarrow$ `ml` (`× 1,000.0`)
  - `tbsp` $\rightarrow$ `ml` (`× 15.0`)
  - `tsp` $\rightarrow$ `ml` (`× 5.0`)
  - `dozen` $\rightarrow$ `pcs` (`× 12.0`)
  - Culinary volume-to-mass rules (`tbsp` $\rightarrow$ `g`, `tsp` $\rightarrow$ `g`, `ml` $\rightarrow$ `g`) for recipe herbs and seasoning.

---

## 🎯 4 Planted Visual Stories (Pune Network)

The dataset deterministically generates 30 days of multi-branch operations (`random.seed(42)`), embedding 4 specific operational stories:

| Branch | Location | Story Archetype | Operational Simulation | Variance & Financial Impact | Audit Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Hinjawadi IT Park** | Pune, West | **Story 1: Unexplained Shrinkage / Theft** | Purchased **+24.2%** more Mozzarella Cheese and Boneless Chicken Breast than theoretical recipe sales + waste justify. Stock drained. | **+24.4%** Cheese (₹22,195 loss)<br>**+24.5%** Chicken (₹15,498 loss) | `Flagged for Review (CRITICAL LEAK)` |
| **Viman Nagar Hub** | Pune, East | **Story 2: Logged Cooler Malfunction Spoilage** | Documented heavy spoilage (**~18% to 23%** of purchases) on Fresh Tomatoes & Basil due to walk-in chiller compressor failure. | Waste: **22.9%** on Basil<br>Unexplained: **-0.3%** (low) | `Excess Waste Logged (SPOILAGE)` |
| **Baner High Street** | Pune, North-West | **Story 3: Unmapped POS Recipe Drain** | High sales (**313 units** for *Truffle Mushroom Melt*; **995 units** for *Iced Caramel Cortado*) with **zero rows in `recipes`**. | Unallocated ingredient draw; ₹370,000+ unmapped sales | `Missing Recipe` in `vw_menu_item_audit` |
| **Koregaon Park Flagship** | Pune, Central | **Story 4: Healthy Baseline Benchmark** | Procurement calibrated within **$\pm 1.5\%$** of `(Theoretical Usage + Logged Waste)` across all 12 ingredients. | **-1.2% to +1.4%** across all items | `Normal Tolerance` |

---

## 🖥️ Streamlit Dashboard Walkthrough

Launch the dashboard via `python -m streamlit run app/dashboard.py`:

```text
========================================================================================
🍽️ KITCHEN LEDGER ANALYTICS - DASHBOARD INTERFACE
========================================================================================
[Sidebar Filters]  📍 Branch Multi-Select | 🥗 Category Filter | 🔍 Review Status Toggle
----------------------------------------------------------------------------------------
[Top KPI Ribbon]   Total Spend: ₹1.85M | Recipe Usage: ₹1.68M | Waste: ₹58K | Shrinkage: ₹42K
----------------------------------------------------------------------------------------
[Tab 1: Variance]  • Grouped Bar: Branch Comparison (Hinjawadi Red Leak Bar Stands Out)
                   • Horizontal Bar: Top 10 Loss Items (Mozzarella & Chicken Lead ₹ Loss)
                   • Heatmap: Diverging Branch × Ingredient Variance % (Red Outlier Cells)
----------------------------------------------------------------------------------------
[Tab 2: Coverage]  • ⚠️ Warning Banner: 1,308 Units Sold Without Recipe BOM (₹193K Drain)
                   • Bubble Scatter: Sales Volume vs Revenue (Unmapped Items in Coral)
                   • Interactive Menu Audit Table with Revenue Breakdown
----------------------------------------------------------------------------------------
[Tab 3: Actions]   • Flagged Review Queue: Items Sorted by Highest Loss Amount (₹)
                   • 📥 One-Click CSV Export: inventory_audit_report.csv
                   • Operational Guidance Directives for Kitchen Management
========================================================================================
```

---

## 🚀 Getting Started

### 1. Clone & Setup Python Environment

```bash
# Clone the repository
git clone https://github.com/your-username/kitchen-ledger-analytics.git
cd kitchen-ledger-analytics

# Create virtual environment (recommended)
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment (`.env`)

```bash
# Copy example environment configuration
cp .env.example .env
```
Edit `.env` with your PostgreSQL database credentials:
```ini
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/restaurant_inventory_db
```

### 3. Initialize PostgreSQL Database & Seed Data

```bash
# 1. Create the database
psql -U postgres -c "CREATE DATABASE restaurant_inventory_db;"

# 2. Initialize relational DDL schema & unit conversion engine
psql -U postgres -d restaurant_inventory_db -f sql/01_schema.sql

# 3. Seed deterministic 30-day operational records & planted stories
psql -U postgres -d restaurant_inventory_db -f sql/02_seed_data.sql

# 4. Compile analytical variance reconciliation views
psql -U postgres -d restaurant_inventory_db -f sql/03_variance_views.sql
```

*Alternative Python Ingestion:*
```bash
# Regenerate fresh seed SQL or execute directly via SQLAlchemy:
python scripts/generate_seed.py --execute --db-url "postgresql://postgres:your_password@localhost:5432/restaurant_inventory_db"
```

### 4. Run the Streamlit Dashboard

```bash
# Launch interactive BI application
python -m streamlit run app/dashboard.py
```
Open **`http://localhost:8501`** in your browser.

> [!TIP]
> **Zero-Configuration Instant Preview:** If PostgreSQL is offline, `app/db.py` automatically activates the built-in **Simulation Fallback Engine**, rendering the full 30-day interactive dashboard immediately!

---

## 🧪 Verification & QA Testing

Run these 3 validation queries inside PostgreSQL to verify data integrity:

### 1. Unit Normalization Audit (Zero NULL Multipliers)
```sql
SELECT 
    b.branch_name,
    COUNT(*) AS total_items,
    COUNT(CASE WHEN r.total_purchased_qty IS NULL THEN 1 END) AS null_purchases,
    COUNT(CASE WHEN r.theoretical_usage_qty IS NULL THEN 1 END) AS null_theoretical,
    COUNT(CASE WHEN r.unexplained_variance_pct IS NULL THEN 1 END) AS null_variance
FROM vw_inventory_reconciliation r
JOIN branches b ON r.branch_id = b.branch_id
GROUP BY b.branch_name;
```
*Expected: 0 null values across all branches.*

### 2. Hinjawadi Shrinkage Anomaly Audit
```sql
SELECT 
    branch_name, ingredient_name, base_unit,
    total_purchased_qty, theoretical_usage_qty, logged_waste_qty,
    unexplained_variance_qty, unexplained_variance_cost,
    unexplained_variance_pct, status
FROM vw_inventory_reconciliation
WHERE branch_name = 'Hinjawadi IT Park'
  AND ingredient_name IN ('Mozzarella Cheese', 'Boneless Chicken Breast');
```
*Expected:*
- `Mozzarella Cheese`: Variance $\approx \mathbf{+24.4\%}$, Unexplained Loss $\approx \mathbf{₹22,195}$, Status = **`Flagged for Review`**.
- `Boneless Chicken Breast`: Variance $\approx \mathbf{+24.5\%}$, Unexplained Loss $\approx \mathbf{₹15,498}$, Status = **`Flagged for Review`**.

### 3. Missing Recipe Coverage Audit
```sql
SELECT 
    menu_item_id, sku, menu_item_name, category_name,
    recipe_status, ingredient_count, total_units_sold, total_revenue
FROM vw_menu_item_audit
WHERE recipe_status = 'Missing Recipe';
```
*Expected:*
- `Truffle Mushroom Melt`: `313 units` at Baner High Street, `total_revenue = ₹131,460`.
- `Iced Caramel Cortado`: `995 units` across branches, `total_revenue = ₹238,800`.

---

## 📁 Repository Structure

```text
kitchen-ledger-analytics/
├── .streamlit/
│   └── config.toml           # Streamlit UI theme (custom typography & warm accents)
├── app/
│   ├── db.py                 # SQLAlchemy connection manager & @st.cache_data query layer
│   └── dashboard.py          # Main Streamlit + Plotly visual dashboard
├── scripts/
│   └── generate_seed.py      # Deterministic 30-day operational seed generator (seed: 42)
├── sql/
│   ├── 01_schema.sql         # Multi-branch DDL, constraints & unit conversion engine
│   ├── 02_seed_data.sql      # Multi-row INSERT seed data (1,766 lines, 143 KB)
│   └── 03_variance_views.sql # Reconciliation engine, menu audit & normalized waste views
├── .env.example              # Environment variables template
├── requirements.txt          # Python dependencies
└── README.md                 # Complete project documentation
```

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.
