const btn = document.getElementById("check-btn");
const rollbackBtn = document.getElementById("rollback-btn");
const statusEl = document.getElementById("status");
const logEl = document.getElementById("log");
const versionEl = document.getElementById("current-version");

const STATUS_LABELS = {
    no_update: { text: "Обновлений нет", cls: "info" },
    installed: { text: "Обновление установлено", cls: "ok" },
    verify_failed: { text: "Верификация не пройдена", cls: "warn" },
    install_failed_rolled_back: { text: "Ошибка установки, выполнен откат", cls: "warn" },
    install_failed: { text: "Ошибка установки, откат невозможен", cls: "err" },
    rolled_back: { text: "Откат выполнен", cls: "ok" },
    rollback_failed: { text: "Откат невозможен", cls: "err" },
    error: { text: "Ошибка", cls: "err" },
};

function refreshVersion() {
    fetch("/api/version")
        .then(r => r.json())
        .then(d => { versionEl.textContent = d.version || "не установлена"; })
        .catch(() => { versionEl.textContent = "—"; });
}

function renderStatus(result) {
    const label = STATUS_LABELS[result.status] || { text: result.status, cls: "info" };
    let text = label.text;
    if (result.error) text += ` — ${result.error}`;
    if (result.detail && result.detail.reason) {
        text += ` (${JSON.stringify(result.detail.reason)})`;
    }
    statusEl.textContent = text;
    statusEl.className = "status " + label.cls;
}

function renderLog(entries) {
    logEl.innerHTML = entries.map(e => {
        const granted = e.granted ? "✅" : "⛔";
        return `<div class="log-line">
            <span class="role">${e.role}</span>
            <span class="action">${e.action}</span>
            <span class="state">${e.state}</span>
            <span class="granted">${granted}</span>
        </div>`;
    }).join("");
    logEl.scrollTop = logEl.scrollHeight;
}

btn.addEventListener("click", async () => {
    btn.disabled = true;
    rollbackBtn.disabled = true;
    statusEl.textContent = "Выполняется...";
    statusEl.className = "status info";

    try {
        const resp = await fetch("/api/check", { method: "POST" });
        const data = await resp.json();
        renderStatus(data.result);
        renderLog(data.total_log);
    } catch (e) {
        statusEl.textContent = "Сетевая ошибка: " + e.message;
        statusEl.className = "status err";
    } finally {
        btn.disabled = false;
        rollbackBtn.disabled = false;
        refreshVersion();
    }
});

rollbackBtn.addEventListener("click", async () => {
    btn.disabled = true;
    rollbackBtn.disabled = true;
    statusEl.textContent = "Выполняется откат...";
    statusEl.className = "status info";

    try {
        const resp = await fetch("/api/rollback", { method: "POST" });
        const data = await resp.json();
        renderStatus(data.result);
        renderLog(data.total_log);
    } catch (e) {
        statusEl.textContent = "Сетевая ошибка: " + e.message;
        statusEl.className = "status err";
    } finally {
        btn.disabled = false;
        rollbackBtn.disabled = false;
        refreshVersion();
    }
});

// Первичная отрисовка лога и версии
fetch("/api/monitor_log")
    .then(r => r.json())
    .then(d => renderLog(d.log));

refreshVersion();