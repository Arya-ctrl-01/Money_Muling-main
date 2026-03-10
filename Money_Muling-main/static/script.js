document.addEventListener("DOMContentLoaded", function () {

    let network = null;
    let currentAnalysis = null;

    const themeToggle = document.getElementById("themeToggle");
    const browseBtn = document.getElementById("browseBtn");
    const fileInput = document.getElementById("fileInput");
    const uploadForm = document.getElementById("uploadForm");
    const emptyState = document.getElementById("emptyState");
    const loader = document.getElementById("netflixLoader");

    /* =========================
       THEME TOGGLE
    ========================== */

    if (localStorage.getItem("theme") === "light") {
        document.body.classList.add("light");
        themeToggle.innerText = "☀️";
    }

    themeToggle.addEventListener("click", function () {
        document.body.classList.toggle("light");

        if (document.body.classList.contains("light")) {
            localStorage.setItem("theme", "light");
            themeToggle.innerText = "☀️";
        } else {
            localStorage.setItem("theme", "dark");
            themeToggle.innerText = "🌙";
        }
    });

    /* =========================
       BROWSE BUTTON
    ========================== */

    browseBtn.addEventListener("click", function () {
        fileInput.click();
    });

    /* =========================
       AUTO UPLOAD ON FILE SELECT
    ========================== */

    fileInput.addEventListener("change", async function () {

        if (!fileInput.files.length) return;

        showLoader();

        const formData = new FormData(uploadForm);

        try {
            const response = await fetch("/upload", {
                method: "POST",
                body: formData
            });

            const responseData = await response.json();

            currentAnalysis = responseData.analysis;

            document.getElementById("accounts").innerText =
                currentAnalysis.summary.total_accounts_analyzed;

            document.getElementById("suspicious").innerText =
                currentAnalysis.summary.suspicious_accounts_flagged;

            document.getElementById("rings").innerText =
                currentAnalysis.summary.fraud_rings_detected;

            document.getElementById("time").innerText =
                currentAnalysis.summary.processing_time_seconds;

            emptyState.style.display = "none";

            renderGraph(responseData.graph);
            populateFraudRings(currentAnalysis.fraud_rings);

        } catch (error) {
            console.error(error);
            alert("Upload failed.");
        }

        hideLoader();
    });

    function showLoader() {
        loader.classList.add("active");
    }

    function hideLoader() {
        loader.classList.remove("active");
    }

    /* =========================
       RENDER GRAPH
    ========================== */

    function renderGraph(graph) {

        const container = document.getElementById("network");

        const suspiciousIds = currentAnalysis.suspicious_accounts.map(
            acc => acc.account_id
        );

        const formattedNodes = graph.nodes.map(node => {
            const isSuspicious = suspiciousIds.includes(node.id);

            return {
                id: node.id,
                label: node.id,
                shape: "circle",
                size: 28,
                font: { size: 12, color: "#ffffff" },
                borderWidth: 2,
                color: isSuspicious
                    ? { background: "#ef4444", border: "#7f1d1d" }
                    : { background: "#3b82f6", border: "#1e40af" }
            };
        });

        const data = {
            nodes: new vis.DataSet(formattedNodes),
            edges: new vis.DataSet(graph.edges)
        };

        const options = {
            edges: {
                arrows: { to: { enabled: true } },
                width: 1.5
            },
            physics: {
                enabled: true,
                solver: "forceAtlas2Based"
            }
        };

        network = new vis.Network(container, data, options);

        network.on("click", function (params) {
            if (params.nodes.length > 0) {
                showSelectedAccount(params.nodes[0]);
            }
        });
    }

    function showSelectedAccount(accountId) {

        const panel = document.getElementById("selectedAccount");

        const suspicious = currentAnalysis.suspicious_accounts.find(
            acc => acc.account_id === accountId
        );

        if (suspicious) {
            panel.innerHTML = `
                <strong>${accountId}</strong><br>
                Suspicion Score: ${suspicious.suspicion_score}<br>
                Ring: ${suspicious.ring_id}<br>
                Patterns: ${suspicious.detected_patterns.join(", ")}
            `;
        } else {
            panel.innerHTML = `
                <strong>${accountId}</strong><br>
                Clean Account
            `;
        }
    }

    function populateFraudRings(rings) {

        const container = document.getElementById("ringList");
        container.innerHTML = "";

        rings.forEach(ring => {
            const div = document.createElement("div");
            div.style.marginBottom = "12px";
            div.style.padding = "8px";
            div.style.borderRadius = "6px";
            div.style.background = "#1f2937";

            div.innerHTML = `
                <strong>${ring.ring_id}</strong><br>
                ${ring.pattern_type.toUpperCase()}<br>
                Risk: ${ring.risk_score}<br>
                ${ring.member_accounts.join(" → ")}
            `;

            container.appendChild(div);
        });
    }

    document.getElementById("downloadBtn").addEventListener("click", function () {
        window.location.href = "/download";
    });

});