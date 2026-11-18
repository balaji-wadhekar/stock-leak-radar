-- ==============================================================================
-- File: 01_schema.sql
-- Project: Kitchen Ledger Analytics / Restaurant Inventory & Variance Visualization
-- Description: Core PostgreSQL Database DDL, Schema Architecture,
--              Multi-Branch Support, Relational Constraints, and Unit Conversions.
-- Engine: PostgreSQL 14+
-- Architect: Data Engineer & PostgreSQL Architect
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 0. SCHEMA & EXTENSION INITIALIZATION
-- ------------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS restaurant_inventory;
SET search_path TO restaurant_inventory, public;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ------------------------------------------------------------------------------
-- 1. DROP EXISTING OBJECTS (IDEMPOTENT RE-RUNS)
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS inventory_counts CASCADE;
DROP TABLE IF EXISTS waste_logs CASCADE;
DROP TABLE IF EXISTS waste_reasons CASCADE;
DROP TABLE IF EXISTS sales CASCADE;
DROP TABLE IF EXISTS purchases CASCADE;
DROP TABLE IF EXISTS suppliers CASCADE;
DROP TABLE IF EXISTS recipe_ingredients CASCADE;
DROP TABLE IF EXISTS recipes CASCADE;
DROP TABLE IF EXISTS menu_items CASCADE;
DROP TABLE IF EXISTS menu_categories CASCADE;
DROP TABLE IF EXISTS ingredients CASCADE;
DROP TABLE IF EXISTS unit_conversions CASCADE;
DROP TABLE IF EXISTS units_of_measure CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS branches CASCADE;

-- ------------------------------------------------------------------------------
-- 2. BRANCHES MASTER TABLE (MULTI-LOCATION ARCHITECTURE)
-- ------------------------------------------------------------------------------
CREATE TABLE branches (
    branch_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    branch_code VARCHAR(20) NOT NULL UNIQUE,
    branch_name VARCHAR(100) NOT NULL UNIQUE,
    city VARCHAR(50) NOT NULL DEFAULT 'Pune',
    region VARCHAR(50) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE branches IS 'Operating restaurant branches across Pune.';

-- ------------------------------------------------------------------------------
-- 3. INGREDIENT CATEGORIES
-- ------------------------------------------------------------------------------
CREATE TABLE categories (
    category_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category_name VARCHAR(50) NOT NULL UNIQUE,
    target_food_cost_pct NUMERIC(5, 2) NOT NULL DEFAULT 30.00 CHECK (target_food_cost_pct > 0 AND target_food_cost_pct <= 100),
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE categories IS 'Classification of ingredients (Dairy, Meat, Produce, Dry Goods, Beverages).';

-- ------------------------------------------------------------------------------
-- 4. UNITS OF MEASURE & UNIT CONVERSION LOOKUP ENGINE
-- ------------------------------------------------------------------------------
CREATE TABLE units_of_measure (
    uom_code VARCHAR(20) PRIMARY KEY,
    uom_name VARCHAR(50) NOT NULL,
    dimension VARCHAR(20) NOT NULL CHECK (dimension IN ('MASS', 'VOLUME', 'COUNT', 'PACKAGE')),
    is_base_unit BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT
);

COMMENT ON TABLE units_of_measure IS 'Physical measurement units.';

CREATE TABLE unit_conversions (
    conversion_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    from_unit VARCHAR(20) NOT NULL REFERENCES units_of_measure(uom_code) ON DELETE RESTRICT,
    to_unit VARCHAR(20) NOT NULL REFERENCES units_of_measure(uom_code) ON DELETE RESTRICT,
    multiplier NUMERIC(16, 8) NOT NULL CHECK (multiplier > 0),
    dimension VARCHAR(20) NOT NULL CHECK (dimension IN ('MASS', 'VOLUME', 'COUNT', 'PACKAGE')),
    CONSTRAINT uq_conversion_pair UNIQUE (from_unit, to_unit)
);

COMMENT ON TABLE unit_conversions IS 'Conversion multipliers: quantity_in_to_unit = quantity_in_from_unit * multiplier.';

-- ------------------------------------------------------------------------------
-- 5. INGREDIENTS MASTER TABLE
-- ------------------------------------------------------------------------------
CREATE TABLE ingredients (
    ingredient_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sku VARCHAR(30) NOT NULL UNIQUE,
    ingredient_name VARCHAR(100) NOT NULL UNIQUE,
    category_id INT NOT NULL REFERENCES categories(category_id) ON DELETE RESTRICT,
    base_unit VARCHAR(20) NOT NULL REFERENCES units_of_measure(uom_code) ON DELETE RESTRICT,
    cost_per_base_unit NUMERIC(12, 4) NOT NULL CHECK (cost_per_base_unit >= 0),
    par_level NUMERIC(12, 4) NOT NULL DEFAULT 0 CHECK (par_level >= 0),
    yield_pct NUMERIC(5, 2) NOT NULL DEFAULT 100.00 CHECK (yield_pct > 0 AND yield_pct <= 100.00),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE ingredients IS 'Raw ingredient catalog with unit costs in INR per base unit (g, ml, pcs).';

-- ------------------------------------------------------------------------------
-- 6. MENU ITEMS & RECIPES (BILL OF MATERIALS)
-- ------------------------------------------------------------------------------
CREATE TABLE menu_categories (
    category_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category_name VARCHAR(50) NOT NULL UNIQUE,
    display_order INT NOT NULL DEFAULT 0
);

CREATE TABLE menu_items (
    menu_item_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sku VARCHAR(30) NOT NULL UNIQUE,
    item_name VARCHAR(100) NOT NULL UNIQUE,
    category_id INT NOT NULL REFERENCES menu_categories(category_id) ON DELETE RESTRICT,
    selling_price NUMERIC(10, 2) NOT NULL CHECK (selling_price >= 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE menu_items IS 'POS Menu Items sold to customers.';

CREATE TABLE recipes (
    recipe_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    menu_item_id INT NOT NULL UNIQUE REFERENCES menu_items(menu_item_id) ON DELETE CASCADE,
    recipe_name VARCHAR(100) NOT NULL,
    yield_servings NUMERIC(6, 2) NOT NULL DEFAULT 1.00 CHECK (yield_servings > 0),
    prep_notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE recipes IS 'Recipe master linking menu items to ingredients.';

CREATE TABLE recipe_ingredients (
    recipe_item_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    recipe_id INT NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    ingredient_id INT NOT NULL REFERENCES ingredients(ingredient_id) ON DELETE RESTRICT,
    quantity NUMERIC(12, 4) NOT NULL CHECK (quantity > 0),
    unit VARCHAR(20) NOT NULL REFERENCES units_of_measure(uom_code) ON DELETE RESTRICT,
    prep_waste_pct NUMERIC(5, 2) NOT NULL DEFAULT 0.00 CHECK (prep_waste_pct >= 0 AND prep_waste_pct < 100.00),
    CONSTRAINT uq_recipe_ingredient UNIQUE (recipe_id, ingredient_id)
);

COMMENT ON TABLE recipe_ingredients IS 'Recipe Bill of Materials (BOM) per portion.';

-- ------------------------------------------------------------------------------
-- 7. SUPPLIERS & PURCHASES (BULK RECEIVING)
-- ------------------------------------------------------------------------------
CREATE TABLE suppliers (
    supplier_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    supplier_code VARCHAR(20) NOT NULL UNIQUE,
    supplier_name VARCHAR(100) NOT NULL,
    contact_email VARCHAR(100),
    phone VARCHAR(30),
    payment_terms VARCHAR(50) DEFAULT 'Net 30',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE purchases (
    purchase_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    branch_id INT NOT NULL REFERENCES branches(branch_id) ON DELETE RESTRICT,
    ingredient_id INT NOT NULL REFERENCES ingredients(ingredient_id) ON DELETE RESTRICT,
    supplier_id INT REFERENCES suppliers(supplier_id) ON DELETE SET NULL,
    purchase_date DATE NOT NULL,
    invoice_no VARCHAR(50) NOT NULL,
    quantity NUMERIC(12, 4) NOT NULL CHECK (quantity > 0),
    unit VARCHAR(20) NOT NULL REFERENCES units_of_measure(uom_code) ON DELETE RESTRICT,
    unit_cost NUMERIC(12, 4) NOT NULL CHECK (unit_cost >= 0),
    total_cost NUMERIC(12, 2) NOT NULL CHECK (total_cost >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE purchases IS 'Inventory purchase receiving records per branch in bulk units (kg, lb, L, dozen, pcs).';

-- ------------------------------------------------------------------------------
-- 8. POS SALES (TRANSACTIONAL DEPLETION)
-- ------------------------------------------------------------------------------
CREATE TABLE sales (
    sale_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    branch_id INT NOT NULL REFERENCES branches(branch_id) ON DELETE RESTRICT,
    menu_item_id INT NOT NULL REFERENCES menu_items(menu_item_id) ON DELETE RESTRICT,
    sale_date DATE NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10, 2) NOT NULL CHECK (unit_price >= 0),
    total_amount NUMERIC(10, 2) NOT NULL CHECK (total_amount >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE sales IS 'POS sales orders aggregated daily per branch and menu item.';

-- ------------------------------------------------------------------------------
-- 9. WASTE & SPOILAGE AUDIT LOGS
-- ------------------------------------------------------------------------------
CREATE TABLE waste_reasons (
    reason_code VARCHAR(50) PRIMARY KEY,
    reason_name VARCHAR(100) NOT NULL,
    is_preventable BOOLEAN NOT NULL DEFAULT TRUE,
    description TEXT
);

CREATE TABLE waste_logs (
    waste_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    branch_id INT NOT NULL REFERENCES branches(branch_id) ON DELETE RESTRICT,
    ingredient_id INT NOT NULL REFERENCES ingredients(ingredient_id) ON DELETE RESTRICT,
    waste_date DATE NOT NULL,
    quantity NUMERIC(12, 4) NOT NULL CHECK (quantity > 0),
    unit VARCHAR(20) NOT NULL REFERENCES units_of_measure(uom_code) ON DELETE RESTRICT,
    reason VARCHAR(50) NOT NULL REFERENCES waste_reasons(reason_code) ON DELETE RESTRICT,
    estimated_cost NUMERIC(12, 2) NOT NULL CHECK (estimated_cost >= 0),
    recorded_by VARCHAR(50) NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE waste_logs IS 'Documented kitchen waste logs tracking intentional scrap & spoilage.';

-- ------------------------------------------------------------------------------
-- 10. PHYSICAL INVENTORY COUNT AUDITS
-- ------------------------------------------------------------------------------
CREATE TABLE inventory_counts (
    count_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    branch_id INT NOT NULL REFERENCES branches(branch_id) ON DELETE RESTRICT,
    ingredient_id INT NOT NULL REFERENCES ingredients(ingredient_id) ON DELETE RESTRICT,
    count_date DATE NOT NULL,
    quantity NUMERIC(12, 4) NOT NULL CHECK (quantity >= 0),
    unit VARCHAR(20) NOT NULL REFERENCES units_of_measure(uom_code) ON DELETE RESTRICT,
    count_type VARCHAR(20) NOT NULL CHECK (count_type IN ('BEGINNING', 'CYCLE', 'ENDING')),
    conducted_by VARCHAR(50) NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_branch_ing_count UNIQUE (branch_id, ingredient_id, count_date, count_type)
);

COMMENT ON TABLE inventory_counts IS 'Physical stock takes (Beginning count at start of 30-day period, Ending count at end).';

-- ------------------------------------------------------------------------------
-- 11. UNIT CONVERSION STORED FUNCTION
-- ------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_convert_unit(
    p_quantity NUMERIC,
    p_from_unit VARCHAR,
    p_to_unit VARCHAR
)
RETURNS NUMERIC
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    v_multiplier NUMERIC(16, 8);
BEGIN
    IF p_quantity IS NULL THEN
        RETURN NULL;
    END IF;
    
    IF p_from_unit = p_to_unit THEN
        RETURN p_quantity;
    END IF;

    -- Look up direct multiplier
    SELECT multiplier INTO v_multiplier
    FROM restaurant_inventory.unit_conversions
    WHERE from_unit = p_from_unit AND to_unit = p_to_unit;

    IF FOUND THEN
        RETURN p_quantity * v_multiplier;
    END IF;

    -- Look up inverse multiplier
    SELECT multiplier INTO v_multiplier
    FROM restaurant_inventory.unit_conversions
    WHERE from_unit = p_to_unit AND to_unit = p_from_unit;

    IF FOUND THEN
        RETURN p_quantity / v_multiplier;
    END IF;

    RAISE EXCEPTION 'No unit conversion rule exists between "%" and "%"', p_from_unit, p_to_unit;
END;
$$;

-- ------------------------------------------------------------------------------
-- 12. PERFORMANCE INDEXES
-- ------------------------------------------------------------------------------
CREATE INDEX idx_purchases_branch_date ON purchases(branch_id, purchase_date);
CREATE INDEX idx_purchases_ingredient ON purchases(ingredient_id);
CREATE INDEX idx_sales_branch_date ON sales(branch_id, sale_date);
CREATE INDEX idx_sales_menu_item ON sales(menu_item_id);
CREATE INDEX idx_waste_branch_date ON waste_logs(branch_id, waste_date);
CREATE INDEX idx_waste_ingredient ON waste_logs(ingredient_id);
CREATE INDEX idx_counts_branch_date ON inventory_counts(branch_id, count_date);
CREATE INDEX idx_recipe_ingredients_recipe ON recipe_ingredients(recipe_id);
CREATE INDEX idx_recipe_ingredients_ing ON recipe_ingredients(ingredient_id);
CREATE INDEX idx_unit_conv_pair ON unit_conversions(from_unit, to_unit);
