"""Modern Desktop GUI for the Electronics Inventory Management System."""
import sqlite3
import time
import tkinter as tk
from tkinter import messagebox, ttk

import config
from database import fetch_one, init_db, query_all, query_one, transaction
from security import verify_password
from utils import compute_totals, derive_stock_status, fmt_money, line_total, now_str
from validators import (
    ValidationError,
    clean_text,
    parse_int,
    parse_money,
    parse_rate,
    validate_email,
    validate_phone,
    validate_sku,
)

# ---------------- Color Palette & Fonts ----------------
BG_MAIN = "#F1F5F9"
BG_CARD = "#FFFFFF"
BG_SIDEBAR = "#0F172A"
BG_SIDEBAR_HOVER = "#1E293B"
ACCENT = "#2563EB"
ACCENT_HOVER = "#1D4ED8"
SUCCESS = "#16A34A"
WARNING = "#D97706"
DANGER = "#DC2626"
TEXT_DARK = "#0F172A"
TEXT_MUTED = "#64748B"
BORDER = "#CBD5E1"

FONT_FAMILY = "Segoe UI"


def can_do(role: str, section: str, action: str) -> bool:
    allowed = config.PERMISSIONS.get(section, {}).get(action, frozenset())
    return role in allowed


def apply_modern_theme(root: tk.Tk) -> None:
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    root.configure(bg=BG_MAIN)

    style.configure("TFrame", background=BG_MAIN)
    style.configure("Card.TFrame", background=BG_CARD, relief="flat")
    style.configure("TLabel", background=BG_MAIN, foreground=TEXT_DARK, font=(FONT_FAMILY, 10))
    style.configure("Card.TLabel", background=BG_CARD, foreground=TEXT_DARK, font=(FONT_FAMILY, 10))
    style.configure("Muted.TLabel", background=BG_CARD, foreground=TEXT_MUTED, font=(FONT_FAMILY, 9))
    style.configure("Title.TLabel", background=BG_MAIN, foreground=TEXT_DARK, font=(FONT_FAMILY, 16, "bold"))
    style.configure("CardTitle.TLabel", background=BG_CARD, foreground=TEXT_DARK, font=(FONT_FAMILY, 12, "bold"))

    style.configure(
        "Primary.TButton",
        background=ACCENT,
        foreground="#FFFFFF",
        font=(FONT_FAMILY, 10, "bold"),
        borderwidth=0,
        padding=(14, 7),
    )
    style.map("Primary.TButton", background=[("active", ACCENT_HOVER), ("disabled", "#94A3B8")])

    style.configure(
        "Success.TButton",
        background=SUCCESS,
        foreground="#FFFFFF",
        font=(FONT_FAMILY, 10, "bold"),
        borderwidth=0,
        padding=(14, 7),
    )
    style.map("Success.TButton", background=[("active", "#15803D")])

    style.configure(
        "Danger.TButton",
        background=DANGER,
        foreground="#FFFFFF",
        font=(FONT_FAMILY, 10, "bold"),
        borderwidth=0,
        padding=(12, 7),
    )
    style.map("Danger.TButton", background=[("active", "#B91C1C")])

    style.configure(
        "Secondary.TButton",
        background="#E2E8F0",
        foreground=TEXT_DARK,
        font=(FONT_FAMILY, 10),
        borderwidth=0,
        padding=(12, 7),
    )
    style.map("Secondary.TButton", background=[("active", "#CBD5E1")])

    style.configure(
        "TEntry",
        fieldbackground="#FFFFFF",
        foreground=TEXT_DARK,
        bordercolor=BORDER,
        padding=5,
        font=(FONT_FAMILY, 10),
    )
    style.configure(
        "TCombobox",
        fieldbackground="#FFFFFF",
        foreground=TEXT_DARK,
        padding=5,
        font=(FONT_FAMILY, 10),
    )

    style.configure(
        "Treeview",
        background="#FFFFFF",
        foreground=TEXT_DARK,
        fieldbackground="#FFFFFF",
        rowheight=30,
        borderwidth=0,
        font=(FONT_FAMILY, 10),
    )
    style.configure(
        "Treeview.Heading",
        background="#E2E8F0",
        foreground=TEXT_DARK,
        font=(FONT_FAMILY, 10, "bold"),
        relief="flat",
        padding=(8, 6),
    )
    style.map("Treeview", background=[("selected", "#DBEAFE")], foreground=[("selected", TEXT_DARK)])


# ==============================================================================
# LOGIN SCREEN
# ==============================================================================
class LoginView(tk.Frame):
    def __init__(self, parent: tk.Tk, on_login_success):
        super().__init__(parent, bg=BG_SIDEBAR)
        self.parent = parent
        self.on_login_success = on_login_success
        self.failed_attempts = 0
        self.locked_until = 0.0
        self.pack(fill="both", expand=True)

        parent.title(f"{config.APP_NAME} — Sign In")
        parent.geometry("920x580")
        parent.minsize(780, 500)

        card = tk.Frame(self, bg=BG_CARD, padx=40, pady=36, highlightbackground="#334155", highlightthickness=1)
        card.place(relx=0.5, rely=0.5, anchor="center")

        badge = tk.Label(
            card, text="EIMS", bg=ACCENT, fg="#FFFFFF", font=(FONT_FAMILY, 12, "bold"), padx=12, pady=4
        )
        badge.pack(anchor="w")

        tk.Label(
            card,
            text=config.APP_NAME,
            bg=BG_CARD,
            fg=TEXT_DARK,
            font=(FONT_FAMILY, 16, "bold"),
            wraplength=340,
            justify="left",
        ).pack(anchor="w", pady=(10, 4))

        tk.Label(
            card,
            text="Sign in to access inventory, billing & reports",
            bg=BG_CARD,
            fg=TEXT_MUTED,
            font=(FONT_FAMILY, 10),
        ).pack(anchor="w", pady=(0, 20))

        tk.Label(card, text="Username", bg=BG_CARD, fg=TEXT_DARK, font=(FONT_FAMILY, 10, "bold")).pack(anchor="w")
        self.user_var = tk.StringVar(value="admin")
        user_entry = ttk.Entry(card, textvariable=self.user_var, width=36)
        user_entry.pack(fill="x", pady=(4, 12))

        tk.Label(card, text="Password", bg=BG_CARD, fg=TEXT_DARK, font=(FONT_FAMILY, 10, "bold")).pack(anchor="w")
        self.pass_var = tk.StringVar()
        pass_entry = ttk.Entry(card, textvariable=self.pass_var, show="•", width=36)
        pass_entry.pack(fill="x", pady=(4, 6))
        pass_entry.bind("<Return>", lambda _e: self.do_login())

        self.status_lbl = tk.Label(card, text="", bg=BG_CARD, fg=DANGER, font=(FONT_FAMILY, 9))
        self.status_lbl.pack(anchor="w", pady=(2, 10))

        btn_row = tk.Frame(card, bg=BG_CARD)
        btn_row.pack(fill="x", pady=(4, 14))
        ttk.Button(btn_row, text="Sign In", style="Primary.TButton", command=self.do_login).pack(
            side="left", fill="x", expand=True, padx=(0, 6)
        )
        ttk.Button(btn_row, text="Exit", style="Secondary.TButton", command=parent.destroy).pack(
            side="right"
        )

        hint_box = tk.Frame(card, bg="#F8FAFC", padx=12, pady=8, highlightbackground=BORDER, highlightthickness=1)
        hint_box.pack(fill="x")
        tk.Label(
            hint_box,
            text="Default Accounts:\n• Admin: admin / admin123\n• Cashier: cashier / cashier123",
            bg="#F8FAFC",
            fg=TEXT_MUTED,
            font=(FONT_FAMILY, 9),
            justify="left",
        ).pack(anchor="w")

        user_entry.focus_set()

    def do_login(self):
        now = time.time()
        if now < self.locked_until:
            wait = int(self.locked_until - now) + 1
            self.status_lbl.config(text=f"Too many failed attempts. Try again in {wait}s.")
            return

        try:
            username = clean_text(self.user_var.get(), "Username", required=True)
        except ValidationError as exc:
            self.status_lbl.config(text=str(exc))
            return

        password = self.pass_var.get()
        if not password:
            self.status_lbl.config(text="Please enter your password.")
            return

        row = query_one(
            "SELECT id, username, password_hash, role, full_name, active "
            "FROM users WHERE username = ? COLLATE NOCASE",
            (username,),
        )
        if not row or not row["active"] or not verify_password(password, row["password_hash"]):
            self.failed_attempts += 1
            if self.failed_attempts >= config.MAX_FAILED_LOGINS:
                self.locked_until = time.time() + config.LOCKOUT_SECONDS
                self.failed_attempts = 0
                self.status_lbl.config(
                    text=f"Account locked for {config.LOCKOUT_SECONDS}s due to failed logins."
                )
            else:
                rem = config.MAX_FAILED_LOGINS - self.failed_attempts
                self.status_lbl.config(text=f"Invalid credentials ({rem} attempts remaining).")
            return

        try:
            with transaction() as conn:
                conn.execute(
                    "INSERT INTO audit_log (ts, username, role, action, details) VALUES (?,?,?,?,?)",
                    (now_str(), row["username"], row["role"], "LOGIN", "Desktop GUI login"),
                )
        except sqlite3.Error:
            pass

        self.destroy()
        self.on_login_success(row)


# ==============================================================================
# MAIN APPLICATION SHELL (SIDEBAR + DYNAMIC VIEWS)
# ==============================================================================
class MainApplication(tk.Frame):
    def __init__(self, parent: tk.Tk, user: dict, on_logout):
        super().__init__(parent, bg=BG_MAIN)
        self.parent = parent
        self.user = user
        self.role = user["role"]
        self.on_logout = on_logout
        self.nav_buttons = {}
        self.active_nav = None
        self.pack(fill="both", expand=True)

        parent.title(f"{config.APP_NAME} — {user['full_name']} ({self.role})")
        parent.geometry("1240x740")
        parent.minsize(1024, 640)

        self._build_sidebar()
        self._build_workspace()
        self.select_section("Overview")

    def _build_sidebar(self):
        sidebar = tk.Frame(self, bg=BG_SIDEBAR, width=230)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        brand = tk.Frame(sidebar, bg=BG_SIDEBAR, padx=18, pady=22)
        brand.pack(fill="x")
        tk.Label(
            brand, text="INVENTORY PRO", bg=BG_SIDEBAR, fg="#38BDF8", font=(FONT_FAMILY, 13, "bold")
        ).pack(anchor="w")
        tk.Label(
            brand, text="Electronics POS & Stock", bg=BG_SIDEBAR, fg="#94A3B8", font=(FONT_FAMILY, 9)
        ).pack(anchor="w", pady=(2, 0))

        tk.Frame(sidebar, bg="#1E293B", height=1).pack(fill="x", padx=14, pady=(0, 12))

        icons = {
            "Overview": "📊  Overview",
            "Products": "📦  Products",
            "Sales": "🧾  Sales & POS",
            "Customers": "👥  Customers",
            "Suppliers": "🚚  Suppliers",
            "Categories": "🗂️  Categories",
            "Tax Rate": "💹  Tax Rate",
            "Exit": "🚪  Logout / Exit",
        }

        for item in config.NAV_ITEMS:
            sec = config.NAV_SECTIONS.get(item)
            if sec and not can_do(self.role, sec, "view") and not can_do(self.role, sec, "view_active") and not can_do(self.role, sec, "view_own"):
                continue

            btn = tk.Button(
                sidebar,
                text=icons.get(item, item),
                bg=BG_SIDEBAR,
                fg="#E2E8F0",
                activebackground=BG_SIDEBAR_HOVER,
                activeforeground="#FFFFFF",
                font=(FONT_FAMILY, 10, "bold"),
                bd=0,
                anchor="w",
                padx=20,
                pady=11,
                cursor="hand2",
                command=lambda name=item: self.select_section(name),
            )
            btn.pack(fill="x", pady=1)
            self.nav_buttons[item] = btn

        footer = tk.Frame(sidebar, bg="#1E293B", padx=16, pady=14)
        footer.pack(side="bottom", fill="x")
        tk.Label(
            footer, text=self.user["full_name"], bg="#1E293B", fg="#FFFFFF", font=(FONT_FAMILY, 10, "bold")
        ).pack(anchor="w")
        role_color = "#38BDF8" if self.role == config.ADMIN else "#4ADE80"
        tk.Label(
            footer, text=f"Role: {self.role}", bg="#1E293B", fg=role_color, font=(FONT_FAMILY, 9, "bold")
        ).pack(anchor="w", pady=(2, 0))

    def _build_workspace(self):
        right = tk.Frame(self, bg=BG_MAIN)
        right.pack(side="right", fill="both", expand=True)

        topbar = tk.Frame(right, bg=BG_CARD, height=58, highlightbackground=BORDER, highlightthickness=1)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        self.page_title = tk.Label(
            topbar, text="Overview", bg=BG_CARD, fg=TEXT_DARK, font=(FONT_FAMILY, 14, "bold")
        )
        self.page_title.pack(side="left", padx=22)

        self.clock_lbl = tk.Label(
            topbar, text=now_str(), bg=BG_CARD, fg=TEXT_MUTED, font=(FONT_FAMILY, 9)
        )
        self.clock_lbl.pack(side="right", padx=22)

        self.content = tk.Frame(right, bg=BG_MAIN, padx=22, pady=18)
        self.content.pack(fill="both", expand=True)

    def select_section(self, item: str):
        if item == "Exit":
            if messagebox.askyesno("Logout", "Do you want to log out to the Sign In screen?"):
                self.destroy()
                self.on_logout()
            return

        for name, btn in self.nav_buttons.items():
            if name == item:
                btn.config(bg=ACCENT, fg="#FFFFFF")
            else:
                btn.config(bg=BG_SIDEBAR, fg="#CBD5E1")

        self.active_nav = item
        self.page_title.config(text=f"{config.APP_NAME}  /  {item}")
        self.clock_lbl.config(text=f"Updated: {now_str()}")

        for w in self.content.winfo_children():
            w.destroy()

        builders = {
            "Overview": self.render_overview,
            "Products": self.render_products,
            "Sales": self.render_sales,
            "Customers": self.render_customers,
            "Suppliers": self.render_suppliers,
            "Categories": self.render_categories,
            "Tax Rate": self.render_tax,
        }
        builders.get(item, self.render_overview)()

    # --------------------------------------------------------------------------
    # 1. OVERVIEW WINDOW
    # --------------------------------------------------------------------------
    def render_overview(self):
        products = query_all("SELECT stock_qty, stock_status, cost_price, selling_price FROM products")
        low_stock = sum(1 for p in products if p["stock_status"] != "In Stock")
        stock_value = sum(p["stock_qty"] * p["selling_price"] for p in products)

        if can_do(self.role, "sales", "view_all"):
            sales = query_all("SELECT total, created_at FROM sales")
        else:
            sales = query_all("SELECT total, created_at FROM sales WHERE cashier_id = ?", (self.user["id"],))

        total_rev = sum(float(s["total"]) for s in sales)
        today_prefix = now_str()[:10]
        today_rev = sum(float(s["total"]) for s in sales if str(s["created_at"]).startswith(today_prefix))

        cards_row = tk.Frame(self.content, bg=BG_MAIN)
        cards_row.pack(fill="x", pady=(0, 18))

        kpis = [
            ("Total Products", str(len(products)), f"Catalog Value: {fmt_money(stock_value)}", ACCENT),
            ("Low / Out of Stock", str(low_stock), "Items needing restock", WARNING if low_stock else SUCCESS),
            ("Total Invoices", str(len(sales)), f"Today's Sales: {fmt_money(today_rev)}", "#7C3AED"),
            (
                "Total Revenue" if can_do(self.role, "overview", "view_financials") else "My Sales Total",
                fmt_money(total_rev),
                f"Active Currency: {config.CURRENCY}",
                SUCCESS,
            ),
        ]

        for idx, (title, big_val, sub, stripe_color) in enumerate(kpis):
            card = tk.Frame(cards_row, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
            card.grid(row=0, column=idx, padx=(0 if idx == 0 else 8, 0), sticky="nsew")
            cards_row.columnconfigure(idx, weight=1)

            tk.Frame(card, bg=stripe_color, height=4).pack(fill="x")
            body = tk.Frame(card, bg=BG_CARD, padx=16, pady=14)
            body.pack(fill="both", expand=True)
            tk.Label(body, text=title, bg=BG_CARD, fg=TEXT_MUTED, font=(FONT_FAMILY, 10)).pack(anchor="w")
            tk.Label(body, text=big_val, bg=BG_CARD, fg=TEXT_DARK, font=(FONT_FAMILY, 18, "bold")).pack(
                anchor="w", pady=(4, 2)
            )
            tk.Label(body, text=sub, bg=BG_CARD, fg=stripe_color, font=(FONT_FAMILY, 9, "bold")).pack(anchor="w")

        split = tk.Frame(self.content, bg=BG_MAIN)
        split.pack(fill="both", expand=True)

        left_card = tk.Frame(split, bg=BG_CARD, padx=14, pady=14, highlightbackground=BORDER, highlightthickness=1)
        left_card.pack(side="left", fill="both", expand=True, padx=(0, 8))
        tk.Label(left_card, text="Low & Out of Stock Alerts", bg=BG_CARD, fg=TEXT_DARK, font=(FONT_FAMILY, 11, "bold")).pack(
            anchor="w", pady=(0, 8)
        )

        low_tree = ttk.Treeview(left_card, columns=("sku", "name", "qty", "status"), show="headings", height=12)
        for c, h, w in [("sku", "SKU", 110), ("name", "Product", 180), ("qty", "Qty", 60), ("status", "Status", 100)]:
            low_tree.heading(c, text=h)
            low_tree.column(c, width=w, anchor="w")
        low_tree.pack(fill="both", expand=True)

        for r in query_all(
            "SELECT sku, name, stock_qty, stock_status FROM products WHERE stock_status != 'In Stock' ORDER BY id ASC"
        ):
            low_tree.insert("", "end", values=(r["sku"], r["name"], r["stock_qty"], r["stock_status"]))

        right_card = tk.Frame(split, bg=BG_CARD, padx=14, pady=14, highlightbackground=BORDER, highlightthickness=1)
        right_card.pack(side="right", fill="both", expand=True, padx=(8, 0))
        tk.Label(right_card, text="System Audit Log", bg=BG_CARD, fg=TEXT_DARK, font=(FONT_FAMILY, 11, "bold")).pack(
            anchor="w", pady=(0, 8)
        )

        if can_do(self.role, "overview", "view_activity_log"):
            log_tree = ttk.Treeview(right_card, columns=("ts", "user", "action", "details"), show="headings", height=12)
            for c, h, w in [("ts", "Time", 130), ("user", "User", 85), ("action", "Action", 105), ("details", "Details", 210)]:
                log_tree.heading(c, text=h)
                log_tree.column(c, width=w, anchor="w")
            log_tree.pack(fill="both", expand=True)

            for r in query_all("SELECT ts, username, action, details FROM audit_log ORDER BY id DESC LIMIT 60"):
                log_tree.insert("", "end", values=(r["ts"], r["username"], r["action"], r["details"]))
        else:
            tk.Label(
                right_card,
                text="Audit logs are visible to Admin accounts only.",
                bg=BG_CARD,
                fg=TEXT_MUTED,
                font=(FONT_FAMILY, 10),
            ).pack(anchor="w", pady=20)

    # --------------------------------------------------------------------------
    # 2. PRODUCTS WINDOW
    # --------------------------------------------------------------------------
    def render_products(self):
        toolbar = tk.Frame(self.content, bg=BG_CARD, padx=14, pady=10, highlightbackground=BORDER, highlightthickness=1)
        toolbar.pack(fill="x", pady=(0, 12))

        tk.Label(toolbar, text="Search:", bg=BG_CARD, fg=TEXT_DARK, font=(FONT_FAMILY, 10, "bold")).pack(side="left")
        search_var = tk.StringVar()
        ttk.Entry(toolbar, textvariable=search_var, width=30).pack(side="left", padx=8)

        if can_do(self.role, "products", "add"):
            ttk.Button(
                toolbar, text="+ Add Product", style="Primary.TButton", command=lambda: self.open_product_dialog()
            ).pack(side="right", padx=(6, 0))

        if can_do(self.role, "products", "edit"):
            ttk.Button(
                toolbar, text="Edit Selected", style="Secondary.TButton", command=lambda: edit_selected()
            ).pack(side="right", padx=6)

        if can_do(self.role, "products", "delete"):
            ttk.Button(
                toolbar, text="Delete", style="Danger.TButton", command=lambda: delete_selected()
            ).pack(side="right", padx=6)

        table_card = tk.Frame(self.content, bg=BG_CARD, padx=12, pady=12, highlightbackground=BORDER, highlightthickness=1)
        table_card.pack(fill="both", expand=True)

        show_cost = can_do(self.role, "products", "view_cost")
        cols = ("id", "sku", "name", "brand", "category", "cost", "price", "qty", "status") if show_cost else (
            "id", "sku", "name", "brand", "category", "price", "qty", "status"
        )
        tree = ttk.Treeview(table_card, columns=cols, show="headings")
        col_defs = [
            ("id", "ID", 45),
            ("sku", "SKU", 115),
            ("name", "Product Name", 230),
            ("brand", "Brand", 110),
            ("category", "Category", 150),
            ("cost", "Cost", 95),
            ("price", "Price", 95),
            ("qty", "Stock", 70),
            ("status", "Status", 105),
        ]
        for c, h, w in col_defs:
            if c in cols:
                tree.heading(c, text=h)
                tree.column(c, width=w, anchor="w")
        tree.pack(fill="both", expand=True)

        def load_rows(*_args):
            term = search_var.get().strip().lower()
            tree.delete(*tree.get_children())
            rows = query_all(
                """SELECT p.*, c.name AS category_name
                   FROM products p JOIN categories c ON c.id = p.category_id
                   ORDER BY p.id ASC"""
            )
            for p in rows:
                if term and term not in p["sku"].lower() and term not in p["name"].lower() and term not in p["brand"].lower():
                    continue
                vals = [p["id"], p["sku"], p["name"], p["brand"], p["category_name"]]
                if show_cost:
                    vals.append(fmt_money(p["cost_price"]))
                vals.extend([fmt_money(p["selling_price"]), p["stock_qty"], p["stock_status"]])
                tree.insert("", "end", values=vals)

        def edit_selected():
            sel = tree.selection()
            if not sel:
                messagebox.showinfo("Products", "Please select a product row first.")
                return
            prod_id = tree.item(sel[0])["values"][0]
            self.open_product_dialog(prod_id)

        def delete_selected():
            sel = tree.selection()
            if not sel:
                messagebox.showinfo("Products", "Please select a product row first.")
                return
            prod_id, sku = tree.item(sel[0])["values"][0], tree.item(sel[0])["values"][1]
            if not messagebox.askyesno("Confirm Delete", f"Delete product {sku}?"):
                return
            try:
                with transaction() as conn:
                    conn.execute("DELETE FROM products WHERE id = ?", (prod_id,))
                    conn.execute(
                        "INSERT INTO audit_log (ts, username, role, action, details) VALUES (?,?,?,?,?)",
                        (now_str(), self.user["username"], self.role, "DELETE_PRODUCT", f"Deleted {sku}"),
                    )
                load_rows()
            except sqlite3.Error as exc:
                messagebox.showerror("Error", str(exc))

        search_var.trace_add("write", load_rows)
        load_rows()

    def open_product_dialog(self, product_id=None):
        existing = query_one("SELECT * FROM products WHERE id = ?", (product_id,)) if product_id else None
        categories = query_all("SELECT id, name FROM categories ORDER BY id ASC")
        suppliers = query_all("SELECT id, name FROM suppliers ORDER BY id ASC")
        if not categories:
            messagebox.showwarning("Categories Required", "Please add a category first.")
            return

        win = tk.Toplevel(self)
        win.title("Edit Product" if existing else "Add New Product")
        win.configure(bg=BG_CARD)
        win.resizable(False, False)
        win.transient(self.winfo_toplevel())
        win.grab_set()

        form = tk.Frame(win, bg=BG_CARD, padx=24, pady=20)
        form.pack(fill="both", expand=True)

        cat_map = {c["name"]: c["id"] for c in categories}
        sup_map = {"(None)": None, **{s["name"]: s["id"] for s in suppliers}}

        cur_cat = next((c["name"] for c in categories if existing and c["id"] == existing["category_id"]), categories[0]["name"])
        cur_sup = next((s["name"] for s in suppliers if existing and s["id"] == existing["supplier_id"]), "(None)")

        vars_map = {
            "sku": tk.StringVar(value=existing["sku"] if existing else ""),
            "name": tk.StringVar(value=existing["name"] if existing else ""),
            "brand": tk.StringVar(value=existing["brand"] if existing else ""),
            "model": tk.StringVar(value=existing["model"] if existing else ""),
            "category": tk.StringVar(value=cur_cat),
            "supplier": tk.StringVar(value=cur_sup),
            "warranty": tk.StringVar(value=str(existing["warranty_months"]) if existing else "12"),
            "cost": tk.StringVar(value=f"{existing['cost_price']:.2f}" if existing else "0.00"),
            "price": tk.StringVar(value=f"{existing['selling_price']:.2f}" if existing else "0.00"),
            "qty": tk.StringVar(value=str(existing["stock_qty"]) if existing else "10"),
            "reorder": tk.StringVar(value=str(existing["reorder_level"]) if existing else "5"),
        }

        layout = [
            ("SKU *", "sku", "entry"),
            ("Product Name *", "name", "entry"),
            ("Brand", "brand", "entry"),
            ("Model", "model", "entry"),
            ("Category *", "category", list(cat_map.keys())),
            ("Supplier", "supplier", list(sup_map.keys())),
            ("Warranty (Months)", "warranty", "entry"),
            ("Cost Price *", "cost", "entry"),
            ("Selling Price *", "price", "entry"),
            ("Stock Qty *", "qty", "entry"),
            ("Reorder Level *", "reorder", "entry"),
        ]

        for idx, (label, key, kind) in enumerate(layout):
            r, c = divmod(idx, 2)
            tk.Label(form, text=label, bg=BG_CARD, fg=TEXT_DARK, font=(FONT_FAMILY, 9, "bold")).grid(
                row=r * 2, column=c, sticky="w", padx=8, pady=(6, 2)
            )
            if kind == "entry":
                ttk.Entry(form, textvariable=vars_map[key], width=28).grid(row=r * 2 + 1, column=c, padx=8, pady=(0, 4))
            else:
                ttk.Combobox(form, textvariable=vars_map[key], values=kind, width=26, state="readonly").grid(
                    row=r * 2 + 1, column=c, padx=8, pady=(0, 4)
                )

        def save():
            try:
                sku = validate_sku(vars_map["sku"].get())
                name = clean_text(vars_map["name"].get(), "Product Name", required=True)
                brand = clean_text(vars_map["brand"].get(), "Brand", max_len=80)
                model = clean_text(vars_map["model"].get(), "Model", max_len=80)
                cat_id = cat_map[vars_map["category"].get()]
                sup_id = sup_map[vars_map["supplier"].get()]
                warranty = parse_int(vars_map["warranty"].get(), "Warranty Months", minimum=0, maximum=120)
                cost = parse_money(vars_map["cost"].get(), "Cost Price")
                price = parse_money(vars_map["price"].get(), "Selling Price")
                qty = parse_int(vars_map["qty"].get(), "Stock Qty", minimum=0)
                reorder = parse_int(vars_map["reorder"].get(), "Reorder Level", minimum=0)
                status = derive_stock_status(qty, reorder)
                ts = now_str()

                with transaction() as conn:
                    if existing:
                        conn.execute(
                            """UPDATE products SET sku=?, name=?, brand=?, model=?, category_id=?, supplier_id=?,
                               warranty_months=?, cost_price=?, selling_price=?, stock_qty=?, reorder_level=?,
                               stock_status=?, updated_at=? WHERE id=?""",
                            (sku, name, brand, model, cat_id, sup_id, warranty, cost, price, qty, reorder, status, ts, product_id),
                        )
                        action, detail = "EDIT_PRODUCT", f"Updated {sku}"
                    else:
                        conn.execute(
                            """INSERT INTO products (sku, barcode, name, brand, model, category_id, supplier_id,
                               serial_number, warranty_months, cost_price, selling_price, stock_qty, reorder_level,
                               stock_status, created_at, updated_at)
                               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (sku, "", name, brand, model, cat_id, sup_id, "", warranty, cost, price, qty, reorder, status, ts, ts),
                        )
                        action, detail = "ADD_PRODUCT", f"Added {sku}"

                    conn.execute(
                        "INSERT INTO audit_log (ts, username, role, action, details) VALUES (?,?,?,?,?)",
                        (ts, self.user["username"], self.role, action, detail),
                    )
                win.destroy()
                self.select_section("Products")
            except (ValidationError, sqlite3.Error) as exc:
                messagebox.showerror("Validation Error", str(exc), parent=win)

        btns = tk.Frame(form, bg=BG_CARD)
        btns.grid(row=14, column=0, columnspan=2, pady=(16, 0), sticky="e")
        ttk.Button(btns, text="Cancel", style="Secondary.TButton", command=win.destroy).pack(side="left", padx=6)
        ttk.Button(btns, text="Save Product", style="Primary.TButton", command=save).pack(side="left")

    # --------------------------------------------------------------------------
    # 3. SALES & POS WINDOW
    # --------------------------------------------------------------------------
    def render_sales(self):
        split = tk.Frame(self.content, bg=BG_MAIN)
        split.pack(fill="both", expand=True)

        if can_do(self.role, "sales", "create"):
            pos_card = tk.Frame(split, bg=BG_CARD, padx=16, pady=14, highlightbackground=BORDER, highlightthickness=1, width=440)
            pos_card.pack(side="left", fill="y", padx=(0, 10))
            pos_card.pack_propagate(False)

            tk.Label(pos_card, text="New Point-of-Sale Invoice", bg=BG_CARD, fg=TEXT_DARK, font=(FONT_FAMILY, 12, "bold")).pack(
                anchor="w", pady=(0, 10)
            )

            customers = query_all("SELECT id, name FROM customers ORDER BY id ASC")
            cust_map = {"Walk-in Customer": None, **{c["name"]: c["id"] for c in customers}}
            cust_var = tk.StringVar(value="Walk-in Customer")

            tk.Label(pos_card, text="Customer:", bg=BG_CARD, fg=TEXT_DARK, font=(FONT_FAMILY, 9, "bold")).pack(anchor="w")
            ttk.Combobox(pos_card, textvariable=cust_var, values=list(cust_map.keys()), state="readonly").pack(
                fill="x", pady=(2, 8)
            )

            products = query_all("SELECT * FROM products WHERE stock_qty > 0 ORDER BY id ASC")
            prod_choices = [f"{p['sku']} | {p['name']} ({fmt_money(p['selling_price'])}, Stock: {p['stock_qty']})" for p in products]
            prod_var = tk.StringVar(value=prod_choices[0] if prod_choices else "")
            qty_var = tk.StringVar(value="1")

            tk.Label(pos_card, text="Select Product:", bg=BG_CARD, fg=TEXT_DARK, font=(FONT_FAMILY, 9, "bold")).pack(anchor="w")
            ttk.Combobox(pos_card, textvariable=prod_var, values=prod_choices, state="readonly").pack(fill="x", pady=(2, 8))

            row_add = tk.Frame(pos_card, bg=BG_CARD)
            row_add.pack(fill="x", pady=(0, 10))
            tk.Label(row_add, text="Qty:", bg=BG_CARD, fg=TEXT_DARK, font=(FONT_FAMILY, 9, "bold")).pack(side="left")
            ttk.Entry(row_add, textvariable=qty_var, width=8).pack(side="left", padx=6)

            cart = []
            cart_tree = ttk.Treeview(pos_card, columns=("sku", "qty", "price", "total"), show="headings", height=7)
            for c, h, w in [("sku", "SKU", 110), ("qty", "Qty", 50), ("price", "Unit", 85), ("total", "Line", 95)]:
                cart_tree.heading(c, text=h)
                cart_tree.column(c, width=w, anchor="w")
            cart_tree.pack(fill="both", expand=True, pady=(0, 8))

            tax_row = query_one("SELECT rate_percent FROM tax_rates WHERE is_active = 1 ORDER BY id DESC LIMIT 1")
            active_rate = tax_row["rate_percent"] if tax_row else 0.0

            summary_lbl = tk.Label(
                pos_card,
                text=f"Subtotal: {fmt_money(0)}  |  Tax ({active_rate:.1f}%): {fmt_money(0)}\nGrand Total: {fmt_money(0)}",
                bg="#F8FAFC",
                fg=TEXT_DARK,
                font=(FONT_FAMILY, 10, "bold"),
                justify="left",
                padx=10,
                pady=8,
            )
            summary_lbl.pack(fill="x", pady=(0, 8))

            pay_row = tk.Frame(pos_card, bg=BG_CARD)
            pay_row.pack(fill="x", pady=(0, 10))
            pay_var = tk.StringVar(value=config.PAYMENT_METHODS[0])
            tender_var = tk.StringVar(value="0.00")
            ttk.Combobox(pay_row, textvariable=pay_var, values=config.PAYMENT_METHODS, width=15, state="readonly").pack(
                side="left", padx=(0, 8)
            )
            tk.Label(pay_row, text="Tendered:", bg=BG_CARD, fg=TEXT_DARK, font=(FONT_FAMILY, 9)).pack(side="left")
            ttk.Entry(pay_row, textvariable=tender_var, width=12).pack(side="left", padx=6)

            def refresh_cart():
                cart_tree.delete(*cart_tree.get_children())
                for item in cart:
                    cart_tree.insert(
                        "", "end", values=(item["sku"], item["qty"], fmt_money(item["price"]), fmt_money(item["line"]))
                    )
                sub, tax, tot = compute_totals([i["line"] for i in cart], active_rate)
                summary_lbl.config(
                    text=f"Subtotal: {fmt_money(sub)}  |  Tax ({active_rate:.1f}%): {fmt_money(tax)}\nGrand Total: {fmt_money(tot)}"
                )
                tender_var.set(f"{tot:.2f}")

            def add_to_cart():
                try:
                    sel = prod_var.get()
                    if " | " not in sel:
                        raise ValidationError("Select a product.")
                    sku = sel.split(" | ", 1)[0].strip()
                    q = parse_int(qty_var.get(), "Quantity", minimum=1, maximum=1000)
                    p = query_one(
                        "SELECT p.*, c.name AS category_name FROM products p JOIN categories c ON c.id = p.category_id WHERE p.sku = ?",
                        (sku,),
                    )
                    if not p:
                        raise ValidationError("Product not found.")
                    existing_qty = sum(i["qty"] for i in cart if i["sku"] == sku)
                    if existing_qty + q > p["stock_qty"]:
                        raise ValidationError(f"Only {p['stock_qty']} in stock.")
                    for item in cart:
                        if item["sku"] == sku:
                            item["qty"] += q
                            item["line"] = line_total(item["price"], item["qty"])
                            break
                    else:
                        cart.append({
                            "id": p["id"],
                            "sku": p["sku"],
                            "name": p["name"],
                            "category": p["category_name"],
                            "warranty": p["warranty_months"],
                            "price": p["selling_price"],
                            "qty": q,
                            "line": line_total(p["selling_price"], q),
                        })
                    qty_var.set("1")
                    refresh_cart()
                except ValidationError as exc:
                    messagebox.showwarning("Cart", str(exc))

            def complete_sale():
                if not cart:
                    messagebox.showwarning("POS", "Cart is empty.")
                    return
                try:
                    sub, tax, tot = compute_totals([i["line"] for i in cart], active_rate)
                    tendered = parse_money(tender_var.get(), "Amount Tendered")
                    if tendered < tot:
                        raise ValidationError("Amount tendered cannot be less than total.")
                    change = round(tendered - tot, 2)
                    ts = now_str()
                    cust_name = cust_var.get()
                    cust_id = cust_map.get(cust_name)

                    with transaction() as conn:
                        cur = conn.execute(
                            """INSERT INTO sales (invoice_no, customer_id, customer_name, cashier_id, cashier_name,
                               subtotal, tax_rate, tax_amount, total, payment_method, amount_tendered, change_due, created_at)
                               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (
                                f"TMP-{ts}", cust_id, cust_name, self.user["id"], self.user["full_name"],
                                sub, active_rate, tax, tot, pay_var.get(), tendered, change, ts,
                            ),
                        )
                        sale_id = cur.lastrowid
                        inv = f"INV-{ts[:10].replace('-', '')}-{sale_id:05d}"
                        conn.execute("UPDATE sales SET invoice_no = ? WHERE id = ?", (inv, sale_id))

                        for item in cart:
                            p_now = fetch_one(conn, "SELECT stock_qty, reorder_level FROM products WHERE id = ?", (item["id"],))
                            if not p_now or p_now["stock_qty"] < item["qty"]:
                                raise ValidationError(f"Insufficient stock for {item['sku']}.")
                            new_q = p_now["stock_qty"] - item["qty"]
                            conn.execute(
                                "UPDATE products SET stock_qty = ?, stock_status = ?, updated_at = ? WHERE id = ?",
                                (new_q, derive_stock_status(new_q, p_now["reorder_level"]), ts, item["id"]),
                            )
                            conn.execute(
                                """INSERT INTO sale_items (sale_id, product_id, sku, product_name, category_name,
                                   warranty_months, quantity, unit_price, line_total)
                                   VALUES (?,?,?,?,?,?,?,?,?)""",
                                (
                                    sale_id, item["id"], item["sku"], item["name"], item["category"],
                                    item["warranty"], item["qty"], item["price"], item["line"],
                                ),
                            )

                        conn.execute(
                            "INSERT INTO audit_log (ts, username, role, action, details) VALUES (?,?,?,?,?)",
                            (ts, self.user["username"], self.role, "SALE", f"{inv} Total {fmt_money(tot)}"),
                        )

                    messagebox.showinfo(
                        "Sale Complete", f"Invoice: {inv}\nTotal: {fmt_money(tot)}\nChange Due: {fmt_money(change)}"
                    )
                    self.select_section("Sales")
                except (ValidationError, sqlite3.Error) as exc:
                    messagebox.showerror("Checkout Error", str(exc))

            ttk.Button(row_add, text="+ Add Item", style="Primary.TButton", command=add_to_cart).pack(side="left", padx=4)
            ttk.Button(row_add, text="Clear", style="Secondary.TButton", command=lambda: (cart.clear(), refresh_cart())).pack(
                side="right"
            )
            ttk.Button(pos_card, text="Complete Checkout", style="Success.TButton", command=complete_sale).pack(fill="x")

        hist_card = tk.Frame(split, bg=BG_CARD, padx=14, pady=14, highlightbackground=BORDER, highlightthickness=1)
        hist_card.pack(side="right", fill="both", expand=True)
        tk.Label(hist_card, text="Sales Invoices", bg=BG_CARD, fg=TEXT_DARK, font=(FONT_FAMILY, 12, "bold")).pack(
            anchor="w", pady=(0, 10)
        )

        s_tree = ttk.Treeview(
            hist_card, columns=("inv", "cust", "cashier", "total", "pay", "date"), show="headings"
        )
        for c, h, w in [
            ("inv", "Invoice #", 145),
            ("cust", "Customer", 145),
            ("cashier", "Cashier", 130),
            ("total", "Total", 95),
            ("pay", "Payment", 110),
            ("date", "Date & Time", 140),
        ]:
            s_tree.heading(c, text=h)
            s_tree.column(c, width=w, anchor="w")
        s_tree.pack(fill="both", expand=True)

        rows = (
            query_all("SELECT * FROM sales ORDER BY id DESC")
            if can_do(self.role, "sales", "view_all")
            else query_all("SELECT * FROM sales WHERE cashier_id = ? ORDER BY id DESC", (self.user["id"],))
        )
        for s in rows:
            s_tree.insert(
                "",
                "end",
                values=(s["invoice_no"], s["customer_name"], s["cashier_name"], fmt_money(s["total"]), s["payment_method"], s["created_at"]),
            )

    # --------------------------------------------------------------------------
    # 4. CUSTOMERS WINDOW
    # --------------------------------------------------------------------------
    def render_customers(self):
        self._render_entity_crud(
            table="customers",
            section="customers",
            title="Registered Customers",
            columns=[("id", "ID", 50), ("name", "Full Name", 200), ("phone", "Phone", 150), ("email", "Email", 220), ("address", "Address", 260)],
            fields=[("name", "Full Name *", True), ("phone", "Phone", False), ("email", "Email", False), ("address", "Address", False)],
            include_ts=True,
        )

    # --------------------------------------------------------------------------
    # 5. SUPPLIERS WINDOW
    # --------------------------------------------------------------------------
    def render_suppliers(self):
        self._render_entity_crud(
            table="suppliers",
            section="suppliers",
            title="Product Suppliers",
            columns=[("id", "ID", 50), ("name", "Company Name", 210), ("contact_person", "Contact Person", 160), ("phone", "Phone", 140), ("email", "Email", 200)],
            fields=[("name", "Company Name *", True), ("contact_person", "Contact Person", False), ("phone", "Phone", False), ("email", "Email", False), ("address", "Address", False)],
            include_ts=False,
        )

    # --------------------------------------------------------------------------
    # 6. CATEGORIES WINDOW
    # --------------------------------------------------------------------------
    def render_categories(self):
        self._render_entity_crud(
            table="categories",
            section="categories",
            title="Product Categories",
            columns=[("id", "ID", 60), ("name", "Category Name", 240), ("description", "Description", 480)],
            fields=[("name", "Category Name *", True), ("description", "Description", False)],
            include_ts=False,
        )

    def _render_entity_crud(self, table: str, section: str, title: str, columns: list, fields: list, include_ts: bool):
        card = tk.Frame(self.content, bg=BG_CARD, padx=16, pady=14, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True)

        header = tk.Frame(card, bg=BG_CARD)
        header.pack(fill="x", pady=(0, 12))
        tk.Label(header, text=title, bg=BG_CARD, fg=TEXT_DARK, font=(FONT_FAMILY, 12, "bold")).pack(side="left")

        tree = ttk.Treeview(card, columns=[c[0] for c in columns], show="headings")
        for c, h, w in columns:
            tree.heading(c, text=h)
            tree.column(c, width=w, anchor="w")

        def open_dialog(rec_id=None):
            existing = query_one(f"SELECT * FROM {table} WHERE id = ?", (rec_id,)) if rec_id else None
            win = tk.Toplevel(self)
            win.title("Edit Record" if existing else "Add Record")
            win.configure(bg=BG_CARD)
            win.resizable(False, False)
            win.transient(self.winfo_toplevel())
            win.grab_set()

            box = tk.Frame(win, bg=BG_CARD, padx=24, pady=20)
            box.pack(fill="both", expand=True)
            vmap = {}
            for col, lbl, _req in fields:
                tk.Label(box, text=lbl, bg=BG_CARD, fg=TEXT_DARK, font=(FONT_FAMILY, 9, "bold")).pack(anchor="w", pady=(6, 2))
                v = tk.StringVar(value=existing[col] if existing and existing[col] else "")
                ttk.Entry(box, textvariable=v, width=38).pack(fill="x")
                vmap[col] = v

            def save():
                try:
                    data = {}
                    for col, lbl, req in fields:
                        val = vmap[col].get()
                        if col == "email":
                            data[col] = validate_email(val)
                        elif col == "phone":
                            data[col] = validate_phone(val)
                        else:
                            data[col] = clean_text(val, lbl.replace("*", "").strip(), required=req, max_len=200)

                    with transaction() as conn:
                        if existing:
                            sets = ", ".join(f"{k}=?" for k in data)
                            conn.execute(f"UPDATE {table} SET {sets} WHERE id=?", (*data.values(), rec_id))
                        else:
                            if include_ts:
                                data["created_at"] = now_str()
                            cols_sql = ", ".join(data.keys())
                            q_sql = ", ".join("?" for _ in data)
                            conn.execute(f"INSERT INTO {table} ({cols_sql}) VALUES ({q_sql})", tuple(data.values()))
                    win.destroy()
                    self.select_section(self.active_nav)
                except (ValidationError, sqlite3.Error) as exc:
                    messagebox.showerror("Error", str(exc), parent=win)

            btns = tk.Frame(box, bg=BG_CARD)
            btns.pack(fill="x", pady=(16, 0))
            ttk.Button(btns, text="Save", style="Primary.TButton", command=save).pack(side="right")
            ttk.Button(btns, text="Cancel", style="Secondary.TButton", command=win.destroy).pack(side="right", padx=6)

        def delete_rec():
            sel = tree.selection()
            if not sel:
                messagebox.showinfo(title, "Please select a row first.")
                return
            rid = tree.item(sel[0])["values"][0]
            if not messagebox.askyesno("Confirm", "Delete selected record?"):
                return
            try:
                with transaction() as conn:
                    conn.execute(f"DELETE FROM {table} WHERE id = ?", (rid,))
                self.select_section(self.active_nav)
            except sqlite3.Error as exc:
                messagebox.showerror("Error", str(exc))

        if can_do(self.role, section, "add"):
            ttk.Button(header, text="+ Add New", style="Primary.TButton", command=lambda: open_dialog()).pack(side="right")
        if can_do(self.role, section, "edit"):
            ttk.Button(
                header,
                text="Edit",
                style="Secondary.TButton",
                command=lambda: open_dialog(tree.item(tree.selection()[0])["values"][0]) if tree.selection() else None,
            ).pack(side="right", padx=6)
        if can_do(self.role, section, "delete"):
            ttk.Button(header, text="Delete", style="Danger.TButton", command=delete_rec).pack(side="right", padx=6)

        tree.pack(fill="both", expand=True)
        for r in query_all(f"SELECT * FROM {table} ORDER BY id ASC"):
            tree.insert("", "end", values=[r[c[0]] for c in columns])

    # --------------------------------------------------------------------------
    # 7. TAX RATE WINDOW
    # --------------------------------------------------------------------------
    def render_tax(self):
        card = tk.Frame(self.content, bg=BG_CARD, padx=16, pady=14, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True)

        if can_do(self.role, "tax_rate", "manage"):
            bar = tk.Frame(card, bg=BG_CARD)
            bar.pack(fill="x", pady=(0, 12))
            name_v = tk.StringVar()
            rate_v = tk.StringVar()
            tk.Label(bar, text="Tax Name:", bg=BG_CARD, fg=TEXT_DARK, font=(FONT_FAMILY, 9, "bold")).pack(side="left")
            ttk.Entry(bar, textvariable=name_v, width=26).pack(side="left", padx=6)
            tk.Label(bar, text="Rate (%):", bg=BG_CARD, fg=TEXT_DARK, font=(FONT_FAMILY, 9, "bold")).pack(side="left")
            ttk.Entry(bar, textvariable=rate_v, width=10).pack(side="left", padx=6)

            def add_tax():
                try:
                    n = clean_text(name_v.get(), "Tax Name", required=True, max_len=80)
                    r = parse_rate(rate_v.get(), "Tax Rate")
                    ts = now_str()
                    with transaction() as conn:
                        conn.execute("UPDATE tax_rates SET is_active = 0")
                        conn.execute(
                            "INSERT INTO tax_rates (name, rate_percent, is_active, created_at, created_by) VALUES (?,?,?,?,?)",
                            (n, r, 1, ts, self.user["username"]),
                        )
                    self.select_section("Tax Rate")
                except (ValidationError, sqlite3.Error) as exc:
                    messagebox.showerror("Error", str(exc))

            ttk.Button(bar, text="Add & Set Active", style="Primary.TButton", command=add_tax).pack(side="left", padx=8)

        tree = ttk.Treeview(card, columns=("id", "name", "rate", "active", "by", "date"), show="headings")
        for c, h, w in [
            ("id", "ID", 50),
            ("name", "Tax Name", 220),
            ("rate", "Rate (%)", 100),
            ("active", "Status", 110),
            ("by", "Created By", 130),
            ("date", "Created At", 160),
        ]:
            tree.heading(c, text=h)
            tree.column(c, width=w, anchor="w")
        tree.pack(fill="both", expand=True)

        sql = (
            "SELECT * FROM tax_rates ORDER BY id ASC"
            if can_do(self.role, "tax_rate", "view_all")
            else "SELECT * FROM tax_rates WHERE is_active = 1 ORDER BY id ASC"
        )
        for t in query_all(sql):
            tree.insert(
                "",
                "end",
                values=(
                    t["id"],
                    t["name"],
                    f"{t['rate_percent']:.2f}%",
                    "ACTIVE" if t["is_active"] else "Inactive",
                    t["created_by"],
                    t["created_at"],
                ),
            )


def launch():
    init_db(seed=True)
    root = tk.Tk()
    apply_modern_theme(root)

    def show_login():
        LoginView(root, on_login_success=lambda user: MainApplication(root, user, on_logout=show_login))

    show_login()
    root.mainloop()


if __name__ == "__main__":
    launch()