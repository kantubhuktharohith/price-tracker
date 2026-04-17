// Auto-detect the current tab's URL when popup opens
document.addEventListener('DOMContentLoaded', () => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        const currentUrl = tabs[0]?.url || '';
        // Only auto-fill if it looks like an Amazon product page
        if (currentUrl.includes('amazon.in') || currentUrl.includes('amazon.com')) {
            document.getElementById('productUrl').value = currentUrl;
        }
    });
});

// Handle clicking the Track button
document.getElementById('trackBtn').addEventListener('click', async () => {
    const url = document.getElementById('productUrl').value.trim();
    const targetPrice = document.getElementById('targetPrice').value.trim();
    const apiUrl = document.getElementById('apiUrl').value.trim();
    const statusEl = document.getElementById('status');
    const btn = document.getElementById('trackBtn');

    if (!url || !targetPrice) {
        statusEl.textContent = 'Please fill in both fields.';
        statusEl.className = 'error';
        return;
    }

    btn.disabled = true;
    btn.textContent = '⏳ Adding...';
    statusEl.style.display = 'none';

    try {
        const response = await fetch(`${apiUrl}/api/add`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url, target_price: parseFloat(targetPrice) })
        });

        const data = await response.json();

        if (response.ok) {
            statusEl.textContent = `✅ Now tracking: ${data.product.name}`;
            statusEl.className = 'success';
            document.getElementById('targetPrice').value = '';
        } else {
            statusEl.textContent = `❌ ${data.error || 'Failed to add.'}`;
            statusEl.className = 'error';
        }
    } catch (err) {
        statusEl.textContent = '❌ Cannot reach dashboard. Is app.py running?';
        statusEl.className = 'error';
    } finally {
        btn.disabled = false;
        btn.textContent = '🚀 Track This Product';
    }
});
