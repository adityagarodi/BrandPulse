/**
 * BrandPulse — Frontend Application Logic (Split Architecture)
 * Communicates with Flask JSON API backend via fetch().
 */

// Global state
let currentAnalysisData = null;
let allPosts = [];
let filteredPosts = [];
let currentFilter = "all";
let currentSearchQuery = "";
let currentPage = 1;
const ITEMS_PER_PAGE = 10;

// Chart.js instances (tracked to destroy & recreate on new analysis)
let donutChartInstance = null;
let trendChartInstance = null;
let barChartInstance = null;

// Cold start timer handle
let coldStartTimer = null;

document.addEventListener("DOMContentLoaded", () => {
    checkBackendHealth();
    setupSourceModeTabs();
    setupQuickBrandButtons();
    setupSliders();
    setupFormSubmission();
    setupTableInteractions();
    setupCsvDownload();
});

// -----------------------------------------------------------------------------
// 1. Backend Health Check
// -----------------------------------------------------------------------------
async function checkBackendHealth() {
    const badge = document.getElementById("apiStatusBadge");
    if (!badge) return;

    try {
        const res = await fetch(`${API_BASE_URL}/health`, { method: "GET" });
        if (res.ok) {
            badge.className = "badge bg-success bg-opacity-25 text-success border border-success border-opacity-50 px-3 py-2 rounded-pill small";
            badge.innerHTML = `<i class="bi bi-hdd-network-fill me-1"></i> Backend Online`;
        } else {
            throw new Error("Health check returned status " + res.status);
        }
    } catch (err) {
        badge.className = "badge bg-warning bg-opacity-25 text-warning border border-warning border-opacity-50 px-3 py-2 rounded-pill small";
        badge.innerHTML = `<i class="bi bi-exclamation-circle me-1"></i> Backend Inactive / Waking Up`;
    }
}

// -----------------------------------------------------------------------------
// 2. Source Mode Tabs Switching
// -----------------------------------------------------------------------------
function setupSourceModeTabs() {
    const tabs = document.querySelectorAll(".source-tab");
    tabs.forEach(tab => {
        tab.addEventListener("click", function (e) {
            e.preventDefault();
            tabs.forEach(t => t.classList.remove("active"));
            this.classList.add("active");

            const mode = this.getAttribute("data-mode");
            document.querySelectorAll(".source-panel").forEach(p => p.classList.add("d-none"));
            const targetPanel = document.getElementById(`panel-${mode}`);
            if (targetPanel) {
                targetPanel.classList.remove("d-none");
            }
        });
    });
}

// -----------------------------------------------------------------------------
// 3. Quick Brand Pill Buttons
// -----------------------------------------------------------------------------
function setupQuickBrandButtons() {
    const buttons = document.querySelectorAll(".quick-brand-btn");
    buttons.forEach(btn => {
        btn.addEventListener("click", () => {
            const brand = btn.getAttribute("data-brand");
            const select = document.getElementById("sampleBrandSelect");
            if (select) select.value = brand;

            // Switch to sample tab
            const sampleTab = document.querySelector('.source-tab[data-mode="sample"]');
            if (sampleTab) sampleTab.click();

            // Run analysis immediately
            submitSampleAnalysis(brand, 50, 40);
        });
    });
}

// -----------------------------------------------------------------------------
// 4. Sliders Synchronization
// -----------------------------------------------------------------------------
function setupSliders() {
    const countSlider = document.getElementById("tweetCountRange");
    const countVal = document.getElementById("tweetCountVal");
    if (countSlider && countVal) {
        countSlider.addEventListener("input", () => {
            countVal.textContent = `${countSlider.value} posts`;
        });
    }

    const thresholdSlider = document.getElementById("thresholdRange");
    const thresholdVal = document.getElementById("thresholdVal");
    if (thresholdSlider && thresholdVal) {
        thresholdSlider.addEventListener("input", () => {
            thresholdVal.textContent = `${thresholdSlider.value}%`;
        });
    }
}

// -----------------------------------------------------------------------------
// 5. Loading Overlay & Cold Start Notice
// -----------------------------------------------------------------------------
function showLoading() {
    const overlay = document.getElementById("loadingOverlay");
    const notice = document.getElementById("coldStartNotice");
    if (overlay) overlay.classList.remove("d-none");
    if (notice) notice.classList.add("d-none");

    // If request takes longer than 4s, reveal the cold start waking up notice
    coldStartTimer = setTimeout(() => {
        if (notice) notice.classList.remove("d-none");
    }, 4000);
}

function hideLoading() {
    const overlay = document.getElementById("loadingOverlay");
    const notice = document.getElementById("coldStartNotice");
    if (overlay) overlay.classList.add("d-none");
    if (notice) notice.classList.add("d-none");

    if (coldStartTimer) {
        clearTimeout(coldStartTimer);
        coldStartTimer = null;
    }
}

// -----------------------------------------------------------------------------
// 6. Form Submission & API Calls
// -----------------------------------------------------------------------------
function setupFormSubmission() {
    const form = document.getElementById("analyzeForm");
    if (!form) return;

    form.addEventListener("submit", (e) => {
        e.preventDefault();
        clearError();

        const activeTab = document.querySelector(".source-tab.active");
        const mode = activeTab ? activeTab.getAttribute("data-mode") : "sample";
        const count = parseInt(document.getElementById("tweetCountRange").value, 10) || 50;
        const threshold = parseFloat(document.getElementById("thresholdRange").value) || 40.0;

        if (mode === "sample") {
            const customKeyword = document.getElementById("sampleKeywordInput").value.trim();
            const selectedBrand = document.getElementById("sampleBrandSelect").value;
            const brand = customKeyword || selectedBrand || "Apple";
            submitSampleAnalysis(brand, count, threshold);
        } else if (mode === "csv") {
            const fileInput = document.getElementById("csvFileInput");
            if (!fileInput.files || fileInput.files.length === 0) {
                showError("Please select a CSV file to upload.");
                return;
            }
            const brandLabel = document.getElementById("csvBrandInput").value.trim();
            submitCsvAnalysis(fileInput.files[0], brandLabel, count, threshold);
        } else if (mode === "live") {
            const keyword = document.getElementById("liveKeywordInput").value.trim();
            if (!keyword) {
                showError("Please enter a brand name or keyword for the live Twitter search.");
                return;
            }
            submitLiveAnalysis(keyword, count, threshold);
        }
    });
}

async function submitSampleAnalysis(brand, count, threshold) {
    showLoading();
    clearError();

    try {
        const res = await fetch(`${API_BASE_URL}/api/analyze/sample`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ brand, count, threshold })
        });

        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.error || `Error ${res.status}: ${res.statusText}`);
        }

        renderDashboard(data);
    } catch (err) {
        showError(err.message);
    } finally {
        hideLoading();
    }
}

async function submitCsvAnalysis(file, brand, count, threshold) {
    showLoading();
    clearError();

    const formData = new FormData();
    formData.append("file", file);
    if (brand) formData.append("brand", brand);
    formData.append("count", count);
    formData.append("threshold", threshold);

    try {
        const res = await fetch(`${API_BASE_URL}/api/analyze/csv`, {
            method: "POST",
            body: formData
        });

        const data = await res.json();
        if (!res.ok) {
            const msg = data.error + (data.user_hint ? ` (${data.user_hint})` : "");
            throw new Error(msg || `Error ${res.status}: ${res.statusText}`);
        }

        renderDashboard(data);
    } catch (err) {
        showError(err.message);
    } finally {
        hideLoading();
    }
}

async function submitLiveAnalysis(keyword, count, threshold) {
    showLoading();
    clearError();

    try {
        const res = await fetch(`${API_BASE_URL}/api/analyze/live`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ keyword, count, threshold })
        });

        const data = await res.json();
        if (!res.ok) {
            const msg = data.error + (data.user_hint ? ` — ${data.user_hint}` : "");
            throw new Error(msg || `Error ${res.status}: ${res.statusText}`);
        }

        renderDashboard(data);
    } catch (err) {
        showError(err.message);
    } finally {
        hideLoading();
    }
}

// -----------------------------------------------------------------------------
// 7. Error Display
// -----------------------------------------------------------------------------
function showError(message) {
    const container = document.getElementById("errorAlertContainer");
    if (!container) return;

    container.innerHTML = `
        <div class="alert alert-danger alert-dismissible fade show border-0 shadow-sm mb-4" role="alert">
            <div class="d-flex align-items-center">
                <i class="bi bi-exclamation-triangle-fill fs-5 me-2"></i>
                <div>${message}</div>
            </div>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    container.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function clearError() {
    const container = document.getElementById("errorAlertContainer");
    if (container) container.innerHTML = "";
}

// -----------------------------------------------------------------------------
// 8. Render Complete Dashboard
// -----------------------------------------------------------------------------
function renderDashboard(data) {
    currentAnalysisData = data;
    allPosts = data.posts || [];

    const dashSection = document.getElementById("dashboardSection");
    if (!dashSection) return;
    dashSection.classList.remove("d-none");

    // Header Meta
    document.getElementById("dashBrandName").textContent = data.meta.brand;
    document.getElementById("dashSourceBadge").textContent = data.meta.source;
    document.getElementById("dashTimestamp").textContent = data.meta.timestamp;
    document.getElementById("dashPostCount").textContent = data.meta.count;

    // Alert Banner
    const alertBanner = document.getElementById("dashAlertBanner");
    if (data.alert && data.alert.alert_triggered) {
        alertBanner.className = "bp-alert-critical d-flex align-items-center justify-content-between mb-4 shadow";
        alertBanner.innerHTML = `
            <div class="d-flex align-items-center gap-3">
                <div class="fs-2 text-danger"><i class="bi bi-exclamation-octagon-fill"></i></div>
                <div>
                    <h5 class="fw-bold text-danger mb-1">Reputation Alert: High Negative Sentiment!</h5>
                    <p class="text-light mb-0 small">${data.alert.alert_message}</p>
                </div>
            </div>
            <span class="badge bg-danger text-light px-3 py-2 rounded-pill fw-bold">CRITICAL</span>
        `;
    } else {
        alertBanner.className = "d-none";
        alertBanner.innerHTML = "";
    }

    // Summary Cards
    const s = data.summary;
    document.getElementById("cardTotalPosts").textContent = s.total_posts;
    document.getElementById("cardPositivePct").textContent = `${s.positive_pct}%`;
    document.getElementById("cardPositiveCount").textContent = s.positive_count;
    document.getElementById("cardNeutralPct").textContent = `${s.neutral_pct}%`;
    document.getElementById("cardNeutralCount").textContent = s.neutral_count;
    document.getElementById("cardNegativePct").textContent = `${s.negative_pct}%`;
    document.getElementById("cardNegativeCount").textContent = s.negative_count;

    const avgEl = document.getElementById("cardAvgCompound");
    avgEl.textContent = (s.avg_compound >= 0 ? "+" : "") + s.avg_compound.toFixed(3);
    avgEl.className = `metric-value ${s.avg_compound >= 0.05 ? "text-success" : (s.avg_compound <= -0.05 ? "text-danger" : "text-warning")}`;

    const healthEl = document.getElementById("cardBrandHealth");
    healthEl.textContent = s.brand_health;
    healthEl.className = `metric-value fs-3 text-${s.health_badge_class}`;
    document.getElementById("cardHealthDesc").textContent = s.health_description;

    const healthBox = document.getElementById("cardHealthBox");
    healthBox.className = `metric-card ${s.brand_health === "Healthy" ? "positive" : (s.brand_health === "Warning" ? "neutral" : "negative")}`;

    // Render Charts
    renderCharts(data);

    // Render Word Clouds
    const posImg = document.getElementById("posWordcloudImg");
    const negImg = document.getElementById("negWordcloudImg");
    if (posImg) posImg.src = data.wordclouds.positive;
    if (negImg) negImg.src = data.wordclouds.negative;

    // Reset Table Filters & Render Posts
    currentFilter = "all";
    currentSearchQuery = "";
    currentPage = 1;
    const searchInput = document.getElementById("postSearchInput");
    if (searchInput) searchInput.value = "";
    document.querySelectorAll(".sentiment-filter-btn").forEach(b => {
        b.classList.toggle("active", b.getAttribute("data-filter") === "all");
    });

    updateTable();

    // Smooth scroll down to dashboard
    dashSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

// -----------------------------------------------------------------------------
// 9. Chart.js Renderings
// -----------------------------------------------------------------------------
function renderCharts(data) {
    const fontColor = "#94a3b8";
    const gridColor = "rgba(51, 65, 85, 0.4)";
    Chart.defaults.color = fontColor;
    Chart.defaults.font.family = "'Inter', sans-serif";

    // 1. Donut Chart
    const donutCtx = document.getElementById("sentimentDonutChart");
    if (donutCtx) {
        if (donutChartInstance) donutChartInstance.destroy();
        donutChartInstance = new Chart(donutCtx, {
            type: "doughnut",
            data: {
                labels: data.distribution.labels,
                datasets: [{
                    data: data.distribution.counts,
                    backgroundColor: ["#10B981", "#F59E0B", "#EF4444"],
                    hoverBackgroundColor: ["#059669", "#D97706", "#DC2626"],
                    borderWidth: 2,
                    borderColor: "#151d30",
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "70%",
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: { padding: 16, usePointStyle: true, font: { size: 12, weight: "bold" } }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                const val = ctx.raw || 0;
                                const pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
                                return ` ${ctx.label}: ${val} posts (${pct}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    // 2. Trend Line Chart
    const lineCtx = document.getElementById("sentimentTrendChart");
    if (lineCtx) {
        if (trendChartInstance) trendChartInstance.destroy();
        const trend = data.daily_trend;
        trendChartInstance = new Chart(lineCtx, {
            type: "line",
            data: {
                labels: trend.dates,
                datasets: [
                    {
                        label: "Positive",
                        data: trend.positive,
                        borderColor: "#10B981",
                        backgroundColor: "rgba(16, 185, 129, 0.15)",
                        tension: 0.35,
                        fill: true,
                        pointRadius: 4,
                    },
                    {
                        label: "Neutral",
                        data: trend.neutral,
                        borderColor: "#F59E0B",
                        backgroundColor: "rgba(245, 158, 11, 0.1)",
                        tension: 0.35,
                        fill: false,
                        pointRadius: 4,
                    },
                    {
                        label: "Negative",
                        data: trend.negative,
                        borderColor: "#EF4444",
                        backgroundColor: "rgba(239, 68, 68, 0.15)",
                        tension: 0.35,
                        fill: true,
                        pointRadius: 4,
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { color: fontColor } },
                    y: { beginAtZero: true, grid: { color: gridColor }, ticks: { color: fontColor, precision: 0 } }
                },
                plugins: {
                    legend: { position: "top", labels: { usePointStyle: true, padding: 12 } }
                }
            }
        });
    }

    // 3. Top Keywords Horizontal Bar Chart
    const barCtx = document.getElementById("topKeywordsChart");
    if (barCtx) {
        if (barChartInstance) barChartInstance.destroy();
        const keywords = data.top_keywords || [];
        barChartInstance = new Chart(barCtx, {
            type: "bar",
            data: {
                labels: keywords.map(k => k.word),
                datasets: [{
                    label: "Occurrences",
                    data: keywords.map(k => k.count),
                    backgroundColor: "#6366F1",
                    hoverBackgroundColor: "#4F46E5",
                    borderRadius: 6,
                    borderWidth: 0,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: "y",
                scales: {
                    x: { beginAtZero: true, grid: { color: gridColor }, ticks: { color: fontColor, precision: 0 } },
                    y: { grid: { display: false }, ticks: { color: "#f8fafc", font: { weight: "600" } } }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: { label: (ctx) => ` Frequency: ${ctx.raw} occurrences` }
                    }
                }
            }
        });
    }
}

// -----------------------------------------------------------------------------
// 10. Posts Table Filter, Live Search & Pagination
// -----------------------------------------------------------------------------
function setupTableInteractions() {
    const searchInput = document.getElementById("postSearchInput");
    if (searchInput) {
        searchInput.addEventListener("input", function () {
            currentSearchQuery = this.value.trim().toLowerCase();
            currentPage = 1;
            updateTable();
        });
    }

    const filterBtns = document.querySelectorAll(".sentiment-filter-btn");
    filterBtns.forEach(btn => {
        btn.addEventListener("click", function () {
            filterBtns.forEach(b => b.classList.remove("active"));
            this.classList.add("active");
            currentFilter = this.getAttribute("data-filter") || "all";
            currentPage = 1;
            updateTable();
        });
    });
}

function updateTable() {
    const tableBody = document.getElementById("postsTableBody");
    const countDisplay = document.getElementById("filteredPostCount");
    if (!tableBody) return;

    // Filter posts
    filteredPosts = allPosts.filter(p => {
        const sentimentMatch = (currentFilter === "all") || (p.sentiment.toLowerCase() === currentFilter.toLowerCase());
        const queryMatch = (!currentSearchQuery) || p.text.toLowerCase().includes(currentSearchQuery);
        return sentimentMatch && queryMatch;
    });

    if (countDisplay) {
        countDisplay.textContent = `Showing ${filteredPosts.length} of ${allPosts.length} posts`;
    }

    // Pagination bounds
    const totalPages = Math.ceil(filteredPosts.length / ITEMS_PER_PAGE) || 1;
    if (currentPage > totalPages) currentPage = totalPages;
    if (currentPage < 1) currentPage = 1;

    const startIdx = (currentPage - 1) * ITEMS_PER_PAGE;
    const pageItems = filteredPosts.slice(startIdx, startIdx + ITEMS_PER_PAGE);

    // Render Table Rows
    if (pageItems.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-muted">No posts match the current filter or search criteria.</td></tr>`;
    } else {
        tableBody.innerHTML = pageItems.map(p => {
            const badgeClass = p.sentiment === "Positive" ? "badge-sentiment-positive" :
                (p.sentiment === "Negative" ? "badge-sentiment-negative" : "badge-sentiment-neutral");
            const icon = p.sentiment === "Positive" ? "bi-arrow-up-right" :
                (p.sentiment === "Negative" ? "bi-arrow-down-right" : "bi-dash");
            const scoreColor = p.compound_score >= 0.05 ? "text-success" :
                (p.compound_score <= -0.05 ? "text-danger" : "text-warning");

            return `
                <tr>
                    <td class="small text-muted text-nowrap">${p.date ? p.date.substring(0, 10) : "N/A"}</td>
                    <td><span class="${badgeClass}"><i class="bi ${icon} me-1"></i> ${p.sentiment}</span></td>
                    <td><span class="fw-bold ${scoreColor}">${(p.compound_score >= 0 ? "+" : "") + p.compound_score.toFixed(3)}</span></td>
                    <td class="small text-muted">
                        <span class="text-success">${Math.round(p.pos_score * 100)}%</span> /
                        <span class="text-warning">${Math.round(p.neu_score * 100)}%</span> /
                        <span class="text-danger">${Math.round(p.neg_score * 100)}%</span>
                    </td>
                    <td class="text-light small">${escapeHtml(p.text)}</td>
                </tr>
            `;
        }).join("");
    }

    renderPagination(totalPages, currentPage);
}

function renderPagination(totalPages, activePage) {
    const nav = document.getElementById("paginationNav");
    if (!nav) return;
    nav.innerHTML = "";

    if (totalPages <= 1) return;

    const ul = document.createElement("ul");
    ul.className = "pagination pagination-sm mb-0 justify-content-center";

    // Previous Button
    const prevLi = document.createElement("li");
    prevLi.className = `page-item ${activePage === 1 ? 'disabled' : ''}`;
    prevLi.innerHTML = `<button class="page-link bg-dark text-light border-secondary">Previous</button>`;
    prevLi.addEventListener("click", () => {
        if (activePage > 1) {
            currentPage = activePage - 1;
            updateTable();
        }
    });
    ul.appendChild(prevLi);

    // Page Buttons
    for (let i = 1; i <= totalPages; i++) {
        const pageLi = document.createElement("li");
        pageLi.className = `page-item ${i === activePage ? 'active' : ''}`;
        pageLi.innerHTML = `<button class="page-link ${i === activePage ? 'bg-primary border-primary' : 'bg-dark text-light border-secondary'}">${i}</button>`;
        pageLi.addEventListener("click", () => {
            currentPage = i;
            updateTable();
        });
        ul.appendChild(pageLi);
    }

    // Next Button
    const nextLi = document.createElement("li");
    nextLi.className = `page-item ${activePage === totalPages ? 'disabled' : ''}`;
    nextLi.innerHTML = `<button class="page-link bg-dark text-light border-secondary">Next</button>`;
    nextLi.addEventListener("click", () => {
        if (activePage < totalPages) {
            currentPage = activePage + 1;
            updateTable();
        }
    });
    ul.appendChild(nextLi);

    nav.appendChild(ul);
}

// -----------------------------------------------------------------------------
// 11. Client-Side CSV Download
// -----------------------------------------------------------------------------
function setupCsvDownload() {
    const btn = document.getElementById("downloadCsvBtn");
    if (!btn) return;

    btn.addEventListener("click", () => {
        if (!allPosts || allPosts.length === 0) {
            showError("No analyzed posts to export.");
            return;
        }

        const brandName = (currentAnalysisData && currentAnalysisData.meta && currentAnalysisData.meta.brand) || "BrandPulse";
        const headers = ["Post ID", "Date", "Brand", "Sentiment", "Compound Score", "Positive Score", "Neutral Score", "Negative Score", "Cleaned Text", "Original Text"];
        
        const rows = allPosts.map(p => [
            p.id || "",
            p.date || "",
            brandName,
            p.sentiment || "",
            p.compound_score,
            p.pos_score,
            p.neu_score,
            p.neg_score,
            `"${(p.cleaned_text || "").replace(/"/g, '""')}"`,
            `"${(p.text || "").replace(/"/g, '""')}"`
        ]);

        const csvContent = "\uFEFF" + [headers.join(","), ...rows.map(r => r.join(","))].join("\r\n");
        const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement("a");
        a.href = url;
        a.download = `BrandPulse_${brandName.replace(/[^a-zA-Z0-9]/g, "_")}_Export.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });
}

function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;")
              .replace(/</g, "&lt;")
              .replace(/>/g, "&gt;")
              .replace(/"/g, "&quot;")
              .replace(/'/g, "&#039;");
}
