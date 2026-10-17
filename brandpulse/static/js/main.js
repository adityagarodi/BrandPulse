/**
 * BrandPulse — Client-Side JavaScript
 * Handles Chart.js initialization, live search, table filtering, pagination, and form spinners.
 */

document.addEventListener("DOMContentLoaded", function () {
    // -------------------------------------------------------------------------
    // 1. Loading Overlay on Form Submit
    // -------------------------------------------------------------------------
    const analyzeForms = document.querySelectorAll("form.needs-loading");
    const loadingOverlay = document.getElementById("loadingOverlay");

    analyzeForms.forEach(form => {
        form.addEventListener("submit", function () {
            if (loadingOverlay) {
                loadingOverlay.classList.remove("d-none");
            }
        });
    });

    // -------------------------------------------------------------------------
    // 2. Source Mode Tab Switcher (Index Page)
    // -------------------------------------------------------------------------
    const sourceTabs = document.querySelectorAll(".source-mode-tab");
    const sourceModeInput = document.getElementById("source_mode");

    if (sourceTabs.length > 0 && sourceModeInput) {
        sourceTabs.forEach(tab => {
            tab.addEventListener("click", function (e) {
                e.preventDefault();
                sourceTabs.forEach(t => t.classList.remove("active"));
                this.classList.add("active");

                const targetMode = this.getAttribute("data-mode");
                sourceModeInput.value = targetMode;

                // Toggle visibility of source-specific panels
                document.querySelectorAll(".source-panel").forEach(p => p.classList.add("d-none"));
                const activePanel = document.getElementById(`panel-${targetMode}`);
                if (activePanel) {
                    activePanel.classList.remove("d-none");
                }
            });
        });
    }

    // -------------------------------------------------------------------------
    // 3. Posts Table Filtering, Search, and Pagination
    // -------------------------------------------------------------------------
    const searchInput = document.getElementById("postSearchInput");
    const filterButtons = document.querySelectorAll(".sentiment-filter-btn");
    const tableBody = document.getElementById("postsTableBody");
    const paginationContainer = document.getElementById("paginationNav");
    const postCountDisplay = document.getElementById("filteredPostCount");

    if (tableBody) {
        const rows = Array.from(tableBody.querySelectorAll("tr.post-row"));
        let currentFilter = "all";
        let currentQuery = "";
        let currentPage = 1;
        const itemsPerPage = 10;

        function updateTable() {
            // 1. Filter rows
            const filteredRows = rows.filter(row => {
                const sentiment = row.getAttribute("data-sentiment") || "";
                const text = (row.querySelector(".post-text")?.textContent || "").toLowerCase();

                const matchesFilter = (currentFilter === "all") || (sentiment.toLowerCase() === currentFilter.toLowerCase());
                const matchesQuery = (!currentQuery) || text.includes(currentQuery);

                return matchesFilter && matchesQuery;
            });

            // 2. Update post count badge
            if (postCountDisplay) {
                postCountDisplay.textContent = `Showing ${filteredRows.length} of ${rows.length} posts`;
            }

            // 3. Pagination calculation
            const totalPages = Math.ceil(filteredRows.length / itemsPerPage) || 1;
            if (currentPage > totalPages) currentPage = totalPages;
            if (currentPage < 1) currentPage = 1;

            const startIndex = (currentPage - 1) * itemsPerPage;
            const endIndex = startIndex + itemsPerPage;

            // 4. Render rows
            rows.forEach(r => r.style.display = "none");
            filteredRows.slice(startIndex, endIndex).forEach(r => r.style.display = "");

            // 5. Render Pagination Controls
            renderPagination(totalPages, currentPage);
        }

        function renderPagination(totalPages, activePage) {
            if (!paginationContainer) return;
            paginationContainer.innerHTML = "";

            if (totalPages <= 1) return;

            const ul = document.createElement("ul");
            ul.className = "pagination pagination-sm mb-0 justify-content-center";

            // Prev Button
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

            // Page numbers
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

            paginationContainer.appendChild(ul);
        }

        // Live Search Input Listener
        if (searchInput) {
            searchInput.addEventListener("input", function () {
                currentQuery = this.value.trim().toLowerCase();
                currentPage = 1;
                updateTable();
            });
        }

        // Sentiment Filter Buttons
        if (filterButtons.length > 0) {
            filterButtons.forEach(btn => {
                btn.addEventListener("click", function () {
                    filterButtons.forEach(b => b.classList.remove("active"));
                    this.classList.add("active");
                    currentFilter = this.getAttribute("data-filter") || "all";
                    currentPage = 1;
                    updateTable();
                });
            });
        }

        // Initial table render
        updateTable();
    }
});

/**
 * Initializes Dashboard Charts using Chart.js configurations passed from backend
 */
function initDashboardCharts(chartData) {
    if (!chartData) return;

    const defaultFontColor = "#94a3b8";
    const defaultGridColor = "rgba(51, 65, 85, 0.4)";

    // Chart.js global styling defaults
    Chart.defaults.color = defaultFontColor;
    Chart.defaults.font.family = "'Inter', sans-serif";

    // 1. Donut Chart (Sentiment Distribution)
    const donutCtx = document.getElementById("sentimentDonutChart");
    if (donutCtx && chartData.donut_chart) {
        new Chart(donutCtx, {
            type: "doughnut",
            data: chartData.donut_chart,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "70%",
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            padding: 18,
                            usePointStyle: true,
                            font: { size: 12, weight: "bold" }
                        }
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

    // 2. Line Chart (Sentiment Trend Over Time)
    const lineCtx = document.getElementById("sentimentTrendChart");
    if (lineCtx && chartData.line_chart) {
        new Chart(lineCtx, {
            type: "line",
            data: chartData.line_chart,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: "index",
                    intersect: false
                },
                scales: {
                    x: {
                        grid: { color: defaultGridColor },
                        ticks: { color: defaultFontColor }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: defaultGridColor },
                        ticks: { color: defaultFontColor, precision: 0 }
                    }
                },
                plugins: {
                    legend: {
                        position: "top",
                        labels: { usePointStyle: true, padding: 12 }
                    }
                }
            }
        });
    }

    // 3. Bar Chart (Top Keywords)
    const barCtx = document.getElementById("topKeywordsChart");
    if (barCtx && chartData.bar_chart) {
        new Chart(barCtx, {
            type: "bar",
            data: chartData.bar_chart,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: "y", // Horizontal bars for clean reading of words
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: { color: defaultGridColor },
                        ticks: { color: defaultFontColor, precision: 0 }
                    },
                    y: {
                        grid: { display: false },
                        ticks: { color: "#f8fafc", font: { weight: "600" } }
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => ` Frequency: ${ctx.raw} occurrences`
                        }
                    }
                }
            }
        });
    }
}
