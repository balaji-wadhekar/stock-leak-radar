-- ==============================================================================
-- File: 03_variance_views.sql
-- Project: Kitchen Ledger Analytics / Restaurant Inventory & Variance Visualization
-- Description: Analytical Variance Views, Theoretical vs. Actual Reconciliation,
--              Recipe Margin Audits, Branch Performance, and Anomaly Detection.
-- Engine: PostgreSQL 14+
-- Architect: Data Engineer & PostgreSQL Architect
-- ==============================================================================

SET search_path TO restaurant_inventory, public;

-- ------------------------------------------------------------------------------
-- DROP EXISTING VIEWS
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_normalized_waste CASCADE;
DROP VIEW IF EXISTS vw_waste_pareto_analysis CASCADE;
DROP VIEW IF EXISTS vw_top_leak_radar_offenders CASCADE;
DROP VIEW IF EXISTS vw_daily_food_cost_kpis CASCADE;
DROP VIEW IF EXISTS vw_branch_variance_summary CASCADE;
DROP VIEW IF EXISTS vw_recipe_costing CASCADE;
DROP VIEW IF EXISTS vw_menu_item_audit CASCADE;
DROP VIEW IF EXISTS vw_inventory_reconciliation CASCADE;

-- ------------------------------------------------------------------------------
-- 1. VIEW: vw_menu_item_audit
-- Audits all POS menu items per branch to detect unmapped items without recipe BOMs,
-- calculating units sold, branch revenue, and unallocated ingredient drain.
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_menu_item_audit AS
SELECT
    m.menu_item_id,
    m.sku,
    m.item_name,
    m.item_name AS menu_item_name,
    mc.category_name,
    m.selling_price,
    b.branch_id,
    b.branch_name,
    b.region,
    CASE
        WHEN r.recipe_id IS NULL OR COUNT(ri.recipe_item_id) = 0 THEN 'Missing Recipe'
        ELSE 'Mapped'
    END AS recipe_status,
    COUNT(DISTINCT ri.recipe_item_id) AS ingredient_count,
    COALESCE(SUM(s.quantity), 0) AS units_sold,
    COALESCE(SUM(s.quantity), 0) AS total_units_sold,
    COALESCE(SUM(s.total_amount), 0.00) AS total_revenue,
    CASE
        WHEN r.recipe_id IS NULL OR COUNT(ri.recipe_item_id) = 0 THEN 'CRITICAL: Menu item sold without recipe BOM - unattributed ingredient drain'
        ELSE 'Healthy: Recipe mapped'
    END AS audit_recommendation
FROM menu_items m
JOIN menu_categories mc ON m.category_id = mc.category_id
CROSS JOIN branches b
LEFT JOIN recipes r ON m.menu_item_id = r.menu_item_id AND r.is_active = TRUE
LEFT JOIN recipe_ingredients ri ON r.recipe_id = ri.recipe_id
LEFT JOIN sales s ON m.menu_item_id = s.menu_item_id AND b.branch_id = s.branch_id
GROUP BY m.menu_item_id, m.sku, m.item_name, mc.category_name, m.selling_price, b.branch_id, b.branch_name, b.region, r.recipe_id
ORDER BY b.branch_id, m.menu_item_id;

COMMENT ON VIEW vw_menu_item_audit IS 'Audit of menu items identifying mapped vs missing recipes and sales revenue per branch.';

-- ------------------------------------------------------------------------------
-- 2. VIEW: vw_inventory_reconciliation (CORE RECONCILIATION ENGINE)
-- Reconciles:
--   Beginning Stock (B) + Purchases (P) - Ending Stock (E) = Actual Usage (AU)
--   Theoretical Usage (TU) from Sales BOM
--   Logged Waste (W) from kitchen logs
--   Total Variance = Actual Usage - Theoretical Usage
--   Unexplained Variance ("The Leak") = Actual Usage - Theoretical Usage - Logged Waste
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_inventory_reconciliation AS
WITH branch_ingredients AS (
    SELECT
        b.branch_id,
        b.branch_name,
        b.city,
        b.region,
        i.ingredient_id,
        i.sku,
        i.ingredient_name,
        c.category_name,
        c.category_name AS category,
        i.base_unit,
        i.cost_per_base_unit
    FROM branches b
    CROSS JOIN ingredients i
    JOIN categories c ON i.category_id = c.category_id
    WHERE b.is_active = TRUE AND i.is_active = TRUE
),
purchases_agg AS (
    SELECT
        p.branch_id,
        p.ingredient_id,
        SUM(p.quantity * COALESCE(uc.multiplier, 1.0)) AS total_purchased_qty,
        SUM(p.total_cost) AS total_purchased_cost
    FROM purchases p
    JOIN ingredients i ON p.ingredient_id = i.ingredient_id
    LEFT JOIN unit_conversions uc ON p.unit = uc.from_unit AND i.base_unit = uc.to_unit
    GROUP BY p.branch_id, p.ingredient_id
),
theoretical_agg AS (
    SELECT
        s.branch_id,
        ri.ingredient_id,
        SUM(
            s.quantity * (ri.quantity * COALESCE(uc.multiplier, 1.0))
            * (1.0 + COALESCE(ri.prep_waste_pct, 0.0) / 100.0)
            / (COALESCE(i.yield_pct, 100.0) / 100.0)
        ) AS theoretical_usage_qty
    FROM sales s
    JOIN recipes r ON s.menu_item_id = r.menu_item_id AND r.is_active = TRUE
    JOIN recipe_ingredients ri ON r.recipe_id = ri.recipe_id
    JOIN ingredients i ON ri.ingredient_id = i.ingredient_id
    LEFT JOIN unit_conversions uc ON ri.unit = uc.from_unit AND i.base_unit = uc.to_unit
    GROUP BY s.branch_id, ri.ingredient_id
),
waste_agg AS (
    SELECT
        w.branch_id,
        w.ingredient_id,
        SUM(w.quantity * COALESCE(uc.multiplier, 1.0)) AS logged_waste_qty,
        SUM(w.estimated_cost) AS logged_waste_cost
    FROM waste_logs w
    JOIN ingredients i ON w.ingredient_id = i.ingredient_id
    LEFT JOIN unit_conversions uc ON w.unit = uc.from_unit AND i.base_unit = uc.to_unit
    GROUP BY w.branch_id, w.ingredient_id
),
beginning_counts AS (
    SELECT
        ic.branch_id,
        ic.ingredient_id,
        SUM(ic.quantity * COALESCE(uc.multiplier, 1.0)) AS beginning_stock_qty
    FROM inventory_counts ic
    JOIN ingredients i ON ic.ingredient_id = i.ingredient_id
    LEFT JOIN unit_conversions uc ON ic.unit = uc.from_unit AND i.base_unit = uc.to_unit
    WHERE ic.count_type = 'BEGINNING'
    GROUP BY ic.branch_id, ic.ingredient_id
),
ending_counts AS (
    SELECT
        ic.branch_id,
        ic.ingredient_id,
        SUM(ic.quantity * COALESCE(uc.multiplier, 1.0)) AS ending_stock_qty
    FROM inventory_counts ic
    JOIN ingredients i ON ic.ingredient_id = i.ingredient_id
    LEFT JOIN unit_conversions uc ON ic.unit = uc.from_unit AND i.base_unit = uc.to_unit
    WHERE ic.count_type = 'ENDING'
    GROUP BY ic.branch_id, ic.ingredient_id
)
SELECT
    bi.branch_id,
    bi.branch_name,
    bi.region,
    bi.ingredient_id,
    bi.sku,
    bi.ingredient_name,
    bi.category_name,
    bi.category,
    bi.base_unit,
    bi.cost_per_base_unit,

    -- Physical Inventory Counts (in base unit)
    ROUND(COALESCE(bc.beginning_stock_qty, 0.0), 2) AS beginning_stock_qty,
    ROUND(COALESCE(ec.ending_stock_qty, 0.0), 2) AS ending_stock_qty,

    -- Purchases Received (in base unit)
    ROUND(COALESCE(pa.total_purchased_qty, 0.0), 2) AS total_purchased_qty,
    ROUND(COALESCE(pa.total_purchased_qty, 0.0), 2) AS purchased_base_qty,
    ROUND(COALESCE(pa.total_purchased_cost, 0.0), 2) AS total_purchased_cost,

    -- Actual Usage (B + P - E)
    ROUND(
        COALESCE(bc.beginning_stock_qty, 0.0) + COALESCE(pa.total_purchased_qty, 0.0) - COALESCE(ec.ending_stock_qty, 0.0),
        2
    ) AS actual_usage_qty,
    ROUND(
        (COALESCE(bc.beginning_stock_qty, 0.0) + COALESCE(pa.total_purchased_qty, 0.0) - COALESCE(ec.ending_stock_qty, 0.0)) * bi.cost_per_base_unit,
        2
    ) AS actual_usage_cost,

    -- Theoretical Usage from Sales
    ROUND(COALESCE(ta.theoretical_usage_qty, 0.0), 2) AS theoretical_usage_qty,
    ROUND(COALESCE(ta.theoretical_usage_qty, 0.0), 2) AS theoretical_used_qty,
    ROUND(COALESCE(ta.theoretical_usage_qty, 0.0) * bi.cost_per_base_unit, 2) AS theoretical_usage_cost,

    -- Logged Waste
    ROUND(COALESCE(wa.logged_waste_qty, 0.0), 2) AS logged_waste_qty,
    ROUND(COALESCE(wa.logged_waste_cost, 0.0), 2) AS logged_waste_cost,

    -- Total Variance (Actual Usage - Theoretical Usage)
    ROUND(
        (COALESCE(bc.beginning_stock_qty, 0.0) + COALESCE(pa.total_purchased_qty, 0.0) - COALESCE(ec.ending_stock_qty, 0.0))
        - COALESCE(ta.theoretical_usage_qty, 0.0),
        2
    ) AS total_variance_qty,
    ROUND(
        (
            (COALESCE(bc.beginning_stock_qty, 0.0) + COALESCE(pa.total_purchased_qty, 0.0) - COALESCE(ec.ending_stock_qty, 0.0))
            - COALESCE(ta.theoretical_usage_qty, 0.0)
        ) * bi.cost_per_base_unit,
        2
    ) AS total_variance_cost,

    -- Unexplained Variance (Actual Usage - Theoretical Usage - Logged Waste)
    ROUND(
        (COALESCE(bc.beginning_stock_qty, 0.0) + COALESCE(pa.total_purchased_qty, 0.0) - COALESCE(ec.ending_stock_qty, 0.0))
        - COALESCE(ta.theoretical_usage_qty, 0.0)
        - COALESCE(wa.logged_waste_qty, 0.0),
        2
    ) AS unexplained_variance_qty,
    ROUND(
        (
            (COALESCE(bc.beginning_stock_qty, 0.0) + COALESCE(pa.total_purchased_qty, 0.0) - COALESCE(ec.ending_stock_qty, 0.0))
            - COALESCE(ta.theoretical_usage_qty, 0.0)
            - COALESCE(wa.logged_waste_qty, 0.0)
        ) * bi.cost_per_base_unit,
        2
    ) AS unexplained_variance_cost,
    ROUND(
        (
            (COALESCE(bc.beginning_stock_qty, 0.0) + COALESCE(pa.total_purchased_qty, 0.0) - COALESCE(ec.ending_stock_qty, 0.0))
            - COALESCE(ta.theoretical_usage_qty, 0.0)
            - COALESCE(wa.logged_waste_qty, 0.0)
        ) * bi.cost_per_base_unit,
        2
    ) AS unexplained_loss_amount,

    -- Unexplained Variance % (relative to Theoretical)
    ROUND(
        CASE
            WHEN COALESCE(ta.theoretical_usage_qty, 0.0) > 0 THEN
                (
                    (
                        (COALESCE(bc.beginning_stock_qty, 0.0) + COALESCE(pa.total_purchased_qty, 0.0) - COALESCE(ec.ending_stock_qty, 0.0))
                        - COALESCE(ta.theoretical_usage_qty, 0.0)
                        - COALESCE(wa.logged_waste_qty, 0.0)
                    ) / ta.theoretical_usage_qty
                ) * 100.0
            ELSE 0.0
        END,
        2
    ) AS unexplained_variance_pct,
    ROUND(
        CASE
            WHEN COALESCE(ta.theoretical_usage_qty, 0.0) > 0 THEN
                (
                    (
                        (COALESCE(bc.beginning_stock_qty, 0.0) + COALESCE(pa.total_purchased_qty, 0.0) - COALESCE(ec.ending_stock_qty, 0.0))
                        - COALESCE(ta.theoretical_usage_qty, 0.0)
                        - COALESCE(wa.logged_waste_qty, 0.0)
                    ) / ta.theoretical_usage_qty
                ) * 100.0
            ELSE 0.0
        END,
        2
    ) AS variance_pct,

    -- Waste % of Purchases
    ROUND(
        CASE
            WHEN COALESCE(pa.total_purchased_qty, 0.0) > 0 THEN
                (COALESCE(wa.logged_waste_qty, 0.0) / pa.total_purchased_qty) * 100.0
            ELSE 0.0
        END,
        2
    ) AS waste_pct_of_purchases,

    -- Status Anomaly Classification
    CASE
        WHEN (
            COALESCE(ta.theoretical_usage_qty, 0.0) > 0 AND (
                (
                    (COALESCE(bc.beginning_stock_qty, 0.0) + COALESCE(pa.total_purchased_qty, 0.0) - COALESCE(ec.ending_stock_qty, 0.0))
                    - COALESCE(ta.theoretical_usage_qty, 0.0)
                    - COALESCE(wa.logged_waste_qty, 0.0)
                ) / ta.theoretical_usage_qty * 100.0
            ) >= 15.0
        ) THEN 'Flagged for Review'

        WHEN (
            COALESCE(pa.total_purchased_qty, 0.0) > 0 AND (
                COALESCE(wa.logged_waste_qty, 0.0) / pa.total_purchased_qty * 100.0
            ) >= 12.0
        ) THEN 'Excess Waste Logged'

        WHEN (
            COALESCE(ta.theoretical_usage_qty, 0.0) > 0 AND (
                (
                    (COALESCE(bc.beginning_stock_qty, 0.0) + COALESCE(pa.total_purchased_qty, 0.0) - COALESCE(ec.ending_stock_qty, 0.0))
                    - COALESCE(ta.theoretical_usage_qty, 0.0)
                ) / ta.theoretical_usage_qty * 100.0
            ) <= -10.0
        ) THEN 'Under-portioning / Audit Count'

        ELSE 'Normal Tolerance'
    END AS status,

    -- Probable Cause classification alias
    CASE
        WHEN (
            COALESCE(ta.theoretical_usage_qty, 0.0) > 0 AND (
                (
                    (COALESCE(bc.beginning_stock_qty, 0.0) + COALESCE(pa.total_purchased_qty, 0.0) - COALESCE(ec.ending_stock_qty, 0.0))
                    - COALESCE(ta.theoretical_usage_qty, 0.0)
                    - COALESCE(wa.logged_waste_qty, 0.0)
                ) / ta.theoretical_usage_qty * 100.0
            ) >= 15.0
        ) THEN 'High Unexplained Shrinkage'

        WHEN (
            COALESCE(pa.total_purchased_qty, 0.0) > 0 AND (
                COALESCE(wa.logged_waste_qty, 0.0) / pa.total_purchased_qty * 100.0
            ) >= 12.0
        ) THEN 'Excess Spoilage'

        ELSE 'Within Tolerance'
    END AS probable_cause

FROM branch_ingredients bi
LEFT JOIN purchases_agg pa ON bi.branch_id = pa.branch_id AND bi.ingredient_id = pa.ingredient_id
LEFT JOIN theoretical_agg ta ON bi.branch_id = ta.branch_id AND bi.ingredient_id = ta.ingredient_id
LEFT JOIN waste_agg wa ON bi.branch_id = wa.branch_id AND bi.ingredient_id = wa.ingredient_id
LEFT JOIN beginning_counts bc ON bi.branch_id = bc.branch_id AND bi.ingredient_id = bc.ingredient_id
LEFT JOIN ending_counts ec ON bi.branch_id = ec.branch_id AND bi.ingredient_id = ec.ingredient_id
ORDER BY bi.branch_id, bi.ingredient_id;

COMMENT ON VIEW vw_inventory_reconciliation IS 'Master reconciliation of Beginning + Purchases - Ending against Theoretical Usage and Waste.';

-- ------------------------------------------------------------------------------
-- 3. VIEW: vw_normalized_waste
-- Normalized kitchen waste log with base unit quantities and financial costs.
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_normalized_waste AS
SELECT
    w.waste_id,
    w.branch_id,
    b.branch_name,
    b.region,
    w.ingredient_id,
    i.sku AS ingredient_sku,
    i.ingredient_name,
    c.category_name,
    c.category_name AS category,
    w.waste_date,
    w.quantity AS logged_quantity,
    w.unit AS logged_unit,
    ROUND(w.quantity * COALESCE(uc.multiplier, 1.0), 2) AS waste_quantity_base,
    i.base_unit,
    w.reason AS reason_code,
    wr.reason_name,
    wr.is_preventable,
    w.estimated_cost AS waste_cost_inr,
    w.recorded_by,
    w.notes
FROM waste_logs w
JOIN branches b ON w.branch_id = b.branch_id
JOIN ingredients i ON w.ingredient_id = i.ingredient_id
JOIN categories c ON i.category_id = c.category_id
JOIN waste_reasons wr ON w.reason = wr.reason_code
LEFT JOIN unit_conversions uc ON w.unit = uc.from_unit AND i.base_unit = uc.to_unit
ORDER BY w.waste_date DESC, w.waste_id DESC;

COMMENT ON VIEW vw_normalized_waste IS 'Granular kitchen waste logs normalized to ingredient base units with costs in INR.';

-- ------------------------------------------------------------------------------
-- 4. VIEW: vw_branch_variance_summary
-- Executive scorecard rolled up by branch.
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_branch_variance_summary AS
WITH branch_sales AS (
    SELECT
        branch_id,
        SUM(quantity) AS total_items_sold,
        SUM(total_amount) AS total_sales_revenue
    FROM sales
    GROUP BY branch_id
)
SELECT
    b.branch_id,
    b.branch_code,
    b.branch_name,
    b.region,
    COALESCE(bs.total_items_sold, 0) AS total_items_sold,
    ROUND(COALESCE(bs.total_sales_revenue, 0.0), 2) AS total_sales_revenue,
    ROUND(SUM(r.total_purchased_cost), 2) AS total_purchased_cost,
    ROUND(SUM(r.theoretical_usage_cost), 2) AS total_theoretical_cost,
    ROUND(SUM(r.logged_waste_cost), 2) AS total_waste_cost,
    ROUND(SUM(r.unexplained_variance_cost), 2) AS total_unexplained_leak_cost,
    ROUND(
        CASE
            WHEN SUM(r.theoretical_usage_cost) > 0 THEN
                (SUM(r.unexplained_variance_cost) / SUM(r.theoretical_usage_cost)) * 100.0
            ELSE 0.0
        END,
        2
    ) AS branch_leak_pct,
    COUNT(CASE WHEN r.status = 'Flagged for Review' THEN 1 END) AS flagged_items_count
FROM branches b
JOIN vw_inventory_reconciliation r ON b.branch_id = r.branch_id
LEFT JOIN branch_sales bs ON b.branch_id = bs.branch_id
GROUP BY b.branch_id, b.branch_code, b.branch_name, b.region, bs.total_items_sold, bs.total_sales_revenue
ORDER BY total_unexplained_leak_cost DESC;

COMMENT ON VIEW vw_branch_variance_summary IS 'Branch executive scorecard summarizing sales, food costs, waste, and shrinkage.';

-- ------------------------------------------------------------------------------
-- 5. VIEW: vw_recipe_costing
-- Recipe costing, BOM component costs, contribution margins and food cost %.
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_recipe_costing AS
WITH ingredient_costs AS (
    SELECT
        r.recipe_id,
        r.menu_item_id,
        ri.ingredient_id,
        ri.quantity,
        ri.unit,
        (ri.quantity * COALESCE(uc.multiplier, 1.0)) AS qty_in_base,
        (
            (ri.quantity * COALESCE(uc.multiplier, 1.0))
            * (1.0 + COALESCE(ri.prep_waste_pct, 0.0) / 100.0)
            / (COALESCE(i.yield_pct, 100.0) / 100.0)
            * i.cost_per_base_unit
        ) AS ingredient_cost
    FROM recipes r
    JOIN recipe_ingredients ri ON r.recipe_id = ri.recipe_id
    JOIN ingredients i ON ri.ingredient_id = i.ingredient_id
    LEFT JOIN unit_conversions uc ON ri.unit = uc.from_unit AND i.base_unit = uc.to_unit
    WHERE r.is_active = TRUE
)
SELECT
    m.menu_item_id,
    m.sku,
    m.item_name,
    mc.category_name,
    m.selling_price,
    r.yield_servings,
    COUNT(ic.ingredient_id) AS ingredient_count,
    ROUND(SUM(ic.ingredient_cost) / r.yield_servings, 2) AS portion_cost,
    ROUND(m.selling_price - (SUM(ic.ingredient_cost) / r.yield_servings), 2) AS gross_margin,
    ROUND(
        CASE
            WHEN m.selling_price > 0 THEN ((SUM(ic.ingredient_cost) / r.yield_servings) / m.selling_price) * 100.0
            ELSE 0.0
        END,
        2
    ) AS food_cost_pct
FROM menu_items m
JOIN menu_categories mc ON m.category_id = mc.category_id
JOIN recipes r ON m.menu_item_id = r.menu_item_id
LEFT JOIN ingredient_costs ic ON r.recipe_id = ic.recipe_id
GROUP BY m.menu_item_id, m.sku, m.item_name, mc.category_name, m.selling_price, r.yield_servings;

COMMENT ON VIEW vw_recipe_costing IS 'Menu item portion costs, gross margins, and food cost percentages.';

-- ------------------------------------------------------------------------------
-- 6. VIEW: vw_daily_food_cost_kpis
-- Daily sales and food cost metrics over time for Plotly line charts.
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_daily_food_cost_kpis AS
WITH daily_sales AS (
    SELECT
        sale_date AS business_date,
        branch_id,
        SUM(quantity) AS daily_units_sold,
        SUM(total_amount) AS daily_revenue
    FROM sales
    GROUP BY sale_date, branch_id
),
daily_waste AS (
    SELECT
        waste_date AS business_date,
        branch_id,
        SUM(estimated_cost) AS daily_waste_cost
    FROM waste_logs
    GROUP BY waste_date, branch_id
)
SELECT
    ds.business_date,
    b.branch_name,
    ds.daily_units_sold,
    ROUND(ds.daily_revenue, 2) AS daily_revenue,
    ROUND(COALESCE(dw.daily_waste_cost, 0.0), 2) AS daily_waste_cost,
    ROUND(
        CASE
            WHEN ds.daily_revenue > 0 THEN (COALESCE(dw.daily_waste_cost, 0.0) / ds.daily_revenue) * 100.0
            ELSE 0.0
        END,
        2
    ) AS waste_pct_of_sales
FROM daily_sales ds
JOIN branches b ON ds.branch_id = b.branch_id
LEFT JOIN daily_waste dw ON ds.business_date = dw.business_date AND ds.branch_id = dw.branch_id
ORDER BY ds.business_date, b.branch_name;

COMMENT ON VIEW vw_daily_food_cost_kpis IS 'Daily branch sales revenue, waste cost, and waste ratio over time.';

-- ------------------------------------------------------------------------------
-- 7. VIEW: vw_top_leak_radar_offenders
-- Top leakage offenders ranked by unexplained dollar loss (INR).
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_top_leak_radar_offenders AS
SELECT
    branch_name,
    ingredient_name,
    category_name,
    base_unit,
    cost_per_base_unit,
    theoretical_usage_qty,
    actual_usage_qty,
    logged_waste_qty,
    unexplained_variance_qty,
    unexplained_variance_cost,
    unexplained_variance_pct,
    status,
    probable_cause,
    DENSE_RANK() OVER (ORDER BY unexplained_variance_cost DESC) AS leak_rank
FROM vw_inventory_reconciliation
WHERE unexplained_variance_cost > 0
ORDER BY unexplained_variance_cost DESC;

COMMENT ON VIEW vw_top_leak_radar_offenders IS 'Top stock leakage offenders across all branches ranked by financial loss.';

-- ------------------------------------------------------------------------------
-- 8. VIEW: vw_waste_pareto_analysis
-- Cumulative 80/20 Pareto analysis on documented kitchen waste reasons.
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_waste_pareto_analysis AS
WITH reason_totals AS (
    SELECT
        wr.reason_code,
        wr.reason_name,
        wr.is_preventable,
        COUNT(w.waste_id) AS incident_count,
        SUM(w.estimated_cost) AS total_waste_cost
    FROM waste_reasons wr
    JOIN waste_logs w ON wr.reason_code = w.reason
    GROUP BY wr.reason_code, wr.reason_name, wr.is_preventable
),
cumulative_ranked AS (
    SELECT
        reason_code,
        reason_name,
        is_preventable,
        incident_count,
        total_waste_cost,
        SUM(total_waste_cost) OVER () AS grand_total_cost,
        SUM(total_waste_cost) OVER (ORDER BY total_waste_cost DESC) AS cumulative_cost
    FROM reason_totals
)
SELECT
    reason_code,
    reason_name,
    is_preventable,
    incident_count,
    ROUND(total_waste_cost, 2) AS total_waste_cost,
    ROUND(cumulative_cost, 2) AS cumulative_cost,
    ROUND(
        CASE
            WHEN grand_total_cost > 0 THEN (cumulative_cost / grand_total_cost) * 100.0
            ELSE 0.0
        END,
        2
    ) AS cumulative_pct,
    CASE
        WHEN (cumulative_cost / NULLIF(grand_total_cost, 0)) * 100.0 <= 80.0 THEN 'Vital Few (Top 80%)'
        ELSE 'Useful Many (Bottom 20%)'
    END AS pareto_classification
FROM cumulative_ranked
ORDER BY total_waste_cost DESC;

COMMENT ON VIEW vw_waste_pareto_analysis IS 'Pareto 80/20 analysis for kitchen waste reasons.';
