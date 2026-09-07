import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, NamedStyle, Protection
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.chart import BarChart, LineChart, Reference
import datetime

def create_inventory_system():
    wb = openpyxl.Workbook()
    # Remove default sheet
    default_sheet = wb.active
    wb.remove(default_sheet)
    
    # ----------------------------------------------------
    # STYLES DEFINITION
    # ----------------------------------------------------
    NAVY = "1E293B"      # Dark slate navy
    NAVY_LIGHT = "F1F5F9" # Navigation background
    WHITE = "FFFFFF"
    GRAY_TEXT = "64748B"
    BORDER_COLOR = "E2E8F0"
    
    font_title = Font(name="Segoe UI", size=16, bold=True, color="FFFFFF")
    font_nav = Font(name="Segoe UI", size=10, bold=True, color="0F172A")
    font_header = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    font_data = Font(name="Segoe UI", size=10)
    font_bold = Font(name="Segoe UI", size=10, bold=True)
    font_italic = Font(name="Segoe UI", size=9, italic=True)
    font_kpi_num = Font(name="Segoe UI", size=20, bold=True, color=NAVY)
    font_kpi_lbl = Font(name="Segoe UI", size=9, bold=True, color=GRAY_TEXT)
    
    fill_navy = PatternFill(start_color=NAVY, end_color=NAVY, fill_type="solid")
    fill_nav = PatternFill(start_color=NAVY_LIGHT, end_color=NAVY_LIGHT, fill_type="solid")
    fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    fill_white = PatternFill(start_color=WHITE, end_color=WHITE, fill_type="solid")
    fill_kpi = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    
    thin_border = Border(
        left=Side(style='thin', color=BORDER_COLOR),
        right=Side(style='thin', color=BORDER_COLOR),
        top=Side(style='thin', color=BORDER_COLOR),
        bottom=Side(style='thin', color=BORDER_COLOR)
    )
    
    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    align_right = Alignment(horizontal="right", vertical="center")
    
    # Status Alert Colors (Conditional Formatting)
    status_rules = {
        "In Stock": {"fill": "D1FAE5", "font": "065F46"},
        "Low Stock": {"fill": "FEF3C7", "font": "92400E"},
        "Out of Stock": {"fill": "FEE2E2", "font": "991B1B"}
    }
    
    # ----------------------------------------------------
    # HELPER: HEADER & NAVIGATION
    # ----------------------------------------------------
    def apply_header_and_nav(ws, title_text):
        # Gridlines visible
        ws.views.sheetView[0].showGridLines = True
        
        # Banner row
        ws.merge_cells("A1:W2")
        ws["A1"] = title_text.upper()
        ws["A1"].font = font_title
        ws["A1"].fill = fill_navy
        ws["A1"].alignment = align_center
        
        # Nav row (Row 4)
        nav_items = [
            ("A4", "📊 Dashboard", "Dashboard"),
            ("D4", "📦 Product Master", "Product Master"),
            ("H4", "📥 Purchase Entry", "Purchase Entry"),
            ("L4", "📤 Sales Entry", "Sales Entry"),
            ("O4", "🤝 Suppliers", "Supplier Management"),
            ("R4", "📈 Reports", "Reports"),
            ("U4", "📄 Printable Invoice", "Invoice")
        ]
        
        for cell_ref, text, sheet_name in nav_items:
            ws[cell_ref] = f'=HYPERLINK("#\'{sheet_name}\'!A1", "{text}")'
            ws[cell_ref].font = font_nav
            ws[cell_ref].alignment = align_center
            ws[cell_ref].fill = fill_nav
            ws[cell_ref].border = thin_border
            
        # Format the Nav Row background and borders
        for col in range(1, 24):
            cell = ws.cell(row=4, column=col)
            if cell.value is None:
                cell.fill = fill_nav
                cell.border = thin_border

        # Adjust header/nav heights
        ws.row_dimensions[1].height = 20
        ws.row_dimensions[2].height = 20
        ws.row_dimensions[3].height = 10
        ws.row_dimensions[4].height = 25
        ws.row_dimensions[5].height = 15

    # ----------------------------------------------------
    # SHEET 8: REFERENCE LISTS
    # ----------------------------------------------------
    ws_refs = wb.create_sheet("ReferenceLists")
    ws_refs.views.sheetView[0].showGridLines = True
    ws_refs["A1"] = "Categories"
    ws_refs["B1"] = "Locations"
    ws_refs["C1"] = "Payment Methods"
    
    categories = ["Electronics", "Apparel", "Grocery", "Pharmacy", "Home & Kitchen"]
    locations = ["Aisle A", "Aisle B", "Aisle C", "Aisle D", "Warehouse"]
    payments = ["Cash", "Credit Card", "Debit Card", "Mobile Wallet", "Bank Transfer"]
    
    for idx, val in enumerate(categories): ws_refs.cell(row=idx+2, column=1, value=val)
    for idx, val in enumerate(locations): ws_refs.cell(row=idx+2, column=2, value=val)
    for idx, val in enumerate(payments): ws_refs.cell(row=idx+2, column=3, value=val)
    
    # Hide reference sheet to keep workbook clean
    ws_refs.sheet_state = "hidden"

    # ----------------------------------------------------
    # SHEET 5: SUPPLIER MANAGEMENT
    # ----------------------------------------------------
    ws_supl = wb.create_sheet("Supplier Management")
    apply_header_and_nav(ws_supl, "Supplier Directory")
    
    sup_headers = ["Supplier ID", "Supplier Name", "Contact Person", "Phone", "Email", "Address"]
    for col_idx, h in enumerate(sup_headers, 1):
        cell = ws_supl.cell(row=6, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_navy
        cell.alignment = align_center
        cell.border = thin_border
        
    suppliers_data = [
        ("SPL-0001", "Apex Distributors", "John Smith", "555-0101", "sales@apex.com", "123 Industrial Pkwy, New York, NY"),
        ("SPL-0002", "Summit Wholesale", "Sarah Connor", "555-0102", "contact@summit.com", "456 Commerce Blvd, Los Angeles, CA"),
        ("SPL-0003", "Prime Logistics", "David Miller", "555-0103", "logistics@prime.com", "789 Supply Rd, Chicago, IL"),
        ("SPL-0004", "Global Trade Co.", "Elena Rostova", "555-0104", "trade@global.com", "101 Port Way, Miami, FL"),
        ("SPL-0005", "BioPharma Supplies", "Alan Grant", "555-0105", "supplies@biopharma.com", "202 Lab Circle, Boston, MA"),
    ]
    
    for r_idx, row_data in enumerate(suppliers_data, 7):
        for c_idx, val in enumerate(row_data, 1):
            cell = ws_supl.cell(row=r_idx, column=c_idx, value=val)
            cell.font = font_data
            cell.border = thin_border
            if r_idx % 2 == 0:
                cell.fill = fill_zebra
            if c_idx == 1:
                cell.alignment = align_center
                
    # Add Excel Table for Suppliers
    tab_supl = Table(displayName="SupplierMaster", ref=f"A6:F{len(suppliers_data)+6}")
    tab_supl.tableStyleInfo = TableStyleInfo(name="TableStyleMedium9", showRowStripes=True)
    ws_supl.add_table(tab_supl)
    ws_supl.freeze_panes = "A7"

    # ----------------------------------------------------
    # SHEET 2: PRODUCT MASTER
    # ----------------------------------------------------
    ws_prod = wb.create_sheet("Product Master")
    apply_header_and_nav(ws_prod, "Product Master Registry")
    
    prod_headers = [
        "Product ID", "Product Name", "Category", "Brand", "Supplier", 
        "Unit of Measure", "Unit Price", "Cost Price", "Selling Price", "Initial Stock", 
        "Purchases Qty", "Sales Qty", "Current Stock", "Reorder Level", 
        "Storage Location", "Status", "Warranty Period", "Quantity per Set", 
        "Set Price", "Stock Value", "Total Sales Value", "FIFO Stock Value", "Margin %"
    ]
    
    for col_idx, h in enumerate(prod_headers, 1):
        cell = ws_prod.cell(row=6, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_navy
        cell.alignment = align_center
        cell.border = thin_border
        
    # Standard 50 realistic products across categories
    # Elements in tuple: Name, Category, Brand, Supplier, UOM, UnitPrice, CostPrice, InitialStock, ReorderLevel, Location, Warranty, QtyPerSet
    dummy_products = [
        # Electronics (1-10)
        ("Sony WH-1000XM4 Headphones", "Electronics", "Sony", "Apex Distributors", "pcs", 250.00, 180.00, 15, 5, "Aisle A", "12 Months", 1),
        ("Samsung 27\" Curved Monitor", "Electronics", "Samsung", "Apex Distributors", "pcs", 180.00, 120.00, 10, 3, "Aisle A", "24 Months", 1),
        ("Apple iPad Air (64GB)", "Electronics", "Apple", "Global Trade Co.", "pcs", 549.00, 420.00, 8, 2, "Aisle A", "12 Months", 1),
        ("Dell Wireless Keyboard Combo", "Electronics", "Dell", "Apex Distributors", "pcs", 45.00, 25.00, 25, 8, "Aisle A", "12 Months", 1),
        ("Logitech C920 HD Pro Webcam", "Electronics", "Logitech", "Apex Distributors", "pcs", 79.00, 45.00, 12, 4, "Aisle A", "12 Months", 1),
        ("SanDisk Extreme 128GB USB-C", "Electronics", "SanDisk", "Summit Wholesale", "pcs", 29.99, 15.00, 40, 10, "Aisle A", "60 Months", 1),
        ("Anker PowerCore 26800mAh", "Electronics", "Anker", "Summit Wholesale", "pcs", 59.99, 35.00, 18, 5, "Aisle A", "18 Months", 1),
        ("HP LaserJet Pro Printer", "Electronics", "HP", "Prime Logistics", "pcs", 229.00, 150.00, 6, 2, "Warehouse", "12 Months", 1),
        ("ASUS ZenBook 14 Laptop", "Electronics", "ASUS", "Global Trade Co.", "pcs", 899.99, 650.00, 5, 2, "Aisle A", "12 Months", 1),
        ("Belkin 12-Outlet Surge Protector", "Electronics", "Belkin", "Summit Wholesale", "pcs", 24.99, 12.00, 30, 8, "Aisle A", "Lifetime", 1),
        # Apparel (11-20)
        ("Nike Air Max Sneakers", "Apparel", "Nike", "Summit Wholesale", "pcs", 120.00, 70.00, 20, 5, "Aisle B", "0 Months", 1),
        ("Adidas Essentials Hoodie", "Apparel", "Adidas", "Summit Wholesale", "pcs", 50.00, 25.00, 30, 10, "Aisle B", "0 Months", 1),
        ("Levi's 501 Original Jeans", "Apparel", "Levi's", "Summit Wholesale", "pcs", 68.00, 32.00, 25, 8, "Aisle B", "0 Months", 1),
        ("Zara Wool Blend Coat", "Apparel", "Zara", "Global Trade Co.", "pcs", 119.00, 55.00, 10, 3, "Aisle B", "0 Months", 1),
        ("H&M Basic Crewneck T-Shirt", "Apparel", "H&M", "Summit Wholesale", "pack", 6.00, 8.00, 50, 15, "Aisle B", "0 Months", 3),
        ("Puma Classic Suede Shoes", "Apparel", "Puma", "Summit Wholesale", "pcs", 65.00, 30.00, 15, 4, "Aisle B", "0 Months", 1),
        ("Under Armour Tech Polo", "Apparel", "Under Armour", "Prime Logistics", "pcs", 39.99, 18.00, 28, 8, "Aisle B", "0 Months", 1),
        ("Champion Reverse Weave Sweatshirt", "Apparel", "Champion", "Summit Wholesale", "pcs", 48.00, 22.00, 22, 6, "Aisle B", "0 Months", 1),
        ("Columbia Fleece Jacket", "Apparel", "Columbia", "Prime Logistics", "pcs", 59.99, 28.00, 12, 4, "Aisle B", "0 Months", 1),
        ("Calvin Klein Cotton Boxer Briefs", "Apparel", "Calvin Klein", "Summit Wholesale", "pack", 9.33, 12.00, 40, 10, "Aisle B", "0 Months", 3),
        # Grocery (21-30)
        ("Nestlé Pure Life Water (24pk)", "Grocery", "Nestlé", "Prime Logistics", "pack", 0.21, 2.50, 100, 20, "Aisle C", "0 Months", 24),
        ("Kraft Macaroni & Cheese", "Grocery", "Kraft", "Prime Logistics", "pcs", 1.25, 0.60, 150, 40, "Aisle C", "6 Months", 1),
        ("Kellogg's Frosted Flakes", "Grocery", "Kellogg's", "Prime Logistics", "pcs", 3.79, 1.80, 80, 20, "Aisle C", "12 Months", 1),
        ("Dole Canned Pineapple Slices", "Grocery", "Dole", "Prime Logistics", "pcs", 1.89, 0.90, 120, 30, "Aisle C", "24 Months", 1),
        ("Heinz Tomato Ketchup (32oz)", "Grocery", "Heinz", "Prime Logistics", "pcs", 2.99, 1.50, 90, 25, "Aisle C", "12 Months", 1),
        ("Campbell's Chicken Noodle Soup", "Grocery", "Campbell's", "Prime Logistics", "pcs", 1.09, 0.50, 200, 50, "Aisle C", "24 Months", 1),
        ("Quaker Oats Old Fashioned 18oz", "Grocery", "Quaker", "Prime Logistics", "pcs", 2.49, 1.20, 75, 20, "Aisle C", "18 Months", 1),
        ("Folgers Classic Roast Coffee", "Grocery", "Folgers", "Prime Logistics", "pcs", 7.99, 4.50, 60, 15, "Aisle C", "15 Months", 1),
        ("Skippy Creamy Peanut Butter", "Grocery", "Skippy", "Prime Logistics", "pcs", 3.49, 1.80, 85, 20, "Aisle C", "12 Months", 1),
        ("Barilla Spaghetti Pasta 1lb", "Grocery", "Barilla", "Prime Logistics", "pcs", 1.49, 0.70, 140, 35, "Aisle C", "24 Months", 1),
        # Pharmacy (31-40)
        ("Pfizer Advil Pain Reliever (100ct)", "Pharmacy", "Pfizer", "BioPharma Supplies", "pcs", 9.49, 4.50, 60, 15, "Aisle D", "24 Months", 1),
        ("Bayer Aspirin 81mg (120ct)", "Pharmacy", "Bayer", "BioPharma Supplies", "pcs", 6.29, 3.00, 50, 12, "Aisle D", "24 Months", 1),
        ("GSK Sensodyne Toothpaste", "Pharmacy", "GSK", "BioPharma Supplies", "pcs", 5.49, 2.50, 70, 18, "Aisle D", "18 Months", 1),
        ("J&J Band-Aid Variety Pack", "Pharmacy", "J&J", "BioPharma Supplies", "pcs", 3.99, 1.80, 90, 25, "Aisle D", "36 Months", 1),
        ("Roche Accu-Chek Test Strips", "Pharmacy", "Roche", "BioPharma Supplies", "pcs", 0.60, 15.00, 30, 8, "Aisle D", "12 Months", 50),
        ("Tylenol Extra Strength 500mg", "Pharmacy", "Tylenol", "BioPharma Supplies", "pcs", 10.49, 5.00, 65, 15, "Aisle D", "24 Months", 1),
        ("Vicks VapoRub Ointment 3.5oz", "Pharmacy", "Vicks", "BioPharma Supplies", "pcs", 5.99, 2.80, 45, 10, "Aisle D", "36 Months", 1),
        ("Centrum Adult Multivitamin", "Pharmacy", "Centrum", "BioPharma Supplies", "pcs", 12.99, 6.00, 40, 10, "Aisle D", "18 Months", 1),
        ("Claritin 24hr Allergy Relief", "Pharmacy", "Claritin", "BioPharma Supplies", "pcs", 22.49, 12.00, 35, 8, "Aisle D", "24 Months", 1),
        ("Neosporin Antiseptic Ointment", "Pharmacy", "Neosporin", "BioPharma Supplies", "pcs", 4.89, 2.20, 55, 12, "Aisle D", "36 Months", 1),
        # Home & Kitchen (41-50)
        ("Dyson V11 Cordless Vacuum", "Home & Kitchen", "Dyson", "Global Trade Co.", "pcs", 599.99, 380.00, 4, 2, "Warehouse", "24 Months", 1),
        ("Keurig K-Classic Coffee Maker", "Home & Kitchen", "Keurig", "Global Trade Co.", "pcs", 89.99, 50.00, 8, 3, "Aisle E", "12 Months", 1),
        ("Instant Pot Duo 7-in-1 (6qt)", "Home & Kitchen", "Instant Pot", "Global Trade Co.", "pcs", 79.99, 45.00, 15, 4, "Aisle E", "12 Months", 1),
        ("Pyrex Glass Food Storage Set", "Home & Kitchen", "Pyrex", "Summit Wholesale", "set", 3.50, 18.00, 20, 6, "Aisle E", "Lifetime", 10),
        ("Philips Sonicare Toothbrush", "Home & Kitchen", "Philips", "Apex Distributors", "pcs", 69.99, 40.00, 12, 3, "Aisle E", "24 Months", 1),
        ("Brita Everyday Water Pitcher", "Home & Kitchen", "Brita", "Summit Wholesale", "pcs", 19.99, 10.00, 25, 6, "Aisle E", "0 Months", 1),
        ("Lodge Cast Iron Skillet 10.25\"", "Home & Kitchen", "Lodge", "Summit Wholesale", "pcs", 24.90, 14.00, 18, 5, "Aisle E", "Lifetime", 1),
        ("T-fal Nonstick Cookware Set", "Home & Kitchen", "T-fal", "Summit Wholesale", "set", 7.50, 45.00, 10, 3, "Warehouse", "12 Months", 12),
        ("Cuisinart 14-Cup Food Processor", "Home & Kitchen", "Cuisinart", "Global Trade Co.", "pcs", 179.99, 110.00, 5, 2, "Aisle E", "36 Months", 1),
        ("Hamilton Beach Electric Kettle", "Home & Kitchen", "Hamilton Beach", "Summit Wholesale", "pcs", 21.99, 12.00, 22, 6, "Aisle E", "12 Months", 1),
    ]
    
    for r_idx, p in enumerate(dummy_products, 7):
        # A: Product ID = IF(ISBLANK(B{r}), "", "PRD-" & TEXT(ROW()-6, "00000"))
        ws_prod.cell(row=r_idx, column=1, value=f'=IF(ISBLANK(B{r_idx}), "", "PRD-" & TEXT(ROW()-6, "00000"))')
        # B: Name, C: Category, D: Brand, E: Supplier, F: UOM
        ws_prod.cell(row=r_idx, column=2, value=p[0])
        ws_prod.cell(row=r_idx, column=3, value=p[1])
        ws_prod.cell(row=r_idx, column=4, value=p[2])
        ws_prod.cell(row=r_idx, column=5, value=p[3])
        ws_prod.cell(row=r_idx, column=6, value=p[4])
        # G: Unit Price (p[5])
        ws_prod.cell(row=r_idx, column=7, value=p[5])
        # H: Cost Price (p[6])
        ws_prod.cell(row=r_idx, column=8, value=p[6])
        # I: Selling Price = Unit Price (G) * Quantity per Set (R)
        ws_prod.cell(row=r_idx, column=9, value=f'=G{r_idx} * R{r_idx}')
        # J: Initial Stock (p[7])
        ws_prod.cell(row=r_idx, column=10, value=p[7])
        
        # Formulas:
        # K: Purchases Qty = SUMIF(PurchaseEntry[Product ID], A{r}, PurchaseEntry[Quantity Purchased])
        ws_prod.cell(row=r_idx, column=11, value=f'=SUMIF(PurchaseEntry[Product ID], A{r_idx}, PurchaseEntry[Quantity Purchased])')
        # L: Sales Qty = SUMIF(SalesEntry[Product ID], A{r}, SalesEntry[Quantity Sold])
        ws_prod.cell(row=r_idx, column=12, value=f'=SUMIF(SalesEntry[Product ID], A{r_idx}, SalesEntry[Quantity Sold])')
        # M: Current Stock = Initial Stock (J) + Purchases Qty (K) - Sales Qty (L)
        ws_prod.cell(row=r_idx, column=13, value=f'=J{r_idx} + K{r_idx} - L{r_idx}')
        # N: Reorder Level (p[8])
        ws_prod.cell(row=r_idx, column=14, value=p[8])
        # O: Storage Location (p[9])
        ws_prod.cell(row=r_idx, column=15, value=p[9])
        # P: Status = IF(Current Stock<=0, "Out of Stock", IF(Current Stock<=Reorder Level, "Low Stock", "In Stock"))
        ws_prod.cell(row=r_idx, column=16, value=f'=IF(M{r_idx}<=0, "Out of Stock", IF(M{r_idx}<=N{r_idx}, "Low Stock", "In Stock"))')
        # Q: Warranty Period (p[10])
        ws_prod.cell(row=r_idx, column=17, value=p[10])
        # R: Quantity per Set (p[11])
        ws_prod.cell(row=r_idx, column=18, value=p[11])
        # S: Set Price = IF(Quantity per Set>1, Selling Price * 0.95, Selling Price)
        ws_prod.cell(row=r_idx, column=19, value=f'=IF(R{r_idx}>1, I{r_idx} * 0.95, I{r_idx})')
        # T: Stock Value = Current Stock (M) * Cost Price (H)
        ws_prod.cell(row=r_idx, column=20, value=f'=M{r_idx} * H{r_idx}')
        # U: Total Sales Value = Sales Qty (L) * Selling Price (I)
        ws_prod.cell(row=r_idx, column=21, value=f'=L{r_idx} * I{r_idx}')
        # V: FIFO Stock Value = MAX(0, Initial Stock - Sales Qty) * Cost Price + SUMIF(PurchaseEntry[Product ID], Product ID, PurchaseEntry[FIFO Value])
        ws_prod.cell(row=r_idx, column=22, value=f'=MAX(0, J{r_idx}-L{r_idx}) * H{r_idx} + SUMIF(PurchaseEntry[Product ID], A{r_idx}, PurchaseEntry[FIFO Value])')
        # W: Margin % = IF(Total Sales Value>0, (Total Sales Value - Sales Qty * Cost Price) / Total Sales Value, 0)
        ws_prod.cell(row=r_idx, column=23, value=f'=IF(U{r_idx}>0, (U{r_idx} - (L{r_idx}*H{r_idx})) / U{r_idx}, 0)')
        
        # Style row cells
        for col_idx in range(1, 24):
            cell = ws_prod.cell(row=r_idx, column=col_idx)
            cell.font = font_data
            cell.border = thin_border
            if r_idx % 2 == 0:
                cell.fill = fill_zebra
            
            # Formats
            if col_idx in [7, 8, 9, 19, 20, 21, 22]:
                cell.number_format = "$#,##0.00"
                cell.alignment = align_right
            elif col_idx in [10, 11, 12, 13, 14, 18]:
                cell.number_format = "#,##0"
                cell.alignment = align_right
            elif col_idx in [1, 3, 6, 15, 16, 17]:
                cell.alignment = align_center
            elif col_idx == 23:
                cell.number_format = "0.0%"
                cell.alignment = align_right

    # Add Excel Table (A6:W56)
    tab_prod = Table(displayName="ProductMaster", ref=f"A6:W{len(dummy_products)+6}")
    tab_prod.tableStyleInfo = TableStyleInfo(name="TableStyleMedium9", showRowStripes=True)
    ws_prod.add_table(tab_prod)
    ws_prod.freeze_panes = "A7"

    # Data Validations for Product Master
    dv_cat = DataValidation(type="list", formula1="ReferenceLists!$A$2:$A$6", allow_blank=True)
    ws_prod.add_data_validation(dv_cat)
    dv_cat.add(f"C7:C{len(dummy_products)+6}")
    
    dv_loc = DataValidation(type="list", formula1="ReferenceLists!$B$2:$B$6", allow_blank=True)
    ws_prod.add_data_validation(dv_loc)
    dv_loc.add(f"O7:O{len(dummy_products)+6}")
    
    dv_sup = DataValidation(type="list", formula1="'Supplier Management'!$B$7:$B$16", allow_blank=True)
    ws_prod.add_data_validation(dv_sup)
    dv_sup.add(f"E7:E{len(dummy_products)+6}")

    # ----------------------------------------------------
    # SHEET 3: PURCHASE ENTRY
    # ----------------------------------------------------
    ws_purch = wb.create_sheet("Purchase Entry")
    apply_header_and_nav(ws_purch, "Purchase Entry Ledger")
    
    purch_headers = [
        "Purchase ID", "Date", "Product ID", "Product Name", 
        "Supplier Name", "Quantity Purchased", "Cost Price", "Total Cost",
        "Cum Purchases", "FIFO Remaining Qty", "FIFO Value"
    ]
    
    for col_idx, h in enumerate(purch_headers, 1):
        cell = ws_purch.cell(row=6, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_navy
        cell.alignment = align_center
        cell.border = thin_border

    # Sample Purchase Transactions
    purchases_data = [
        (datetime.date(2026, 1, 15), "PRD-00001", 10),
        (datetime.date(2026, 1, 20), "PRD-00002", 5),
        (datetime.date(2026, 2, 5), "PRD-00003", 5),
        (datetime.date(2026, 2, 10), "PRD-00006", 15),
        (datetime.date(2026, 2, 28), "PRD-00011", 10),
        (datetime.date(2026, 3, 1), "PRD-00015", 30),
        (datetime.date(2026, 3, 5), "PRD-00021", 50),
        (datetime.date(2026, 3, 10), "PRD-00031", 20),
        (datetime.date(2026, 3, 15), "PRD-00041", 3),
        (datetime.date(2026, 4, 1), "PRD-00001", 15),
        (datetime.date(2026, 4, 5), "PRD-00002", 10),
        (datetime.date(2026, 4, 10), "PRD-00003", 10),
        (datetime.date(2026, 4, 15), "PRD-00006", 20),
        (datetime.date(2026, 4, 20), "PRD-00011", 15),
        (datetime.date(2026, 5, 1), "PRD-00015", 40),
        (datetime.date(2026, 5, 5), "PRD-00021", 80),
        (datetime.date(2026, 5, 10), "PRD-00031", 25),
        (datetime.date(2026, 5, 15), "PRD-00041", 5)
    ]
    
    for r_idx, p in enumerate(purchases_data, 7):
        # A: Purchase ID
        ws_purch.cell(row=r_idx, column=1, value=f'="PUR-" & TEXT(ROW()-6, "00000")')
        # B: Date, C: Product ID, F: Qty Purchased
        ws_purch.cell(row=r_idx, column=2, value=p[0])
        ws_purch.cell(row=r_idx, column=3, value=p[1])
        # D: Product Name
        ws_purch.cell(row=r_idx, column=4, value=f'=IFERROR(VLOOKUP(C{r_idx}, ProductMaster, 2, FALSE), "")')
        # E: Supplier Name
        ws_purch.cell(row=r_idx, column=5, value=f'=IFERROR(VLOOKUP(C{r_idx}, ProductMaster, 5, FALSE), "")')
        ws_purch.cell(row=r_idx, column=6, value=p[2])
        # G: Cost Price VLOOKUP (Lookups column 8 of ProductMaster)
        ws_purch.cell(row=r_idx, column=7, value=f'=IFERROR(VLOOKUP(C{r_idx}, ProductMaster, 8, FALSE), 0)')
        # H: Total Cost = Qty Purchased (F) * Cost Price (G)
        ws_purch.cell(row=r_idx, column=8, value=f'=F{r_idx} * G{r_idx}')
        # I: Cum Purchases (Running Sum of Quantity Purchased for this Product ID)
        ws_purch.cell(row=r_idx, column=9, value=f'=SUMIFS(INDEX([Quantity Purchased], 1):[@[Quantity Purchased]], INDEX([Product ID], 1):[@[Product ID]], [@[Product ID]])')
        # J: FIFO Remaining Qty = MAX(0, MIN([@[Quantity Purchased]], [@[Cum Purchases]] - MAX(0, SUMIF(SalesEntry[Product ID], [@[Product ID]], SalesEntry[Quantity Sold]) - IFERROR(VLOOKUP([@[Product ID]], ProductMaster, 10, FALSE), 0))))
        # Note: 10 is the index of Initial Stock (J) in Product Master
        ws_purch.cell(row=r_idx, column=10, value=f'=MAX(0, MIN([@[Quantity Purchased]], [@[Cum Purchases]] - MAX(0, SUMIF(SalesEntry[Product ID], [@[Product ID]], SalesEntry[Quantity Sold]) - IFERROR(VLOOKUP([@[Product ID]], ProductMaster, 10, FALSE), 0))))')
        # K: FIFO Value = FIFO Remaining Qty (J) * Cost Price (G)
        ws_purch.cell(row=r_idx, column=11, value=f'=J{r_idx} * G{r_idx}')
        
        for col_idx in range(1, 12):
            cell = ws_purch.cell(row=r_idx, column=col_idx)
            cell.font = font_data
            cell.border = thin_border
            if r_idx % 2 == 0:
                cell.fill = fill_zebra
                
            # Formats
            if col_idx in [7, 8, 11]:
                cell.number_format = "$#,##0.00"
                cell.alignment = align_right
            elif col_idx in [6, 9, 10]:
                cell.number_format = "#,##0"
                cell.alignment = align_right
            elif col_idx in [1, 2, 3]:
                cell.alignment = align_center
            if col_idx == 2:
                cell.number_format = "YYYY-MM-DD"
                
    # Add Table (A6:K24)
    tab_purch = Table(displayName="PurchaseEntry", ref=f"A6:K{len(purchases_data)+6}")
    tab_purch.tableStyleInfo = TableStyleInfo(name="TableStyleMedium9", showRowStripes=True)
    ws_purch.add_table(tab_purch)
    ws_purch.freeze_panes = "A7"
    
    # Validation
    dv_prod_p = DataValidation(type="list", formula1="'Product Master'!$A$7:$A$56", allow_blank=True)
    ws_purch.add_data_validation(dv_prod_p)
    dv_prod_p.add(f"C7:C1000")

    # ----------------------------------------------------
    # SHEET 4: SALES ENTRY
    # ----------------------------------------------------
    ws_sales = wb.create_sheet("Sales Entry")
    apply_header_and_nav(ws_sales, "Sales Ledger Log")
    
    sales_headers = [
        "Sales ID", "Date", "Product ID", "Product Name", 
        "Quantity Sold", "Selling Price", "Total Amount", "Payment Method"
    ]
    
    for col_idx, h in enumerate(sales_headers, 1):
        cell = ws_sales.cell(row=6, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_navy
        cell.alignment = align_center
        cell.border = thin_border

    # Sample Sales Transactions
    sales_data = [
        (datetime.date(2026, 1, 16), "PRD-00001", 2, "Cash"),
        (datetime.date(2026, 1, 22), "PRD-00002", 1, "Credit Card"),
        (datetime.date(2026, 1, 25), "PRD-00001", 1, "Debit Card"),
        (datetime.date(2026, 2, 6), "PRD-00003", 2, "Mobile Wallet"),
        (datetime.date(2026, 2, 12), "PRD-00006", 3, "Cash"),
        (datetime.date(2026, 2, 14), "PRD-00001", 4, "Credit Card"),
        (datetime.date(2026, 2, 20), "PRD-00002", 2, "Debit Card"),
        (datetime.date(2026, 3, 2), "PRD-00011", 5, "Bank Transfer"),
        (datetime.date(2026, 3, 4), "PRD-00015", 10, "Cash"),
        (datetime.date(2026, 3, 8), "PRD-00021", 20, "Mobile Wallet"),
        (datetime.date(2026, 3, 12), "PRD-00031", 12, "Credit Card"),
        (datetime.date(2026, 3, 18), "PRD-00041", 2, "Bank Transfer"),
        (datetime.date(2026, 4, 2), "PRD-00001", 5, "Cash"),
        (datetime.date(2026, 4, 8), "PRD-00002", 3, "Credit Card"),
        (datetime.date(2026, 4, 12), "PRD-00003", 4, "Debit Card"),
        (datetime.date(2026, 4, 18), "PRD-00006", 8, "Mobile Wallet"),
        (datetime.date(2026, 4, 22), "PRD-00011", 6, "Cash"),
        (datetime.date(2026, 5, 2), "PRD-00015", 15, "Credit Card"),
        (datetime.date(2026, 5, 8), "PRD-00021", 40, "Debit Card"),
        (datetime.date(2026, 5, 12), "PRD-00031", 10, "Mobile Wallet"),
        (datetime.date(2026, 5, 18), "PRD-00041", 2, "Bank Transfer")
    ]
    
    for r_idx, p in enumerate(sales_data, 7):
        # A: Sales ID
        ws_sales.cell(row=r_idx, column=1, value=f'="SAL-" & TEXT(ROW()-6, "00000")')
        # B: Date, C: Product ID, E: Quantity Sold, H: Payment Method
        ws_sales.cell(row=r_idx, column=2, value=p[0])
        ws_sales.cell(row=r_idx, column=3, value=p[1])
        # D: Product Name
        ws_sales.cell(row=r_idx, column=4, value=f'=IFERROR(VLOOKUP(C{r_idx}, ProductMaster, 2, FALSE), "")')
        ws_sales.cell(row=r_idx, column=5, value=p[2])
        # F: Selling Price (Lookups column 9 of ProductMaster)
        ws_sales.cell(row=r_idx, column=6, value=f'=IFERROR(VLOOKUP(C{r_idx}, ProductMaster, 9, FALSE), 0)')
        # G: Total Amount = Quantity Sold (E) * Selling Price (F)
        ws_sales.cell(row=r_idx, column=7, value=f'=E{r_idx} * F{r_idx}')
        ws_sales.cell(row=r_idx, column=8, value=p[3])
        
        for col_idx in range(1, 9):
            cell = ws_sales.cell(row=r_idx, column=col_idx)
            cell.font = font_data
            cell.border = thin_border
            if r_idx % 2 == 0:
                cell.fill = fill_zebra
                
            # Formats
            if col_idx in [6, 7]:
                cell.number_format = "$#,##0.00"
                cell.alignment = align_right
            elif col_idx in [5]:
                cell.number_format = "#,##0"
                cell.alignment = align_right
            elif col_idx in [1, 2, 3, 8]:
                cell.alignment = align_center
            if col_idx == 2:
                cell.number_format = "YYYY-MM-DD"
                
    # Add Table (A6:H27)
    tab_sales = Table(displayName="SalesEntry", ref=f"A6:H{len(sales_data)+6}")
    tab_sales.tableStyleInfo = TableStyleInfo(name="TableStyleMedium9", showRowStripes=True)
    ws_sales.add_table(tab_sales)
    ws_sales.freeze_panes = "A7"
    
    # Validations
    dv_prod_s = DataValidation(type="list", formula1="'Product Master'!$A$7:$A$56", allow_blank=True)
    ws_sales.add_data_validation(dv_prod_s)
    dv_prod_s.add(f"C7:C1000")
    
    dv_pay = DataValidation(type="list", formula1="ReferenceLists!$C$2:$C$6", allow_blank=True)
    ws_sales.add_data_validation(dv_pay)
    dv_pay.add(f"H7:H1000")
    
    # Quantity validation: prevent selling more than stock
    # 13 is Current Stock (M) in Product Master, 1 is Product ID (A) in Product Master
    dv_qty = DataValidation(type="custom", formula1="=E7<=INDEX('Product Master'!$M$7:$M$56,MATCH(C7,'Product Master'!$A$7:$A$56,0))+E7", allow_blank=True)
    dv_qty.error = "Quantity exceeds available stock! Sales transaction blocked."
    dv_qty.errorTitle = "Stock Limit Exceeded"
    ws_sales.add_data_validation(dv_qty)
    dv_qty.add(f"E7:E1000")

    # ----------------------------------------------------
    # SHEET 6: REPORTS SHEET
    # ----------------------------------------------------
    ws_rep = wb.create_sheet("Reports")
    apply_header_and_nav(ws_rep, "Automated Reports Summary")
    
    # Financial metrics boxes (D5:I8)
    def style_metric_box(ws, start_col, start_row, end_col, end_row, title, formula, number_fmt=None):
        ws.merge_cells(start_row=start_row, start_column=start_col, end_row=start_row, end_column=end_col)
        ws.merge_cells(start_row=start_row+1, start_column=start_col, end_row=end_row, end_column=end_col)
        
        lbl_cell = ws.cell(row=start_row, column=start_col, value=title.upper())
        lbl_cell.font = Font(name="Segoe UI", size=8, bold=True, color=GRAY_TEXT)
        lbl_cell.alignment = align_center
        
        val_cell = ws.cell(row=start_row+1, column=start_col, value=formula)
        val_cell.font = Font(name="Segoe UI", size=14, bold=True, color=NAVY)
        val_cell.alignment = align_center
        if number_fmt:
            val_cell.number_format = number_fmt
            
        for r in range(start_row, end_row+1):
            for c in range(start_col, end_col+1):
                cell = ws.cell(row=r, column=c)
                cell.fill = fill_kpi
                cell.border = thin_border

    style_metric_box(ws_rep, 1, 6, 4, 7, "Cost of Goods Sold (COGS)", 
                     "=SUMPRODUCT(SalesEntry[Quantity Sold], SUMIF(ProductMaster[Product ID], SalesEntry[Product ID], ProductMaster[Cost Price]))", 
                     "$#,##0.00")
                     
    style_metric_box(ws_rep, 6, 6, 9, 7, "Average Inventory Value", 
                     "=(SUMPRODUCT(ProductMaster[Initial Stock], ProductMaster[Cost Price]) + SUM(ProductMaster[Stock Value])) / 2", 
                     "$#,##0.00")
                     
    style_metric_box(ws_rep, 11, 6, 14, 7, "Inventory Turnover Ratio", 
                     "=IF(F7>0, A7/F7, 0)", 
                     "0.00")
                     
    style_metric_box(ws_rep, 16, 6, 19, 7, "Days Sales of Inventory (DSI)", 
                     "=IF(K7>0, 365/K7, 0)", 
                     "0.0")

    # Dynamic low stock report
    ws_rep.cell(row=10, column=1, value="CRITICAL LOW STOCK REPORT (Dynamic FILTER)").font = font_bold
    rep_cols = ["Product ID", "Product Name", "Category", "Current Stock", "Reorder Level", "Status"]
    for idx, col_name in enumerate(rep_cols, 1):
        cell = ws_rep.cell(row=11, column=idx, value=col_name)
        cell.font = font_header
        cell.fill = fill_navy
        cell.alignment = align_center
        cell.border = thin_border
        
    # Spill Formula in A12 (CHOOSECOLS: 1=ID, 2=Name, 3=Category, 13=CurrentStock, 14=ReorderLevel, 16=Status)
    ws_rep.cell(row=12, column=1, value='=IFERROR(FILTER(CHOOSECOLS(ProductMaster,1,2,3,13,14,16), (ProductMaster[Status]="Low Stock")+(ProductMaster[Status]="Out of Stock")), "All stock levels normal")')
    
    # Formatting for low stock rows (A12:F30)
    for r in range(12, 31):
        for c in range(1, 7):
            cell = ws_rep.cell(row=r, column=c)
            cell.font = font_data
            cell.border = thin_border
            if c in [1, 3, 6]:
                cell.alignment = align_center
            if c in [4, 5]:
                cell.alignment = align_right
                cell.number_format = "#,##0"

    # Dynamic dead stock report
    ws_rep.cell(row=10, column=9, value="DEAD STOCK REPORT (Dynamic FILTER)").font = font_bold
    for idx, col_name in enumerate(rep_cols[:5], 9):
        cell = ws_rep.cell(row=11, column=idx, value=col_name)
        cell.font = font_header
        cell.fill = fill_navy
        cell.alignment = align_center
        cell.border = thin_border
        
    # Spill Formula in I12 (CHOOSECOLS: 1=ID, 2=Name, 3=Category, 13=CurrentStock, 14=ReorderLevel)
    ws_rep.cell(row=12, column=9, value='=IFERROR(FILTER(CHOOSECOLS(ProductMaster,1,2,3,13,14), (ProductMaster[Current Stock]>0)*(ProductMaster[Sales Qty]=0)), "No dead stock found")')
    
    # Formatting for dead stock rows (I12:M30)
    for r in range(12, 31):
        for c in range(9, 14):
            cell = ws_rep.cell(row=r, column=c)
            cell.font = font_data
            cell.border = thin_border
            if c in [9, 11]:
                cell.alignment = align_center
            if c in [12, 13]:
                cell.alignment = align_right
                cell.number_format = "#,##0"

    # ----------------------------------------------------
    # SHEET 7: INVOICE SHEET (PRINTABLE)
    # ----------------------------------------------------
    ws_inv = wb.create_sheet("Invoice")
    apply_header_and_nav(ws_inv, "Retail Sales Invoice")
    
    # Title Block
    ws_inv.merge_cells("A6:C8")
    ws_inv["A6"] = "RETAIL STORE INC.\n123 Market St, Suite 100\nPhone: (555) 0199 | billing@store.com"
    ws_inv["A6"].font = font_italic
    ws_inv["A6"].alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    
    ws_inv.merge_cells("H6:K8")
    ws_inv["H6"] = "INVOICE: #INV-2026001\nDATE: 2026-05-25\nCUSTOMER: Walk-in Retail Client"
    ws_inv["H6"].font = font_bold
    ws_inv["H6"].alignment = Alignment(horizontal="right", vertical="center", wrap_text=True)
    
    # Table headers
    ws_inv.row_dimensions[10].height = 25
    inv_header_defs = [
        ("A10", "S.No."),
        ("B10", "Product ID"),
        ("D10", "Product Name"),
        ("G10", "Category"),
        ("H10", "Quantity"),
        ("I10", "Unit Price"),
        ("K10", "Total Amount")
    ]
    
    # Merge mappings for header and data rows
    merges_inv = [
        ("B", "C"),
        ("D", "F"),
        ("I", "J"),
        ("K", "L")
    ]
    
    for ref, name in inv_header_defs:
        ws_inv[ref] = name
        ws_inv[ref].font = font_header
        ws_inv[ref].fill = fill_navy
        ws_inv[ref].alignment = align_center
        ws_inv[ref].border = thin_border
        
    for start_c, end_c in merges_inv:
        ws_inv.merge_cells(f"{start_c}10:{end_c}10")
        # Apply borders to merged parts
        for col_letter in [start_c, end_c]:
            ws_inv[f"{col_letter}10"].border = thin_border
            
    # Printable invoice rows (10 items, rows 11 to 20)
    for i in range(1, 11):
        r = 10 + i
        ws_inv.row_dimensions[r].height = 20
        
        # S.No.
        ws_inv.cell(row=r, column=1, value=i).alignment = align_center
        
        # Product ID (Dropdown input in Column B)
        ws_inv.cell(row=r, column=2, value="PRD-00001" if i==1 else "PRD-00006" if i==2 else "").alignment = align_center
        
        # Merge columns
        for start_c, end_c in merges_inv:
            ws_inv.merge_cells(f"{start_c}{r}:{end_c}{r}")
            
        # Product Name
        ws_inv.cell(row=r, column=4, value=f'=IFERROR(VLOOKUP(B{r}, ProductMaster, 2, FALSE), "")').alignment = align_left
        # Category
        ws_inv.cell(row=r, column=7, value=f'=IFERROR(VLOOKUP(B{r}, ProductMaster, 3, FALSE), "")').alignment = align_center
        # Quantity (Input in Column H)
        ws_inv.cell(row=r, column=8, value=2 if i==1 else 1 if i==2 else "").alignment = align_right
        # Unit Price (Lookup Column 9 = Selling Price)
        ws_inv.cell(row=r, column=9, value=f'=IFERROR(VLOOKUP(B{r}, ProductMaster, 9, FALSE), 0)').alignment = align_right
        ws_inv.cell(row=r, column=9).number_format = "$#,##0.00"
        # Total Amount
        ws_inv.cell(row=r, column=11, value=f'=IF(ISBLANK(B{r}), 0, H{r} * I{r})').alignment = align_right
        ws_inv.cell(row=r, column=11).number_format = "$#,##0.00"
        
        # Apply borders and fonts to all cells
        for c in range(1, 13):
            cell = ws_inv.cell(row=r, column=c)
            cell.font = font_data
            cell.border = thin_border
            if r % 2 == 0:
                cell.fill = fill_zebra
                
    # Invoice Totals (Bottom-Right, rows 22 to 25)
    totals_defs = [
        ("I22", "K22", "Subtotal", "=SUM(K11:K20)"),
        ("I23", "K23", "Discount (5%)", "=K22 * 0.05"),
        ("I24", "K24", "Tax (8.25%)", "=(K22 - K23) * 0.0825"),
        ("I25", "K25", "Total Due", "=K22 - K23 + K24")
    ]
    
    for lbl_start, val_start, label, formula in totals_defs:
        lbl_letter = lbl_start[0]
        val_letter = val_start[0]
        r = lbl_start[1:]
        
        # Merge labels
        ws_inv.merge_cells(f"{lbl_letter}{r}:{chr(ord(lbl_letter)+1)}{r}")
        ws_inv[lbl_start] = label
        ws_inv[lbl_start].font = font_bold
        ws_inv[lbl_start].alignment = align_right
        ws_inv[lbl_start].border = thin_border
        ws_inv[f"{chr(ord(lbl_letter)+1)}{r}"].border = thin_border
        
        # Merge values
        ws_inv.merge_cells(f"{val_letter}{r}:{chr(ord(val_letter)+1)}{r}")
        ws_inv[val_start] = formula
        ws_inv[val_start].font = font_bold
        ws_inv[val_start].alignment = align_right
        ws_inv[val_start].border = thin_border
        ws_inv[val_start].number_format = "$#,##0.00"
        ws_inv[f"{chr(ord(val_letter)+1)}{r}"].border = thin_border
        
        if label == "Total Due":
            ws_inv[lbl_start].fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
            ws_inv[val_start].fill = PatternFill(start_color="CBD5E1", end_color="CBD5E1", fill_type="solid")
            
    # Add Terms and Footer
    ws_inv.merge_cells("A22:F23")
    ws_inv["A22"] = "Payment Methods Accepted: Cash, Credit Card, Bank Transfer\nThank you for shopping with us!"
    ws_inv["A22"].font = font_italic
    ws_inv["A22"].alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
    
    # Validation for Invoice Product Selection (Column B, Row 11 to 20)
    dv_inv_prod = DataValidation(type="list", formula1="'Product Master'!$A$7:$A$56", allow_blank=True)
    ws_inv.add_data_validation(dv_inv_prod)
    dv_inv_prod.add("B11:B20")

    # ----------------------------------------------------
    # SHEET 1: DASHBOARD SHEET
    # ----------------------------------------------------
    ws_dash = wb.create_sheet("Dashboard")
    apply_header_and_nav(ws_dash, "Store Inventory & Sales Performance Dashboard")
    
    # KPI Box Generator for Dashboard
    def make_kpi_card(ws, start_col, title, formula, number_fmt=None):
        r_title = 6
        r_val = 7
        end_col = start_col + 2
        
        ws.merge_cells(start_row=r_title, start_column=start_col, end_row=r_title, end_column=end_col)
        ws.merge_cells(start_row=r_val, start_column=start_col, end_row=r_val+1, end_column=end_col)
        
        lbl_cell = ws.cell(row=r_title, column=start_col, value=title.upper())
        lbl_cell.font = font_kpi_lbl
        lbl_cell.alignment = align_center
        
        val_cell = ws.cell(row=r_val, column=start_col, value=formula)
        val_cell.font = font_kpi_num
        val_cell.alignment = align_center
        
        if number_fmt:
            val_cell.number_format = number_fmt
            
        # Draw border & fill
        for r in range(r_title, r_val+2):
            for c in range(start_col, end_col+1):
                cell = ws.cell(row=r, column=c)
                cell.fill = fill_kpi
                cell.border = thin_border
                
    make_kpi_card(ws_dash, 1, "Total Products Registries", "=COUNTA(ProductMaster[Product ID])")
    make_kpi_card(ws_dash, 5, "Total Inventory Valuation", "=SUM(ProductMaster[Stock Value])", "$#,##0.00")
    make_kpi_card(ws_dash, 9, "Low Stock Alerts", '=COUNTIF(ProductMaster[Status], "Low Stock")')
    make_kpi_card(ws_dash, 13, "Out of Stock Items", '=COUNTIF(ProductMaster[Status], "Out of Stock")')
    make_kpi_card(ws_dash, 17, "Monthly Total Revenue", "=SUM(SalesEntry[Total Amount])", "$#,##0.00")
    
    # Helper tables for charts in Dashboard (driven in side columns X & AA)
    # Side Category Summary (Row 10 to 15, columns X:Y)
    ws_dash.cell(row=10, column=24, value="Category").font = font_bold
    ws_dash.cell(row=10, column=25, value="Stock Value").font = font_bold
    for idx, cat in enumerate(categories):
        r = 11 + idx
        ws_dash.cell(row=r, column=24, value=cat).font = font_data
        ws_dash.cell(row=r, column=25, value=f'=SUMIF(ProductMaster[Category], X{r}, ProductMaster[Stock Value])').number_format = "$#,##0.00"
        
    # Side Monthly Sales Trend (Row 10 to 15, columns AA:AB)
    ws_dash.cell(row=10, column=27, value="Month").font = font_bold
    ws_dash.cell(row=10, column=28, value="Sales Value").font = font_bold
    
    months = [
        ("Jan", "2026-01-01", "2026-01-31"),
        ("Feb", "2026-02-01", "2026-02-28"),
        ("Mar", "2026-03-01", "2026-03-31"),
        ("Apr", "2026-04-01", "2026-04-30"),
        ("May", "2026-05-01", "2026-05-31")
    ]
    
    for idx, (m_lbl, sd, ed) in enumerate(months):
        r = 11 + idx
        ws_dash.cell(row=r, column=27, value=m_lbl).font = font_data
        ws_dash.cell(row=r, column=28, value=f'=SUMIFS(SalesEntry[Total Amount], SalesEntry[Date], ">={sd}", SalesEntry[Date], "<={ed}")').number_format = "$#,##0.00"

    # Add Charts
    # Chart 1: Stock Value by Category (Col B Chart)
    chart1 = BarChart()
    chart1.type = "col"
    chart1.style = 10
    chart1.title = "Inventory Value by Category"
    chart1.y_axis.title = "Value ($)"
    chart1.x_axis.title = "Category"
    chart1.height = 10
    chart1.width = 15
    
    data1 = Reference(ws_dash, min_col=25, min_row=10, max_row=15) # Column Y
    cats1 = Reference(ws_dash, min_col=24, min_row=11, max_row=15) # Column X
    chart1.add_data(data1, titles_from_data=True)
    chart1.set_categories(cats1)
    chart1.legend = None
    ws_dash.add_chart(chart1, "A10")
    
    # Chart 2: Monthly Sales Trend (Col J Chart)
    chart2 = LineChart()
    chart2.title = "Sales Revenue Trends"
    chart2.style = 13
    chart2.y_axis.title = "Revenue ($)"
    ws_dash.cell(row=10, column=28).font = font_bold # Ensures chart reads column header
    chart2.height = 10
    chart2.width = 15
    
    data2 = Reference(ws_dash, min_col=28, min_row=10, max_row=15) # Column AB
    cats2 = Reference(ws_dash, min_col=27, min_row=11, max_row=15) # Column AA
    chart2.add_data(data2, titles_from_data=True)
    chart2.set_categories(cats2)
    chart2.legend = None
    ws_dash.add_chart(chart2, "I10")

    # Bottom Dashboard tables: Top 5 Selling Products & Top Stock Alerts
    ws_dash.cell(row=21, column=1, value="CRITICAL LOW STOCK ALERTS").font = font_bold
    ws_dash.cell(row=21, column=9, value="TOP 5 SELLING PRODUCTS").font = font_bold
    
    # Low stock dashboard table headers
    dash_low_headers = ["Product ID", "Product Name", "Current Stock", "Reorder Level", "Status"]
    for idx, val in enumerate(dash_low_headers, 1):
        cell = ws_dash.cell(row=22, column=idx, value=val)
        cell.font = font_header
        cell.fill = fill_navy
        cell.alignment = align_center
        cell.border = thin_border
        
    # Spill dynamic filter into Dashboard A23 (Current Stock is 13, Reorder Level is 14, Status is 16)
    ws_dash.cell(row=23, column=1, value='=IFERROR(FILTER(CHOOSECOLS(ProductMaster,1,2,13,14,16), (ProductMaster[Status]="Low Stock")+(ProductMaster[Status]="Out of Stock")), "All stock levels normal")')
    
    for r in range(23, 29):
        for c in range(1, 6):
            cell = ws_dash.cell(row=r, column=c)
            cell.font = font_data
            cell.border = thin_border
            if c in [1, 5]:
                cell.alignment = align_center
            if c in [3, 4]:
                cell.alignment = align_right
                cell.number_format = "#,##0"

    # Top selling dashboard table headers
    dash_top_headers = ["Product ID", "Product Name", "Qty Sold", "Sales Value", "Margin %"]
    for idx, val in enumerate(dash_top_headers, 9):
        cell = ws_dash.cell(row=22, column=idx, value=val)
        cell.font = font_header
        cell.fill = fill_navy
        cell.alignment = align_center
        cell.border = thin_border
        
    # Spill top selling into Dashboard I23 (ID=1, Name=2, QtySold=12, SalesValue=21, Margin=23)
    ws_dash.cell(row=23, column=9, value='=IFERROR(TAKE(SORT(FILTER(CHOOSECOLS(ProductMaster,1,2,12,21,23), ProductMaster[Total Sales Value]>0), 4, -1), 5), "No sales recorded yet")')
    
    for r in range(23, 29):
        for c in range(9, 14):
            cell = ws_dash.cell(row=r, column=c)
            cell.font = font_data
            cell.border = thin_border
            if c == 9:
                cell.alignment = align_center
            if c in [11, 12]:
                cell.alignment = align_right
                cell.number_format = "#,##0" if c==11 else "$#,##0.00"
            if c == 13:
                cell.alignment = align_right
                cell.number_format = "0.0%"

    # Move Dashboard to front
    wb._sheets = [ws_dash, ws_prod, ws_purch, ws_sales, ws_supl, ws_rep, ws_inv, ws_refs]

    # ----------------------------------------------------
    # FINAL SHEET FORMATTING: ALIGNMENTS, COLUMN WIDTHS & LOCKING
    # ----------------------------------------------------
    for ws in wb.worksheets:
        if ws.title == "ReferenceLists":
            continue
            
        # Freeze panes
        if ws.title == "Dashboard":
            ws.freeze_panes = "A5"
        
        # Unlock input cells & Protect formulas (leaves sheet unprotected by default for easy playing)
        ws.protection.sheet = False
        
        # Autoadjust column widths
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val = str(cell.value or '')
                if val.startswith('='):
                    # Estimate length of formula outputs to prevent massive columns
                    if "VLOOKUP" in val or "ProductMaster" in val:
                        max_len = max(max_len, 15)
                    elif "SUM" in val or "SUMIFS" in val:
                        max_len = max(max_len, 12)
                    else:
                        max_len = max(max_len, 10)
                else:
                    max_len = max(max_len, len(val))
            ws.column_dimensions[col_letter].width = max(max_len + 3, 11)
            
    # Setup Conditional Formatting for Status column in Product Master (P7:P56) -- Status is 16th column (P)
    rule_green = CellIsRule(operator='equal', formula=['"In Stock"'], stopIfTrue=True,
                            fill=PatternFill(start_color=status_rules["In Stock"]["fill"], end_color=status_rules["In Stock"]["fill"], fill_type="solid"),
                            font=Font(name="Segoe UI", color=status_rules["In Stock"]["font"], bold=True))
    rule_yellow = CellIsRule(operator='equal', formula=['"Low Stock"'], stopIfTrue=True,
                             fill=PatternFill(start_color=status_rules["Low Stock"]["fill"], end_color=status_rules["Low Stock"]["fill"], fill_type="solid"),
                             font=Font(name="Segoe UI", color=status_rules["Low Stock"]["font"], bold=True))
    rule_red = CellIsRule(operator='equal', formula=['"Out of Stock"'], stopIfTrue=True,
                          fill=PatternFill(start_color=status_rules["Out of Stock"]["fill"], end_color=status_rules["Out of Stock"]["fill"], fill_type="solid"),
                          font=Font(name="Segoe UI", color=status_rules["Out of Stock"]["font"], bold=True))
                          
    ws_prod.conditional_formatting.add(f"P7:P{len(dummy_products)+6}", rule_green)
    ws_prod.conditional_formatting.add(f"P7:P{len(dummy_products)+6}", rule_yellow)
    ws_prod.conditional_formatting.add(f"P7:P{len(dummy_products)+6}", rule_red)
    
    # Apply status highlights to other reports where status appears
    ws_rep.conditional_formatting.add("F12:F30", rule_green)
    ws_rep.conditional_formatting.add("F12:F30", rule_yellow)
    ws_rep.conditional_formatting.add("F12:F30", rule_red)
    
    ws_dash.conditional_formatting.add("E23:E30", rule_green)
    ws_dash.conditional_formatting.add("E23:E30", rule_yellow)
    ws_dash.conditional_formatting.add("E23:E30", rule_red)
    
    # Save the workbook
    filename = "Inventory_Management_System.xlsx"
    wb.save(filename)
    print(f"Inventory System successfully created: {filename}")

if __name__ == "__main__":
    create_inventory_system()
