/**
 * INTRINSIC Subscription & Invoicing Platform
 * API Integration Layer with JWT Bearer handling and human-friendly error formatting.
 */

const API_BASE = "/api";
const TOKEN_STORAGE_KEY = "intrinsic_auth_token";

const API = {
    getToken() {
        return localStorage.getItem(TOKEN_STORAGE_KEY) || null;
    },

    setToken(token) {
        if (token) {
            localStorage.setItem(TOKEN_STORAGE_KEY, token);
        } else {
            localStorage.removeItem(TOKEN_STORAGE_KEY);
        }
    },

    formatErrorMessage(data, status) {
        if (!data) {
            return `Request could not be completed (Status ${status}).`;
        }

        // Check if detail is already a clean string
        if (typeof data.detail === "string") {
            return data.detail;
        }

        // If detail is an array of validation errors (Pydantic format)
        if (Array.isArray(data.detail)) {
            const messages = data.detail.map(item => {
                if (typeof item === "string") return item;
                const loc = Array.isArray(item.loc) 
                    ? item.loc.filter(l => l !== "body" && l !== "query").join(" ")
                    : "";
                const fieldName = loc ? loc.charAt(0).toUpperCase() + loc.slice(1) : "Field";
                const msg = item.msg || "is invalid";
                return `${fieldName}: ${msg}`;
            });
            return messages.join("; ");
        }

        if (data.message && typeof data.message === "string") {
            return data.message;
        }

        if (status === 401) {
            return "Invalid email or password. Please try again.";
        }
        if (status === 403) {
            return "You do not have permission to perform this action.";
        }
        if (status === 404) {
            return "The requested record was not found.";
        }

        return `An unexpected error occurred (Code ${status}).`;
    },

    async request(endpoint, options = {}) {
        const headers = {
            "Content-Type": "application/json",
            ...(options.headers || {})
        };

        const token = this.getToken();
        if (token) {
            headers["Authorization"] = `Bearer ${token}`;
        }

        const config = {
            ...options,
            headers
        };

        try {
            const response = await fetch(`${API_BASE}${endpoint}`, config);
            const contentType = response.headers.get("content-type");
            let data = null;

            if (contentType && contentType.includes("application/json")) {
                data = await response.json();
            } else {
                data = await response.text();
            }

            if (!response.ok) {
                // If 401 Unauthorized, automatically clear token if it wasn't a login attempt
                if (response.status === 401 && !endpoint.includes("/auth/login")) {
                    this.setToken(null);
                }
                const formattedMessage = this.formatErrorMessage(data, response.status);
                const error = new Error(formattedMessage);
                error.status = response.status;
                error.data = data;
                throw error;
            }

            return data;
        } catch (err) {
            console.warn(`[INTRINSIC API] Call to ${endpoint} failed:`, err.message);
            throw err;
        }
    },

    // ----------------- Auth -----------------
    login(email, password) {
        return this.request("/auth/login", {
            method: "POST",
            body: JSON.stringify({ email: email.trim(), password })
        });
    },

    register(name, email, password, role = "customer") {
        return this.request("/auth/register", {
            method: "POST",
            body: JSON.stringify({ name: name.trim(), email: email.trim(), password, role })
        });
    },

    getMe() {
        return this.request("/auth/me");
    },

    // ----------------- Plans -----------------
    getPlans() {
        return this.request("/plans");
    },

    createPlan(planData) {
        return this.request("/plans", {
            method: "POST",
            body: JSON.stringify(planData)
        });
    },

    // ----------------- Products -----------------
    getProducts() {
        return this.request("/products");
    },

    createProduct(productData) {
        return this.request("/products", {
            method: "POST",
            body: JSON.stringify(productData)
        });
    },

    // ----------------- Discounts -----------------
    getDiscounts() {
        return this.request("/discounts");
    },

    createDiscount(discountData) {
        return this.request("/discounts", {
            method: "POST",
            body: JSON.stringify(discountData)
        });
    },

    validateDiscount(code, amount = 0) {
        return this.request(`/discounts/validate/${encodeURIComponent(code)}?amount=${amount}`);
    },

    // ----------------- Subscriptions -----------------
    getSubscriptions(status = null) {
        const query = status ? `?status=${encodeURIComponent(status)}` : "";
        return this.request(`/subscriptions${query}`);
    },

    getSubscription(id) {
        return this.request(`/subscriptions/${id}`);
    },

    createSubscription(subscriptionData) {
        return this.request("/subscriptions", {
            method: "POST",
            body: JSON.stringify(subscriptionData)
        });
    },

    updateSubscriptionStatus(id, newStatus) {
        return this.request(`/subscriptions/${id}/status`, {
            method: "PATCH",
            body: JSON.stringify({ status: newStatus })
        });
    },

    // ----------------- Invoices & Billing -----------------
    getInvoices(status = null) {
        const query = status ? `?status=${encodeURIComponent(status)}` : "";
        return this.request(`/invoices${query}`);
    },

    getInvoice(id) {
        return this.request(`/invoices/${id}`);
    },

    generateInvoices(subscriptionId = null, issueDate = null) {
        return this.request("/invoices/generate", {
            method: "POST",
            body: JSON.stringify({
                subscription_id: subscriptionId,
                issue_date: issueDate
            })
        });
    },

    payInvoice(invoiceId, paymentData) {
        return this.request(`/invoices/${invoiceId}/pay`, {
            method: "POST",
            body: JSON.stringify(paymentData)
        });
    },

    // ----------------- Dashboard Metrics -----------------
    getDashboardMetrics() {
        return this.request("/dashboard/metrics");
    }
};

window.API = API;
