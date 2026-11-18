"""
==============================================================================
Script: generate_seed.py
Project: Kitchen Ledger Analytics / Restaurant Inventory & Variance Visualization
Description: Deterministic Python seed generator (random.seed(42)) creating 30 days
             of realistic restaurant operations across 4 Pune branches, mixed
             measurement units, and 4 deliberate analytical anomaly stories.
Output: sql/02_seed_data.sql
Execution: python scripts/generate_seed.py [--execute] [--db-url <url>]
==============================================================================
"""

import os
import sys
import random
import argparse
from datetime import datetime, timedelta

def generate_seed_data(output_sql_path: str, execute_db: bool = False, db_url: str = None):
    # Set deterministic random seed
    random.seed(42)
    print("=" * 80)
    print("KITCHEN LEDGER ANALYTICS - SEED DATA GENERATOR")
    print("Random Seed: 42 (Deterministic & Reproducible)")
    print("Simulation Period: Last 30 Days (CURRENT_DATE - INTERVAL '30 days' to CURRENT_DATE)")
    print("=" * 80)

    # --------------------------------------------------------------------------
    # 1. MASTER REFERENCE DEFINITIONS
    # --------------------------------------------------------------------------
    branches = [
        (1, 'KP-01', 'Koregaon Park Flagship', 'Pune', 'Pune, Central'),
        (2, 'HINJ-02', 'Hinjawadi IT Park', 'Pune', 'Pune, West'),
        (3, 'VN-03', 'Viman Nagar Hub', 'Pune', 'Pune, East'),
        (4, 'BAN-04', 'Baner High Street', 'Pune', 'Pune, North-West')
    ]

    categories = [
        (1, 'Dairy', 28.00, 'Dairy products including cheese, cream, butter'),
        (2, 'Meat', 32.00, 'Fresh poultry, mutton and butchery proteins'),
        (3, 'Produce', 25.00, 'Fresh farm vegetables, herbs and aromatics'),
        (4, 'Dry Goods', 20.00, 'Flours, extra virgin olive oil, bakery grains'),
        (5, 'Beverages', 18.00, 'Specialty coffee beans, syrups, and bar ingredients')
    ]

    units_of_measure = [
        # Mass
        ('g',     'Gram',         'MASS',    True,  'Base unit of mass'),
        ('kg',    'Kilogram',     'MASS',    False, '1 kg = 1000 g'),
        ('oz',    'Ounce (wt)',   'MASS',    False, '1 oz = 28.34952 g'),
        ('lb',    'Pound',        'MASS',    False, '1 lb = 453.59237 g'),
        # Volume
        ('ml',    'Milliliter',   'VOLUME',  True,  'Base unit of volume'),
        ('l',     'Liter (l)',    'VOLUME',  False, '1 l = 1000 ml'),
        ('L',     'Liter (L)',    'VOLUME',  False, '1 L = 1000 ml'),
        ('tbsp',  'Tablespoon',   'VOLUME',  False, '1 tbsp = 15 ml'),
        ('tsp',   'Teaspoon',     'VOLUME',  False, '1 tsp = 5 ml'),
        ('fl_oz', 'Fluid Ounce',  'VOLUME',  False, '1 fl oz = 29.5735 ml'),
        ('cup',   'Cup (US)',     'VOLUME',  False, '1 cup = 240 ml'),
        # Count
        ('pcs',   'Pieces / Unit','COUNT',   True,  'Base discrete unit'),
        ('dozen', 'Dozen (12x)',  'COUNT',   False, '1 dozen = 12 pcs')
    ]

    unit_conversions = [
        # To Base Unit: g (Mass)
        ('g',     'g',   1.00000000,   'MASS'),
        ('kg',    'g',   1000.00000000,'MASS'),
        ('oz',    'g',   28.34952313,  'MASS'),
        ('lb',    'g',   453.59237000, 'MASS'),
        ('tsp',   'g',   5.00000000,   'MASS'),
        ('tbsp',  'g',   15.00000000,  'MASS'),
        ('ml',    'g',   1.00000000,   'MASS'),
        ('l',     'g',   1000.00000000,'MASS'),
        ('L',     'g',   1000.00000000,'MASS'),
        # To Base Unit: ml (Volume)
        ('ml',    'ml',  1.00000000,   'VOLUME'),
        ('l',     'ml',  1000.00000000,'VOLUME'),
        ('L',     'ml',  1000.00000000,'VOLUME'),
        ('tbsp',  'ml',  15.00000000,  'VOLUME'),
        ('tsp',   'ml',  5.00000000,   'VOLUME'),
        ('fl_oz', 'ml',  29.57352956,  'VOLUME'),
        ('cup',   'ml',  240.00000000, 'VOLUME'),
        ('g',     'ml',  1.00000000,   'VOLUME'),
        ('kg',    'ml',  1000.00000000,'VOLUME'),
        # To Base Unit: pcs (Count)
        ('pcs',   'pcs', 1.00000000,   'COUNT'),
        ('dozen', 'pcs', 12.00000000,  'COUNT')
    ]

    # Pre-build conversion map in python for accurate math verification
    conv_map = {(row[0], row[1]): row[2] for row in unit_conversions}

    # 12 Ingredients
    ingredients = [
        # id, sku, name, cat_id, base_unit, cost_per_base_unit, par_level, yield_pct
        (1,  'ING-DAI-001', 'Mozzarella Cheese',       1, 'g',   0.6500, 20000.0, 100.0),
        (2,  'ING-DAI-002', 'Fresh Cream',             1, 'ml',  0.2800, 15000.0, 100.0),
        (3,  'ING-DAI-003', 'Salted Butter',           1, 'g',   0.5500, 10000.0, 100.0),
        (4,  'ING-MEA-001', 'Boneless Chicken Breast', 2, 'g',   0.4200, 30000.0, 95.0),
        (5,  'ING-MEA-002', 'Mutton Keema',            2, 'g',   0.7500, 20000.0, 98.0),
        (6,  'ING-PRO-001', 'Fresh Tomatoes',          3, 'g',   0.0600, 40000.0, 92.0),
        (7,  'ING-PRO-002', 'Capsicum & Bell Peppers', 3, 'g',   0.0900, 15000.0, 90.0),
        (8,  'ING-PRO-003', 'Fresh Basil & Herbs',     3, 'g',   0.3500, 4000.0,  85.0),
        (9,  'ING-DRY-001', 'Pizza Flour (00)',        4, 'g',   0.0800, 50000.0, 100.0),
        (10, 'ING-DRY-002', 'Extra Virgin Olive Oil',  4, 'ml',  0.8500, 12000.0, 100.0),
        (11, 'ING-BEV-001', 'Espresso Coffee Beans',   5, 'g',   1.2000, 6000.0,  100.0),
        (12, 'ING-DRY-003', 'Artisanal Burger Buns',   4, 'pcs', 18.0000, 400.0,  100.0)
    ]
    ing_dict = {ing[0]: {'name': ing[2], 'cat': ing[3], 'unit': ing[4], 'cost': ing[5], 'par': ing[6], 'yield': ing[7]} for ing in ingredients}

    menu_categories = [
        (1, 'Artisan Pizza', 1),
        (2, 'Gourmet Burgers', 2),
        (3, 'Handcrafted Mains & Flatbreads', 3),
        (4, 'Fresh Pastas', 4),
        (5, 'Specialty Coffee & Beverages', 5)
    ]

    menu_items = [
        # id, sku, name, cat_id, price, mapped_in_recipes
        (1, 'MNU-PIZ-001', 'Margherita Artisan Pizza',   1, 380.00, True),
        (2, 'MNU-PIZ-002', 'Peri-Peri Chicken Pizza',    1, 480.00, True),
        (3, 'MNU-BUR-001', 'Smoked Chicken Burger',      2, 340.00, True),
        (4, 'MNU-MAI-001', 'Mutton Keema Flatbread',     3, 490.00, True),
        (5, 'MNU-PAS-001', 'Creamy Tomato Pasta',        4, 360.00, True),
        (6, 'MNU-BEV-001', 'Classic Cappuccino',         5, 190.00, True),
        # 2 Items intentionally unmapped
        (7, 'MNU-MAI-002', 'Truffle Mushroom Melt',      3, 420.00, False),
        (8, 'MNU-BEV-002', 'Iced Caramel Cortado',       5, 240.00, False)
    ]

    # Recipes for items 1-6
    recipes = [
        (1, 1, 'Standard Margherita Artisan Pizza BOM', 1.0, 'Hand-stretched dough, san marzano tomato reduction, fresh basil'),
        (2, 2, 'Spicy Peri-Peri Chicken Pizza BOM',     1.0, 'Marinated peri-peri chicken breast with crisp peppers'),
        (3, 3, 'Smoked Chicken Burger with Brioche BOM',1.0, 'Grilled chicken breast with herb butter glaze on artisanal bun'),
        (4, 4, 'Slow-Cooked Mutton Keema Flatbread BOM',1.0, 'Spiced minced lamb flatbread baked in deck oven'),
        (5, 5, 'Velvety Creamy Tomato Rigatoni BOM',    1.0, 'Simmered tomato reduction with fresh cream, melted mozzarella and herbs'),
        (6, 6, 'Single-Origin Double Shot Cappuccino',  1.0, '18g espresso extraction with velvety microfoam')
    ]

    # Recipe ingredients (item_id, recipe_id, ing_id, qty, unit, prep_waste_pct)
    recipe_ingredients = [
        # Recipe 1: Margherita Pizza
        (1, 1, 9,  180.0, 'g',    0.0),  # Pizza Flour
        (2, 1, 6,  120.0, 'g',    5.0),  # Fresh Tomatoes (5% prep loss)
        (3, 1, 1,  4.5,   'oz',   0.0),  # Mozzarella: 4.5 oz = 127.57 g
        (4, 1, 10, 1.0,   'tbsp', 0.0),  # Olive oil: 1 tbsp = 15 ml
        (5, 1, 8,  10.0,  'g',    10.0), # Fresh Basil: 10 g (10% trim loss)

        # Recipe 2: Peri-Peri Chicken Pizza
        (6,  2, 9,  180.0, 'g',    0.0),  # Pizza Flour
        (7,  2, 6,  100.0, 'g',    5.0),  # Fresh Tomatoes
        (8,  2, 1,  4.0,   'oz',   0.0),  # Mozzarella: 4.0 oz = 113.40 g
        (9,  2, 4,  140.0, 'g',    0.0),  # Chicken Breast: 140 g
        (10, 2, 7,  40.0,  'g',    8.0),  # Bell Peppers: 40 g (8% seed loss)
        (11, 2, 10, 1.0,   'tbsp', 0.0),  # Olive Oil: 15 ml

        # Recipe 3: Smoked Chicken Burger
        (12, 3, 12, 1.0,   'pcs',  0.0),  # Artisanal Bun
        (13, 3, 4,  150.0, 'g',    0.0),  # Chicken Breast: 150 g
        (14, 3, 3,  20.0,  'g',    0.0),  # Salted Butter: 20 g
        (15, 3, 7,  30.0,  'g',    5.0),  # Bell Peppers: 30 g
        (16, 3, 6,  30.0,  'g',    5.0),  # Fresh Tomatoes: 30 g

        # Recipe 4: Mutton Keema Flatbread
        (17, 4, 9,  150.0, 'g',    0.0),  # Pizza Flour: 150 g
        (18, 4, 5,  160.0, 'g',    0.0),  # Mutton Keema: 160 g
        (19, 4, 3,  25.0,  'g',    0.0),  # Salted Butter: 25 g
        (20, 4, 6,  60.0,  'g',    5.0),  # Fresh Tomatoes: 60 g
        (21, 4, 8,  15.0,  'g',    10.0), # Fresh Basil: 15 g

        # Recipe 5: Creamy Tomato Pasta
        (22, 5, 6,  150.0, 'g',    5.0),  # Fresh Tomatoes: 150 g
        (23, 5, 2,  80.0,  'ml',   0.0),  # Fresh Cream: 80 ml
        (24, 5, 3,  25.0,  'g',    0.0),  # Salted Butter: 25 g
        (25, 5, 1,  1.5,   'oz',   0.0),  # Mozzarella: 1.5 oz = 42.52 g
        (26, 5, 8,  2.0,   'tsp',  10.0), # Basil: 2 tsp = 10 g (10% loss)
        (27, 5, 10, 1.0,   'tbsp', 0.0),  # Olive oil: 1 tbsp = 15 ml

        # Recipe 6: Classic Cappuccino
        (28, 6, 11, 18.0,  'g',    0.0),  # Espresso Coffee Beans: 18 g
        (29, 6, 2,  40.0,  'ml',   0.0)   # Fresh Cream: 40 ml
    ]

    # Precompute theoretical requirement per portion in base unit
    # formula: qty * multiplier * (1 + prep_waste/100) / (yield/100)
    recipe_bom_base = {}
    for row in recipe_ingredients:
        rec_id, ing_id, qty, unit, prep_waste = row[1], row[2], row[3], row[4], row[5]
        mult = conv_map[(unit, ing_dict[ing_id]['unit'])]
        yield_pct = ing_dict[ing_id]['yield']
        effective_base_qty = qty * mult * (1.0 + (prep_waste / 100.0)) / (yield_pct / 100.0)
        recipe_bom_base.setdefault(rec_id, {})[ing_id] = effective_base_qty

    suppliers = [
        (1, 'SUP-DAI-01', 'Pune Fresh Dairy Farms Ltd.',     'orders@punefreshdairy.com',  '+91-20-2567-1100'),
        (2, 'SUP-MEA-02', 'Deccan Meat & Poultry Supplies',   'sales@deccanmeats.co.in',    '+91-20-2612-4422'),
        (3, 'SUP-PRO-03', 'Sahyadri Organic Agro & Produce',  'procurement@sahyadriagro.in','+91-20-2745-8899'),
        (4, 'SUP-DRY-04', 'Mahalaxmi Dry Goods & Grain Co.',  'dispatch@mahalaxmigrains.com','+91-20-2444-3311'),
        (5, 'SUP-BEV-05', 'Blue Mountain Coffee Roasters',    'orders@bluemountain.in',     '+91-20-2688-9900')
    ]

    waste_reasons = [
        ('SPOILED_COOLER',   'Spoilage - Cooler Malfunction',      True,  'Walk-in cooler or display chiller temperature failure'),
        ('EXPIRED_SHELF',    'Product Expiration / Past Shelf Life',True, 'Unused product reached end of freshness period'),
        ('DROPPED_DAMAGED',  'Kitchen Mishandling / Dropped Item', True,  'Physical dropping or kitchen line damage'),
        ('PREP_TRIM_EXCESS', 'Excessive Prep Trim / Butcher Loss', True,  'Substandard raw material yield or knife technique'),
        ('LINE_SPILL',       'Cooking Overcooked / Line Contaminated',True,'Burnt, over-salted, or contaminated line prep')
    ]

    # --------------------------------------------------------------------------
    # 2. 30-DAY OPERATIONAL SIMULATION
    # --------------------------------------------------------------------------
    sales_rows = []
    # Track totals per branch and ingredient
    theoretical_usage = {b[0]: {i[0]: 0.0 for i in ingredients} for b in branches}
    menu_sales_totals = {b[0]: {m[0]: 0 for m in menu_items} for b in branches}

    sale_id_seq = 1

    # Simulate 30 days of sales
    for day_offset in range(30, 0, -1):
        # Day goes from (CURRENT_DATE - 30 days) to (CURRENT_DATE - 1 day)
        date_expr = f"(CURRENT_DATE - INTERVAL '{day_offset} days')::DATE"

        for b_id, b_code, b_name, _, _ in branches:
            is_weekend = (day_offset % 7 in [1, 2])
            weekend_multiplier = 1.35 if is_weekend else 1.0

            for m_id, sku, name, cat_id, price, is_mapped in menu_items:
                # Baseline volumes per branch profile
                if b_id == 1: # Koregaon Park (Flagship - steady high volume)
                    base_sales = random.randint(14, 24)
                elif b_id == 2: # Hinjawadi (IT crowd - high weekday pizza & coffee)
                    base_sales = random.randint(12, 22) if not is_weekend else random.randint(8, 14)
                elif b_id == 3: # Viman Nagar (Hub - youthful evening crowd)
                    base_sales = random.randint(10, 20)
                else: # Baner High Street (High-street dining)
                    base_sales = random.randint(10, 18)

                # Special Planted Sales Stories:
                # Story 3: Truffle Mushroom Melt (m_id=7) high volume at Baner High Street (180+ units)
                if m_id == 7: # Truffle Mushroom Melt (unmapped)
                    if b_id == 4: # Baner High Street
                        qty = int(random.randint(7, 12) * weekend_multiplier)
                    else:
                        qty = random.randint(1, 4)
                elif m_id == 8: # Iced Caramel Cortado (unmapped)
                    # Moderate sales across all branches
                    qty = int(random.randint(5, 10) * weekend_multiplier)
                else:
                    qty = int(base_sales * weekend_multiplier)

                total_amount = round(qty * price, 2)
                sales_rows.append((sale_id_seq, b_id, m_id, date_expr, qty, price, total_amount))
                sale_id_seq += 1

                menu_sales_totals[b_id][m_id] += qty

                # If recipe is mapped, accumulate theoretical ingredient usage
                if is_mapped and m_id in recipe_bom_base:
                    for ing_id, base_req in recipe_bom_base[m_id].items():
                        theoretical_usage[b_id][ing_id] += qty * base_req

    print(f"-> Generated {len(sales_rows)} POS sales transaction batches across 30 days.")
    print("-> Verification of Story 3 Menu Item Sales:")
    print(f"   * Truffle Mushroom Melt (Baner): {menu_sales_totals[4][7]} units sold (Target: >= 180 units)")
    print(f"   * Iced Caramel Cortado (All Branches): {sum(menu_sales_totals[b[0]][8] for b in branches)} units sold")

    # --------------------------------------------------------------------------
    # 3. WASTE LOGS SIMULATION
    # --------------------------------------------------------------------------
    waste_rows = []
    waste_totals = {b[0]: {i[0]: 0.0 for i in ingredients} for b in branches}
    waste_id_seq = 1

    # Mixed units for kitchen waste logging
    waste_unit_choices = {
        'g': ['g', 'kg'],
        'ml': ['ml', 'L'],
        'pcs': ['pcs']
    }

    # Simulate waste across days
    for day_offset in range(30, 0, -1):
        date_expr = f"(CURRENT_DATE - INTERVAL '{day_offset} days')::DATE"

        for b_id, b_code, b_name, _, _ in branches:
            for ing_id in range(1, 13):
                base_uom = ing_dict[ing_id]['unit']
                unit_cost = ing_dict[ing_id]['cost']

                # Planted Anomaly Story 2: Viman Nagar Hub (b_id=3)
                # Excess produce spoilage on Tomatoes (ing_id=6) and Basil (ing_id=8)
                # Target: ~18% of total volume logged as 'SPOILED_COOLER'
                if b_id == 3 and ing_id in [6, 8]:
                    # Major cooler breakdown event between day 18 and day 16 ago, plus minor daily leaks
                    if day_offset in [18, 17, 16]:
                        # Heavy spoilage incident
                        if ing_id == 6: # Tomatoes
                            qty_base = random.uniform(7000.0, 9500.0) # 7-9.5 kg
                            unit = 'kg'
                            qty_disp = round(qty_base / 1000.0, 2)
                        else: # Basil
                            qty_base = random.uniform(800.0, 1200.0) # 0.8-1.2 kg
                            unit = 'kg'
                            qty_disp = round(qty_base / 1000.0, 2)
                        
                        est_cost = round(qty_base * unit_cost, 2)
                        waste_rows.append((waste_id_seq, b_id, ing_id, date_expr, qty_disp, unit, 'SPOILED_COOLER', est_cost, 'Kitchen Lead - Ravi'))
                        waste_id_seq += 1
                        waste_totals[b_id][ing_id] += qty_base
                    elif day_offset % 3 == 0:
                        # Routine produce waste
                        qty_base = random.uniform(300.0, 600.0)
                        unit = 'g'
                        est_cost = round(qty_base * unit_cost, 2)
                        waste_rows.append((waste_id_seq, b_id, ing_id, date_expr, round(qty_base, 2), unit, 'EXPIRED_SHELF', est_cost, 'Prep Cook - Aniket'))
                        waste_id_seq += 1
                        waste_totals[b_id][ing_id] += qty_base

                else:
                    # Normal healthy operations: 1-2.5% of theoretical usage logged occasionally
                    if day_offset % 4 == 0 and random.random() < 0.65:
                        tu_avg_daily = theoretical_usage[b_id][ing_id] / 30.0
                        waste_frac = random.uniform(0.01, 0.025)
                        qty_base = max(1.0, tu_avg_daily * waste_frac * 4) # 4 days accumulation

                        # Choose display unit
                        if base_uom == 'g':
                            if qty_base > 1000 and random.random() < 0.5:
                                unit = 'kg'
                                qty_disp = round(qty_base / 1000.0, 3)
                            else:
                                unit = 'g'
                                qty_disp = round(qty_base, 1)
                        elif base_uom == 'ml':
                            if qty_base > 1000 and random.random() < 0.5:
                                unit = 'L'
                                qty_disp = round(qty_base / 1000.0, 3)
                            else:
                                unit = 'ml'
                                qty_disp = round(qty_base, 1)
                        else:
                            unit = 'pcs'
                            qty_disp = round(qty_base, 0)

                        reason = random.choice(['DROPPED_DAMAGED', 'EXPIRED_SHELF', 'PREP_TRIM_EXCESS', 'LINE_SPILL'])
                        est_cost = round(qty_base * unit_cost, 2)
                        waste_rows.append((waste_id_seq, b_id, ing_id, date_expr, qty_disp, unit, reason, est_cost, 'Duty Chef'))
                        waste_id_seq += 1
                        waste_totals[b_id][ing_id] += qty_base

    print(f"-> Generated {len(waste_rows)} kitchen waste audit records.")

    # --------------------------------------------------------------------------
    # 4. PURCHASES SIMULATION (BULK SHIPMENTS & ANOMALY INJECTION)
    # --------------------------------------------------------------------------
    purchases_rows = []
    purchase_totals = {b[0]: {i[0]: 0.0 for i in ingredients} for b in branches}
    purchase_id_seq = 1

    # Bulk delivery schedule: 5 delivery cycles over 30 days
    delivery_days = [29, 22, 15, 8, 2]

    # Supplier mapping for ingredients
    ing_supplier_map = {
        1: 1, 2: 1, 3: 1,   # Dairy -> Pune Fresh Dairy
        4: 2, 5: 2,         # Meat -> Deccan Meats
        6: 3, 7: 3, 8: 3,   # Produce -> Sahyadri Agro
        9: 4, 10: 4, 12: 4, # Dry Goods -> Mahalaxmi
        11: 5               # Beverages -> Blue Mountain Coffee
    }

    # Bulk purchase unit packaging options
    bulk_packaging = {
        # ing_id: (unit, multiplier_to_base)
        1:  ('kg',    1000.0),    # Mozzarella in kg blocks
        2:  ('L',     1000.0),    # Cream in Liters
        3:  ('kg',    1000.0),    # Butter in kg tubs
        4:  ('lb',    453.59237), # Chicken Breast in lb cases
        5:  ('kg',    1000.0),    # Keema in kg packs
        6:  ('kg',    1000.0),    # Tomatoes in kg crates
        7:  ('kg',    1000.0),    # Bell peppers in kg crates
        8:  ('kg',    1000.0),    # Fresh herbs in kg bundles
        9:  ('kg',    1000.0),    # Flour in kg sacks
        10: ('L',     1000.0),    # Olive oil in Liters
        11: ('kg',    1000.0),    # Coffee beans in kg bags
        12: ('dozen', 12.0)       # Burger buns in dozen packs
    }

    # For each branch and ingredient, establish target total purchase in base units
    for b_id, b_code, b_name, _, _ in branches:
        for ing_id in range(1, 13):
            tu = theoretical_usage[b_id][ing_id]
            waste = waste_totals[b_id][ing_id]
            base_uom = ing_dict[ing_id]['unit']
            unit_cost = ing_dict[ing_id]['cost']

            # Target 30-day purchases:
            # Story 1: Hinjawadi IT Park (b_id=2) on Cheese (ing_id=1) & Chicken (ing_id=4)
            # Planted severe shrinkage/over-portioning anomaly: purchase ~24% MORE than TU + Waste
            if b_id == 2 and ing_id in [1, 4]:
                anomaly_multiplier = 1.242 # +24.2% over-consumption
                target_purchase_base = (tu + waste) * anomaly_multiplier
            # Story 2: Viman Nagar Hub (b_id=3) on Tomatoes (ing_id=6) & Basil (ing_id=8)
            # Logged waste is ~18% of purchases; purchases properly resupplied
            elif b_id == 3 and ing_id in [6, 8]:
                # Target purchase covers TU and the high cooler waste
                target_purchase_base = (tu + waste) * random.uniform(1.005, 1.025)
            # Story 4: Koregaon Park Flagship (b_id=1) - Healthy benchmark
            elif b_id == 1:
                # Aligned within ±2.5% of (TU + Waste)
                target_purchase_base = (tu + waste) * random.uniform(0.995, 1.020)
            else:
                # Normal healthy operation for other branches/ingredients
                target_purchase_base = (tu + waste) * random.uniform(0.990, 1.025)

            # Safeguard minimum purchase
            target_purchase_base = max(target_purchase_base, 100.0)

            # Divide total purchase across the 5 delivery days
            bulk_unit, bulk_mult = bulk_packaging[ing_id]
            delivery_shares = [0.22, 0.20, 0.20, 0.20, 0.18]

            for idx, day_offset in enumerate(delivery_days):
                date_expr = f"(CURRENT_DATE - INTERVAL '{day_offset} days')::DATE"
                share = delivery_shares[idx]
                qty_base_shipment = target_purchase_base * share

                # Convert to bulk receiving unit
                qty_bulk = round(qty_base_shipment / bulk_mult, 2)
                # Actual base qty received
                actual_base_received = qty_bulk * bulk_mult

                # Purchase unit cost in bulk
                bulk_unit_cost = round(unit_cost * bulk_mult, 2)
                total_cost = round(qty_bulk * bulk_unit_cost, 2)
                inv_no = f"INV-{b_code}-{day_offset:02d}-{ing_id:02d}"

                purchases_rows.append((
                    purchase_id_seq,
                    b_id,
                    ing_id,
                    ing_supplier_map[ing_id],
                    date_expr,
                    inv_no,
                    qty_bulk,
                    bulk_unit,
                    bulk_unit_cost,
                    total_cost
                ))
                purchase_id_seq += 1
                purchase_totals[b_id][ing_id] += actual_base_received

    print(f"-> Generated {len(purchases_rows)} purchase receiving shipments across 5 delivery cycles.")

    # --------------------------------------------------------------------------
    # 5. PHYSICAL INVENTORY COUNTS (BEGINNING & ENDING AUDITS)
    # --------------------------------------------------------------------------
    inventory_count_rows = []
    count_id_seq = 1

    # Beginning Count at (CURRENT_DATE - 30 days)
    # Ending Count at CURRENT_DATE
    # Actual Usage AU = Beginning + Purchases - Ending
    # We calibrate Ending Count so that:
    #   For Hinjawadi Cheese & Chicken: AU = P, so Ending = Beginning (stock drained / stolen)
    #   For normal items: Ending = Beginning + Purchases - (TU + Waste + random noise)
    for b_id, b_code, b_name, _, _ in branches:
        for ing_id in range(1, 13):
            base_uom = ing_dict[ing_id]['unit']
            par = ing_dict[ing_id]['par']
            tu = theoretical_usage[b_id][ing_id]
            waste = waste_totals[b_id][ing_id]
            purchased = purchase_totals[b_id][ing_id]

            # Beginning physical count (30 days ago) - set around par level
            beginning_qty = round(par * random.uniform(0.95, 1.05), 1)

            # Ending physical count (Today)
            if b_id == 2 and ing_id in [1, 4]:
                # Hinjawadi Cheese & Chicken: The extra purchases are GONE (theft/over-portioning)
                # Ending stock is low-to-normal par, so AU reflects the entire bloated purchase!
                ending_qty = round(beginning_qty * random.uniform(0.96, 1.02), 1)
            else:
                # Normal operational balance: Ending = Beginning + Purchases - (TU + Waste)
                expected_ending = beginning_qty + purchased - (tu + waste)
                # Add minor realistic audit noise (±1.5%)
                ending_qty = max(10.0, round(expected_ending + random.uniform(-0.015, 0.015) * tu, 1))

            # Store beginning count
            inventory_count_rows.append((
                count_id_seq,
                b_id,
                ing_id,
                "(CURRENT_DATE - INTERVAL '30 days')::DATE",
                beginning_qty,
                base_uom,
                'BEGINNING',
                'Internal Audit Team'
            ))
            count_id_seq += 1

            # Store ending count
            inventory_count_rows.append((
                count_id_seq,
                b_id,
                ing_id,
                "CURRENT_DATE",
                ending_qty,
                base_uom,
                'ENDING',
                'Internal Audit Team'
            ))
            count_id_seq += 1

    print(f"-> Generated {len(inventory_count_rows)} beginning & ending physical stock audit counts.")

    # --------------------------------------------------------------------------
    # 6. MATHEMATICAL VERIFICATION & STORY AUDITING
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("ANALYTICAL VERIFICATION & STORY CHECK (30-DAY TOTALS)")
    print("=" * 80)
    for b_id, b_code, b_name, _, _ in branches:
        print(f"\n[Branch {b_id}: {b_name}]")
        print(f"{'Ingredient':<26} | {'Purchased':>10} | {'TU (Sales)':>10} | {'Waste':>10} | {'Unexplained':>11} | {'Unexp %':>8} | {'Status'}")
        print("-" * 95)
        for ing_id in range(1, 13):
            ing_name = ing_dict[ing_id]['name']
            tu = theoretical_usage[b_id][ing_id]
            w = waste_totals[b_id][ing_id]
            p = purchase_totals[b_id][ing_id]
            # Since Beginning ~ Ending in par model, AU ~ P
            # More precisely:
            b_cnt = [r[4] for r in inventory_count_rows if r[1] == b_id and r[2] == ing_id and r[6] == 'BEGINNING'][0]
            e_cnt = [r[4] for r in inventory_count_rows if r[1] == b_id and r[2] == ing_id and r[6] == 'ENDING'][0]
            au = b_cnt + p - e_cnt
            unexp_qty = au - tu - w
            unexp_pct = (unexp_qty / tu * 100.0) if tu > 0 else 0.0

            if unexp_pct >= 15.0:
                status = "Flagged for Review (CRITICAL LEAK)"
            elif (w / p * 100.0) >= 12.0:
                status = "Excess Waste Logged (SPOILAGE)"
            elif unexp_pct <= -10.0:
                status = "Under-portioning / Audit Count"
            else:
                status = "Normal Tolerance"

            if ing_id in [1, 4, 6, 8] or b_id == 1:
                print(f"{ing_name:<26} | {p:>10.1f} | {tu:>10.1f} | {w:>10.1f} | {unexp_qty:>11.1f} | {unexp_pct:>7.1f}% | {status}")

    # --------------------------------------------------------------------------
    # 7. GENERATE SQL STATEMENTS (sql/02_seed_data.sql)
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print(f"WRITING SEED DATA SQL TO: {output_sql_path}")
    print("=" * 80)

    sql_lines = []
    sql_lines.append("-- ==============================================================================")
    sql_lines.append("-- File: 02_seed_data.sql")
    sql_lines.append("-- Project: Kitchen Ledger Analytics / Restaurant Inventory & Variance Visualization")
    sql_lines.append("-- Generated By: scripts/generate_seed.py (Deterministic seed: 42)")
    sql_lines.append(f"-- Timestamp: {datetime.now().isoformat()}")
    sql_lines.append("-- Description: 30 days of multi-branch restaurant operational data, mixed units,")
    sql_lines.append("--              and 4 planted analytical anomaly stories.")
    sql_lines.append("-- ==============================================================================\n")

    sql_lines.append("SET search_path TO restaurant_inventory, public;\n")

    # TRUNCATE statement
    sql_lines.append("-- ------------------------------------------------------------------------------")
    sql_lines.append("-- TRUNCATE ALL OPERATIONAL & MASTER DATA CASCADE")
    sql_lines.append("-- ------------------------------------------------------------------------------")
    sql_lines.append("TRUNCATE TABLE")
    sql_lines.append("    inventory_counts,")
    sql_lines.append("    waste_logs,")
    sql_lines.append("    sales,")
    sql_lines.append("    purchases,")
    sql_lines.append("    recipe_ingredients,")
    sql_lines.append("    recipes,")
    sql_lines.append("    menu_items,")
    sql_lines.append("    ingredients,")
    sql_lines.append("    unit_conversions,")
    sql_lines.append("    units_of_measure,")
    sql_lines.append("    waste_reasons,")
    sql_lines.append("    suppliers,")
    sql_lines.append("    menu_categories,")
    sql_lines.append("    categories,")
    sql_lines.append("    branches")
    sql_lines.append("RESTART IDENTITY CASCADE;\n")

    # 1. Branches
    sql_lines.append("-- ------------------------------------------------------------------------------")
    sql_lines.append("-- 1. BRANCHES (4 Pune Locations)")
    sql_lines.append("-- ------------------------------------------------------------------------------")
    branch_vals = [f"('{b[1]}', '{b[2]}', '{b[3]}', '{b[4]}')" for b in branches]
    sql_lines.append(f"INSERT INTO branches (branch_code, branch_name, city, region) VALUES\n  " + ",\n  ".join(branch_vals) + ";\n")

    # 2. Categories
    sql_lines.append("-- ------------------------------------------------------------------------------")
    sql_lines.append("-- 2. CATEGORIES")
    sql_lines.append("-- ------------------------------------------------------------------------------")
    cat_vals = [f"('{c[1]}', {c[2]}, '{c[3]}')" for c in categories]
    sql_lines.append(f"INSERT INTO categories (category_name, target_food_cost_pct, description) VALUES\n  " + ",\n  ".join(cat_vals) + ";\n")

    # 3. Units of Measure
    sql_lines.append("-- ------------------------------------------------------------------------------")
    sql_lines.append("-- 3. UNITS OF MEASURE")
    sql_lines.append("-- ------------------------------------------------------------------------------")
    uom_vals = [f"('{u[0]}', '{u[1]}', '{u[2]}', {str(u[3]).upper()}, '{u[4]}')" for u in units_of_measure]
    sql_lines.append(f"INSERT INTO units_of_measure (uom_code, uom_name, dimension, is_base_unit, description) VALUES\n  " + ",\n  ".join(uom_vals) + ";\n")

    # 4. Unit Conversions
    sql_lines.append("-- ------------------------------------------------------------------------------")
    sql_lines.append("-- 4. UNIT CONVERSIONS")
    sql_lines.append("-- ------------------------------------------------------------------------------")
    conv_vals = [f"('{uc[0]}', '{uc[1]}', {uc[2]:.8f}, '{uc[3]}')" for uc in unit_conversions]
    sql_lines.append(f"INSERT INTO unit_conversions (from_unit, to_unit, multiplier, dimension) VALUES\n  " + ",\n  ".join(conv_vals) + ";\n")

    # 5. Ingredients
    sql_lines.append("-- ------------------------------------------------------------------------------")
    sql_lines.append("-- 5. INGREDIENTS (12 Core Raw Materials with INR Costs)")
    sql_lines.append("-- ------------------------------------------------------------------------------")
    ing_vals = [f"('{i[1]}', '{i[2]}', {i[3]}, '{i[4]}', {i[5]:.4f}, {i[6]:.2f}, {i[7]:.2f})" for i in ingredients]
    sql_lines.append(f"INSERT INTO ingredients (sku, ingredient_name, category_id, base_unit, cost_per_base_unit, par_level, yield_pct) VALUES\n  " + ",\n  ".join(ing_vals) + ";\n")

    # 6. Menu Categories & Items
    sql_lines.append("-- ------------------------------------------------------------------------------")
    sql_lines.append("-- 6. MENU CATEGORIES & ITEMS (8 Menu Items, 2 Intentionally Unmapped)")
    sql_lines.append("-- ------------------------------------------------------------------------------")
    mc_vals = [f"('{mc[1]}', {mc[2]})" for mc in menu_categories]
    sql_lines.append(f"INSERT INTO menu_categories (category_name, display_order) VALUES\n  " + ",\n  ".join(mc_vals) + ";\n")

    mi_vals = [f"('{m[1]}', '{m[2]}', {m[3]}, {m[4]:.2f})" for m in menu_items]
    sql_lines.append(f"INSERT INTO menu_items (sku, item_name, category_id, selling_price) VALUES\n  " + ",\n  ".join(mi_vals) + ";\n")

    # 7. Recipes & Recipe Ingredients
    sql_lines.append("-- ------------------------------------------------------------------------------")
    sql_lines.append("-- 7. RECIPES & RECIPE INGREDIENTS (Bill of Materials with Mixed Units)")
    sql_lines.append("-- ------------------------------------------------------------------------------")
    rec_vals = [f"({r[1]}, '{r[2]}', {r[3]:.2f}, '{r[4]}')" for r in recipes]
    sql_lines.append(f"INSERT INTO recipes (menu_item_id, recipe_name, yield_servings, prep_notes) VALUES\n  " + ",\n  ".join(rec_vals) + ";\n")

    ri_vals = [f"({ri[1]}, {ri[2]}, {ri[3]:.4f}, '{ri[4]}', {ri[5]:.2f})" for ri in recipe_ingredients]
    sql_lines.append(f"INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity, unit, prep_waste_pct) VALUES\n  " + ",\n  ".join(ri_vals) + ";\n")

    # 8. Suppliers
    sql_lines.append("-- ------------------------------------------------------------------------------")
    sql_lines.append("-- 8. SUPPLIERS")
    sql_lines.append("-- ------------------------------------------------------------------------------")
    sup_vals = [f"('{s[1]}', '{s[2]}', '{s[3]}', '{s[4]}')" for s in suppliers]
    sql_lines.append(f"INSERT INTO suppliers (supplier_code, supplier_name, contact_email, phone) VALUES\n  " + ",\n  ".join(sup_vals) + ";\n")

    # 9. Waste Reasons
    sql_lines.append("-- ------------------------------------------------------------------------------")
    sql_lines.append("-- 9. WASTE REASONS")
    sql_lines.append("-- ------------------------------------------------------------------------------")
    wr_vals = [f"('{w[0]}', '{w[1]}', {str(w[2]).upper()}, '{w[3]}')" for w in waste_reasons]
    sql_lines.append(f"INSERT INTO waste_reasons (reason_code, reason_name, is_preventable, description) VALUES\n  " + ",\n  ".join(wr_vals) + ";\n")

    # 10. Inventory Counts
    sql_lines.append("-- ------------------------------------------------------------------------------")
    sql_lines.append("-- 10. INVENTORY COUNTS (Beginning & Ending Audits)")
    sql_lines.append("-- ------------------------------------------------------------------------------")
    ic_chunks = [inventory_count_rows[i:i + 200] for i in range(0, len(inventory_count_rows), 200)]
    for chunk in ic_chunks:
        c_vals = [f"({c[1]}, {c[2]}, {c[3]}, {c[4]:.4f}, '{c[5]}', '{c[6]}', '{c[7]}')" for c in chunk]
        sql_lines.append(f"INSERT INTO inventory_counts (branch_id, ingredient_id, count_date, quantity, unit, count_type, conducted_by) VALUES\n  " + ",\n  ".join(c_vals) + ";\n")

    # 11. Purchases
    sql_lines.append("-- ------------------------------------------------------------------------------")
    sql_lines.append("-- 11. PURCHASES (Bulk Shipments with Mixed Units)")
    sql_lines.append("-- ------------------------------------------------------------------------------")
    pur_chunks = [purchases_rows[i:i + 200] for i in range(0, len(purchases_rows), 200)]
    for chunk in pur_chunks:
        p_vals = [f"({p[1]}, {p[2]}, {p[3]}, {p[4]}, '{p[5]}', {p[6]:.4f}, '{p[7]}', {p[8]:.4f}, {p[9]:.2f})" for p in chunk]
        sql_lines.append(f"INSERT INTO purchases (branch_id, ingredient_id, supplier_id, purchase_date, invoice_no, quantity, unit, unit_cost, total_cost) VALUES\n  " + ",\n  ".join(p_vals) + ";\n")

    # 12. POS Sales
    sql_lines.append("-- ------------------------------------------------------------------------------")
    sql_lines.append("-- 12. POS SALES (30 Days of Transactions)")
    sql_lines.append("-- ------------------------------------------------------------------------------")
    sales_chunks = [sales_rows[i:i + 200] for i in range(0, len(sales_rows), 200)]
    for chunk in sales_chunks:
        s_vals = [f"({s[1]}, {s[2]}, {s[3]}, {s[4]}, {s[5]:.2f}, {s[6]:.2f})" for s in chunk]
        sql_lines.append(f"INSERT INTO sales (branch_id, menu_item_id, sale_date, quantity, unit_price, total_amount) VALUES\n  " + ",\n  ".join(s_vals) + ";\n")

    # 13. Waste Logs
    sql_lines.append("-- ------------------------------------------------------------------------------")
    sql_lines.append("-- 13. WASTE LOGS (Operational Spoilage & Mishandling)")
    sql_lines.append("-- ------------------------------------------------------------------------------")
    waste_chunks = [waste_rows[i:i + 200] for i in range(0, len(waste_rows), 200)]
    for chunk in waste_chunks:
        w_vals = [f"({w[1]}, {w[2]}, {w[3]}, {w[4]:.4f}, '{w[5]}', '{w[6]}', {w[7]:.2f}, '{w[8]}')" for w in chunk]
        sql_lines.append(f"INSERT INTO waste_logs (branch_id, ingredient_id, waste_date, quantity, unit, reason, estimated_cost, recorded_by) VALUES\n  " + ",\n  ".join(w_vals) + ";\n")

    # Write SQL content to file
    full_sql = "\n".join(sql_lines)
    os.makedirs(os.path.dirname(os.path.abspath(output_sql_path)), exist_ok=True)
    with open(output_sql_path, "w", encoding="utf-8") as f:
        f.write(full_sql)

    # Mirror to secondary path if present
    alt_paths = [
        os.path.join("restaurant-inventory-viz", "sql", "02_seed_data.sql"),
        os.path.join("sql", "02_seed_data.sql")
    ]
    for alt_p in alt_paths:
        if os.path.abspath(alt_p) != os.path.abspath(output_sql_path):
            os.makedirs(os.path.dirname(os.path.abspath(alt_p)), exist_ok=True)
            with open(alt_p, "w", encoding="utf-8") as f:
                f.write(full_sql)

    print(f"-> Successfully written {len(sql_lines)} lines to {output_sql_path}")
    print(f"-> File size: {len(full_sql.encode('utf-8')) / 1024:.1f} KB")

    # Optional DB execution via SQLAlchemy
    if execute_db:
        print("\n" + "=" * 80)
        print("EXECUTING SEED SQL DIRECTLY VIA SQLALCHEMY / PSYCOPG2")
        print("=" * 80)
        try:
            from sqlalchemy import create_engine, text
            target_url = db_url or os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/restaurant_inventory_db")
            print(f"Connecting to: {target_url} ...")
            engine = create_engine(target_url, isolation_level="AUTOCOMMIT")
            with engine.connect() as conn:
                conn.execute(text(full_sql))
            print("-> Successfully executed seed script against PostgreSQL database!")
        except Exception as e:
            print(f"-> SQLAlchemy Execution Note: {e}")
            print("   (Ensure PostgreSQL is running and credentials in .env or --db-url are correct)")

    print("\n" + "=" * 80)
    print("PHASE 2 SEED GENERATION COMPLETE!")
    print("=" * 80)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deterministic PostgreSQL Seed Data Generator for Kitchen Ledger Analytics")
    parser.add_argument("--output", type=str, default="sql/02_seed_data.sql", help="Output path for SQL file")
    parser.add_argument("--execute", action="store_true", help="Execute the generated SQL directly via SQLAlchemy")
    parser.add_argument("--db-url", type=str, default=None, help="PostgreSQL connection string")
    args = parser.parse_args()

    generate_seed_data(output_sql_path=args.output, execute_db=args.execute, db_url=args.db_url)
