/**
 * INTRINSIC - Subscription & Invoicing Platform
 * Reactive UI Controller with Alpine.js
 * Strictly enforces zero emojis, full-screen initial authentication,
 * fluid screen scaling, dark/bright mode toggle, and human-friendly error messages.
 */

document.addEventListener("alpine:init", () => {
    Alpine.data("intrinsicApp", () => ({
        // App Identity
        appName: "INTRINSIC",
        
        // Initial Authentication & Session State
        initialLoading: true,
        isAuthenticated: false,
        currentUser: null,

        // Theme Switcher State ('dark' or 'light')
        theme: "dark",

        // Mobile Navigation State
        mobileMenuOpen: false,

        // Active Dashboard View
        activeTab: "dashboard",
        loading: false,

        // Auth Form State
        authMode: "login", // 'login' or 'register'
        authForm: {
            name: "",
            email: "",
            password: "",
            role: "customer"
        },
        authError: "",
        authSuccess: "",

        // Data Collections
        metrics: {
            mrr: 0,
            active_subscriptions_count: 0,
            overdue_invoices_count: 0,
            overdue_invoices_amount: 0,
            total_revenue: 0,
            total_customers_count: 0,
            recent_revenue_logs: []
        },
        subscriptions: [],
        subStatusFilter: "",
        invoices: [],
        invStatusFilter: "",
        plans: [],
        products: [],
        discounts: [],

        // Modals & Action Forms
        subModalOpen: false,
        subForm: {
            plan_id: "",
            quantity: 1,
            discount_code: "",
            status: "Draft"
        },
        discountPreview: null,

        payModalOpen: false,
        selectedInvoice: null,
        payForm: {
            method: "credit_card",
            amount: 0,
            notes: ""
        },

        planModalOpen: false,
        planForm: {
            name: "",
            frequency: "monthly",
            min_quantity: 1,
            price: 0,
            status_rules: ""
        },

        productModalOpen: false,
        productForm: {
            name: "",
            type: "service",
            sales_price: 0,
            cost_price: 0,
            variant_attribute: "",
            price_modifier: 0
        },

        discountModalOpen: false,
        discountForm: {
            code: "",
            type: "percentage",
            value: 10,
            min_purchase: 0,
            usage_limit: 100,
            expiry_date: ""
        },

        // Notification Toasts (Strictly Zero Emojis)
        toasts: [],

        // Initialization
        async init() {
            // 1. Initialize Theme from localStorage or Default to Dark
            const savedTheme = localStorage.getItem("intrinsic_theme") || "dark";
            this.setTheme(savedTheme);

            // 2. Mandatory Landing Flow: Verify existing session token
            const token = API.getToken();
            if (token) {
                try {
                    const user = await API.getMe();
                    this.currentUser = user;
                    this.isAuthenticated = true;
                    await this.refreshAllData();
                } catch (err) {
                    API.setToken(null);
                    this.currentUser = null;
                    this.isAuthenticated = false;
                }
            } else {
                this.currentUser = null;
                this.isAuthenticated = false;
            }

            this.initialLoading = false;
        },

        // ----------------- Theme Switcher -----------------
        setTheme(themeName) {
            this.theme = themeName === "light" ? "light" : "dark";
            localStorage.setItem("intrinsic_theme", this.theme);
            if (this.theme === "dark") {
                document.documentElement.classList.add("dark");
            } else {
                document.documentElement.classList.remove("dark");
            }
        },

        toggleTheme() {
            const nextTheme = this.theme === "dark" ? "light" : "dark";
            this.setTheme(nextTheme);
            this.notify("info", "Theme Updated", `Switched to ${nextTheme.toUpperCase()} mode.`);
        },

        // ----------------- Authentication & Landing Flow -----------------
        async handleAuthSubmit() {
            this.authError = "";
            this.authSuccess = "";

            // User-friendly client validation
            if (!this.authForm.email || !this.authForm.email.includes("@")) {
                this.authError = "Please provide a valid corporate or personal email address.";
                return;
            }

            if (!this.authForm.password || this.authForm.password.length < 6) {
                this.authError = "Password must contain at least 6 characters for security compliance.";
                return;
            }

            if (this.authMode === "register" && (!this.authForm.name || this.authForm.name.trim().length < 2)) {
                this.authError = "Full name is required to initialize your user profile.";
                return;
            }

            try {
                this.loading = true;
                if (this.authMode === "login") {
                    const res = await API.login(this.authForm.email, this.authForm.password);
                    API.setToken(res.access_token);
                    this.currentUser = res.user;
                    this.isAuthenticated = true;
                    this.notify("success", "Authentication Successful", `Welcome back, ${res.user.name} [Role: ${res.user.role.toUpperCase()}].`);
                } else {
                    await API.register(
                        this.authForm.name,
                        this.authForm.email,
                        this.authForm.password,
                        this.authForm.role
                    );
                    const res = await API.login(this.authForm.email, this.authForm.password);
                    API.setToken(res.access_token);
                    this.currentUser = res.user;
                    this.isAuthenticated = true;
                    this.notify("success", "Account Created", `Profile registered successfully. Logged in as ${res.user.name}.`);
                }

                // Reset auth fields
                this.authForm = { name: "", email: "", password: "", role: "customer" };
                this.activeTab = "dashboard";
                await this.refreshAllData();
            } catch (err) {
                this.authError = err.message || "Authentication could not be completed. Please check your credentials.";
            } finally {
                this.loading = false;
            }
        },

        async quickLogin(email, password) {
            this.authError = "";
            try {
                this.loading = true;
                const res = await API.login(email, password);
                API.setToken(res.access_token);
                this.currentUser = res.user;
                this.isAuthenticated = true;
                this.activeTab = "dashboard";
                this.notify("success", "Instant Session Started", `Logged in as ${res.user.name} [${res.user.role.toUpperCase()}].`);
                await this.refreshAllData();
            } catch (err) {
                this.authError = err.message || "Failed to initialize demo persona session.";
            } finally {
                this.loading = false;
            }
        },

        logout() {
            API.setToken(null);
            this.currentUser = null;
            this.isAuthenticated = false;
            this.activeTab = "dashboard";
            this.mobileMenuOpen = false;
            this.authForm = { name: "", email: "", password: "", role: "customer" };
            this.authError = "";
            this.notify("info", "Signed Out", "Your session has been securely terminated. Sign in again to resume.");
        },

        // ----------------- Data Refresh -----------------
        async refreshAllData() {
            if (!this.isAuthenticated || !this.currentUser) return;
            this.loading = true;
            try {
                await Promise.allSettled([
                    this.loadMetrics(),
                    this.loadSubscriptions(),
                    this.loadInvoices(),
                    this.loadPlans(),
                    this.loadProducts(),
                    this.loadDiscounts()
                ]);
            } catch (err) {
                console.error("Data synchronization error:", err);
            } finally {
                this.loading = false;
            }
        },

        async loadMetrics() {
            if (this.currentUser.role === "customer") return;
            try {
                this.metrics = await API.getDashboardMetrics();
            } catch (err) {
                console.warn("Metrics load skipped:", err.message);
            }
        },

        async loadSubscriptions() {
            try {
                this.subscriptions = await API.getSubscriptions(this.subStatusFilter || null);
            } catch (err) {
                this.subscriptions = [];
            }
        },

        async loadInvoices() {
            try {
                this.invoices = await API.getInvoices(this.invStatusFilter || null);
            } catch (err) {
                this.invoices = [];
            }
        },

        async loadPlans() {
            try {
                this.plans = await API.getPlans();
            } catch (err) {
                this.plans = [];
            }
        },

        async loadProducts() {
            try {
                this.products = await API.getProducts();
            } catch (err) {
                this.products = [];
            }
        },

        async loadDiscounts() {
            if (this.currentUser.role === "customer") return;
            try {
                this.discounts = await API.getDiscounts();
            } catch (err) {
                this.discounts = [];
            }
        },

        // ----------------- Subscription Lifecycle -----------------
        openNewSubModal() {
            if (this.plans.length > 0) {
                this.subForm.plan_id = this.plans[0].id;
            }
            this.subForm.quantity = 1;
            this.subForm.discount_code = "";
            this.subForm.status = "Draft";
            this.discountPreview = null;
            this.subModalOpen = true;
        },

        async checkDiscountCode() {
            if (!this.subForm.discount_code.trim()) {
                this.discountPreview = null;
                return;
            }
            const selectedPlan = this.plans.find(p => p.id == this.subForm.plan_id);
            const subtotal = selectedPlan ? (selectedPlan.price * this.subForm.quantity) : 0;
            try {
                const res = await API.validateDiscount(this.subForm.discount_code, subtotal);
                this.discountPreview = res;
            } catch (err) {
                this.discountPreview = { valid: false, reason: err.message };
            }
        },

        async handleCreateSubscription() {
            if (!this.subForm.plan_id) {
                this.notify("error", "Plan Selection Required", "Please select a subscription plan from the list.");
                return;
            }

            try {
                this.loading = true;
                const payload = {
                    plan_id: parseInt(this.subForm.plan_id),
                    quantity: parseInt(this.subForm.quantity || 1),
                    discount_code: this.subForm.discount_code.trim() || null,
                    status: this.subForm.status
                };
                const created = await API.createSubscription(payload);
                this.subModalOpen = false;
                this.notify("success", "Contract Initialized", `Subscription ${created.sub_number} recorded in status [${created.status}].`);
                await this.refreshAllData();
            } catch (err) {
                this.notify("error", "Validation Issue", err.message);
            } finally {
                this.loading = false;
            }
        },

        async transitionStatus(sub, targetStatus) {
            try {
                this.loading = true;
                const updated = await API.updateSubscriptionStatus(sub.id, targetStatus);
                this.notify("success", "Lifecycle Updated", `Subscription ${updated.sub_number} transitioned to [${targetStatus}].`);
                await this.refreshAllData();
            } catch (err) {
                this.notify("error", "Transition Denied", err.message);
            } finally {
                this.loading = false;
            }
        },

        // ----------------- Invoices & Settlements -----------------
        openPayModal(invoice) {
            this.selectedInvoice = invoice;
            this.payForm.amount = invoice.total_amount;
            this.payForm.method = "credit_card";
            this.payForm.notes = `Settlement for statement ${invoice.invoice_number}`;
            this.payModalOpen = true;
        },

        async handlePayInvoice() {
            if (!this.selectedInvoice) return;
            if (this.payForm.amount <= 0) {
                this.notify("error", "Invalid Amount", "Settlement amount must be greater than zero.");
                return;
            }

            try {
                this.loading = true;
                const payment = await API.payInvoice(this.selectedInvoice.id, {
                    method: this.payForm.method,
                    amount: parseFloat(this.payForm.amount),
                    notes: this.payForm.notes
                });
                this.payModalOpen = false;
                this.notify("success", "Payment Cleared", `Transaction ${payment.payment_number} settled for $${payment.amount.toFixed(2)}.`);
                await this.refreshAllData();
            } catch (err) {
                this.notify("error", "Payment Failed", err.message);
            } finally {
                this.loading = false;
            }
        },

        async triggerBillingEngine(subId = null) {
            try {
                this.loading = true;
                const generated = await API.generateInvoices(subId);
                const count = generated.length;
                this.notify("success", "Billing Run Complete", `Generated ${count} recurring statement(s) across active subscription cycles.`);
                await this.refreshAllData();
            } catch (err) {
                this.notify("error", "Billing Engine Notice", err.message);
            } finally {
                this.loading = false;
            }
        },

        // ----------------- Catalog & Rule Creators (Admin) -----------------
        async handleCreatePlan() {
            if (!this.planForm.name.trim()) {
                this.notify("error", "Field Required", "Plan name is required.");
                return;
            }
            if (this.planForm.price < 0) {
                this.notify("error", "Invalid Price", "Price cannot be negative.");
                return;
            }

            try {
                this.loading = true;
                const payload = {
                    name: this.planForm.name.trim(),
                    frequency: this.planForm.frequency,
                    min_quantity: parseInt(this.planForm.min_quantity || 1),
                    price: parseFloat(this.planForm.price),
                    status_rules: this.planForm.status_rules.trim() || null
                };
                await API.createPlan(payload);
                this.planModalOpen = false;
                this.planForm = { name: "", frequency: "monthly", min_quantity: 1, price: 0, status_rules: "" };
                this.notify("success", "Plan Published", "New subscription plan tier is now live.");
                await this.loadPlans();
            } catch (err) {
                this.notify("error", "Plan Setup Notice", err.message);
            } finally {
                this.loading = false;
            }
        },

        async handleCreateProduct() {
            if (!this.productForm.name.trim()) {
                this.notify("error", "Field Required", "Product name cannot be empty.");
                return;
            }

            try {
                this.loading = true;
                const payload = {
                    name: this.productForm.name.trim(),
                    type: this.productForm.type.trim(),
                    sales_price: parseFloat(this.productForm.sales_price),
                    cost_price: parseFloat(this.productForm.cost_price || 0),
                    variant_attribute: this.productForm.variant_attribute.trim() || null,
                    price_modifier: parseFloat(this.productForm.price_modifier || 0)
                };
                await API.createProduct(payload);
                this.productModalOpen = false;
                this.productForm = { name: "", type: "service", sales_price: 0, cost_price: 0, variant_attribute: "", price_modifier: 0 };
                this.notify("success", "Product Catalog Updated", "Product and variant specification recorded.");
                await this.loadProducts();
            } catch (err) {
                this.notify("error", "Product Setup Notice", err.message);
            } finally {
                this.loading = false;
            }
        },

        async handleCreateDiscount() {
            if (!this.discountForm.code.trim()) {
                this.notify("error", "Field Required", "Discount code cannot be blank.");
                return;
            }

            try {
                this.loading = true;
                const payload = {
                    code: this.discountForm.code.trim().toUpperCase(),
                    type: this.discountForm.type,
                    value: parseFloat(this.discountForm.value),
                    min_purchase: parseFloat(this.discountForm.min_purchase || 0),
                    usage_limit: parseInt(this.discountForm.usage_limit || 100),
                    expiry_date: this.discountForm.expiry_date ? new Date(this.discountForm.expiry_date).toISOString() : null
                };
                await API.createDiscount(payload);
                this.discountModalOpen = false;
                this.discountForm = { code: "", type: "percentage", value: 10, min_purchase: 0, usage_limit: 100, expiry_date: "" };
                this.notify("success", "Promotional Rule Active", "Discount rule configured and active.");
                await this.loadDiscounts();
            } catch (err) {
                this.notify("error", "Discount Setup Notice", err.message);
            } finally {
                this.loading = false;
            }
        },

        // ----------------- Helpers & Toasts -----------------
        notify(type, title, message) {
            const id = Date.now() + Math.random();
            this.toasts.push({ id, type, title, message });
            setTimeout(() => {
                this.toasts = this.toasts.filter(t => t.id !== id);
            }, 5000);
        },

        removeToast(id) {
            this.toasts = this.toasts.filter(t => t.id !== id);
        },

        formatCurrency(val) {
            return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(val || 0);
        },

        formatDate(isoStr) {
            if (!isoStr) return "N/A";
            const d = new Date(isoStr);
            return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
        },

        getStatusBadgeClass(status) {
            switch (status) {
                case "Active":
                case "Paid":
                    return "bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-400 border border-emerald-300 dark:border-emerald-800";
                case "Confirmed":
                    return "bg-blue-100 dark:bg-blue-950/80 text-blue-800 dark:text-blue-400 border border-blue-300 dark:border-blue-800";
                case "Quotation":
                    return "bg-amber-100 dark:bg-amber-950/80 text-amber-800 dark:text-amber-400 border border-amber-300 dark:border-amber-800";
                case "Draft":
                    return "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-700";
                case "Closed":
                    return "bg-rose-100 dark:bg-rose-950/80 text-rose-800 dark:text-rose-400 border border-rose-300 dark:border-rose-800";
                default:
                    return "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-400 border border-slate-300 dark:border-slate-700";
            }
        }
    }));
});
