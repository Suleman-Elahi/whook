console.log('Initializing WebSocket connection...');
let ws = null;
let reconnectInterval = null;
let currentRequestData = null;

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    console.log('Connecting to:', wsUrl);
    ws = new WebSocket(wsUrl);
    
    ws.onopen = function() {
        console.log('WebSocket Connected!');
        if (reconnectInterval) {
            clearInterval(reconnectInterval);
            reconnectInterval = null;
        }
    };
    
    ws.onerror = function(error) {
        console.error('WebSocket Error:', error);
    };
    
    ws.onclose = function(event) {
        console.log('WebSocket Disconnected:', event.code, event.reason);
        if (!reconnectInterval) {
            reconnectInterval = setInterval(() => {
                console.log('Attempting to reconnect...');
                connectWebSocket();
            }, 2000);
        }
    };
    
    ws.onmessage = function(event) {
        console.log('WebSocket message received:', event.data);
        try {
            const data = JSON.parse(event.data);
            
            if (data.type === 'new_webhook_request') {
                console.log('Received new_webhook_request event:', data);
                
                const webhookId = document.body.dataset.webhookId;
                if (data.webhook_id && data.webhook_id.toString() === webhookId) {
                    console.log('New request for current webhook, reloading...');
                    setTimeout(() => {
                        location.reload();
                    }, 300);
                } else {
                    console.log('Request is for a different webhook, ignoring...');
                }
            }
        } catch (e) {
            console.error('Error parsing WebSocket message:', e);
        }
    };
}

// Initialize connection
connectWebSocket();

// Show request details
function showRequest(requestId) {
    // Remove active class from all items
    document.querySelectorAll('.request-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // Add active class to clicked item
    const clickedItem = document.querySelector(`[data-request-id="${requestId}"]`);
    if (clickedItem) {
        clickedItem.classList.add('active');
    }
    
    fetch(`/webhook/request/${requestId}`)
        .then(response => response.json())
        .then(data => {
            currentRequestData = data;
            updateRequestDetails(data);
        })
        .catch(error => {
            console.error('Error fetching request:', error);
        });
}

function updateRequestDetails(data) {
    // Update stats bar
    document.getElementById('status-code').textContent = '200 OK';
    document.getElementById('timestamp').textContent = data.timestamp || 'N/A';
    document.getElementById('response-time').textContent = '245ms';
    document.getElementById('size').textContent = `${data.body.length} bytes`;
    
    // Update Body tab
    updateBodyTab(data.body);
    
    // Update Headers tab
    updateHeadersTab(data.headers);
    
    // Update Raw tab
    updateRawTab(data);
}

function updateBodyTab(body) {
    const bodyContent = document.getElementById('body-content');
    const bodyContentText = document.getElementById('body-content-text');
    const codeElement = bodyContent.querySelector('code') || bodyContent;
    
    try {
        const parsed = JSON.parse(body);
        const formatted = JSON.stringify(parsed, null, 2);
        codeElement.textContent = formatted;
        if (bodyContentText) {
            bodyContentText.textContent = formatted;
        }
        
        // Apply syntax highlighting
        highlightJSON(codeElement);
    } catch (e) {
        codeElement.textContent = body;
        if (bodyContentText) {
            bodyContentText.textContent = body;
        }
    }
}

function updateHeadersTab(headers) {
    const headersTable = document.getElementById('headers-table');
    const tbody = headersTable.querySelector('tbody');
    const headersCount = document.getElementById('headers-count');
    const headersContentText = document.getElementById('headers-content-text');
    
    tbody.innerHTML = '';
    
    const headerEntries = Object.entries(headers);
    headersCount.textContent = headerEntries.length;
    
    // Update hidden text element for copy button
    if (headersContentText) {
        headersContentText.textContent = JSON.stringify(headers, null, 2);
    }
    
    if (headerEntries.length === 0) {
        tbody.innerHTML = '<tr><td colspan="2" class="empty-message">No headers</td></tr>';
        return;
    }
    
    headerEntries.forEach(([key, value]) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${escapeHtml(key)}</td>
            <td>${escapeHtml(value)}</td>
        `;
        tbody.appendChild(row);
    });
}

function updateRawTab(data) {
    const rawContent = document.getElementById('raw-content');
    const rawContentText = document.getElementById('raw-content-text');
    const codeElement = rawContent.querySelector('code') || rawContent;
    
    const raw = `Headers:\n${JSON.stringify(data.headers, null, 2)}\n\nBody:\n${data.body}`;
    codeElement.textContent = raw;
    if (rawContentText) {
        rawContentText.textContent = raw;
    }
}

function highlightJSON(element) {
    let html = element.textContent;
    
    // Highlight keys
    html = html.replace(/"([^"]+)":/g, '<span class="json-key">"$1"</span>:');
    
    // Highlight strings
    html = html.replace(/: "([^"]*)"/g, ': <span class="json-string">"$1"</span>');
    
    // Highlight numbers
    html = html.replace(/: (\d+\.?\d*)/g, ': <span class="json-number">$1</span>');
    
    // Highlight booleans
    html = html.replace(/: (true|false)/g, ': <span class="json-boolean">$1</span>');
    
    // Highlight null
    html = html.replace(/: (null)/g, ': <span class="json-null">$1</span>');
    
    element.innerHTML = html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Delete single request
function deleteRequest(requestId) {
    if (!confirm('Delete this request?')) return;
    
    fetch('/delete_request', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ id: requestId })
    })
    .then(response => {
        if (response.ok) {
            const item = document.querySelector(`[data-request-id="${requestId}"]`);
            if (item) {
                item.remove();
            }
            
            // Clear details if this was the active request
            if (item && item.classList.contains('active')) {
                document.getElementById('body-content').innerHTML = '<code>Select a request to view details</code>';
            }
        }
    })
    .catch(error => {
        console.error('Error deleting request:', error);
    });
}

// Filter functionality
const statusFilter = document.getElementById('status-filter');
const dateFilter = document.getElementById('date-filter');

function applyFilters() {
    const statusValue = statusFilter?.value;
    const dateValue = dateFilter?.value;
    const items = document.querySelectorAll('.request-item');
    
    console.log('Applying filters - Status:', statusValue, 'Date:', dateValue);
    
    items.forEach(item => {
        let showItem = true;
        
        // Status filter
        if (statusValue) {
            const itemStatus = item.getAttribute('data-status');
            console.log('Item status:', itemStatus, 'Filter:', statusValue);
            if (itemStatus !== statusValue) {
                showItem = false;
            }
        }
        
        // Date filter
        if (dateValue && showItem) {
            const timeText = item.querySelector('.request-time')?.textContent;
            const now = new Date();
            
            // Parse the timestamp
            if (timeText && timeText !== 'Just now') {
                // This is a simplified date filter
                // In production, you'd want to parse the actual timestamp properly
                const today = now.toDateString();
                
                switch(dateValue) {
                    case 'today':
                        // Show only today's requests
                        if (!timeText.includes(now.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }))) {
                            showItem = false;
                        }
                        break;
                    case 'yesterday':
                        const yesterday = new Date(now);
                        yesterday.setDate(yesterday.getDate() - 1);
                        if (!timeText.includes(yesterday.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }))) {
                            showItem = false;
                        }
                        break;
                    case 'week':
                    case 'month':
                        // For week and month, show all for now
                        // In production, you'd parse and compare actual dates
                        break;
                }
            }
        }
        
        item.style.display = showItem ? '' : 'none';
    });
}

if (statusFilter) {
    statusFilter.addEventListener('sl-change', (e) => {
        console.log('Status filter changed:', e.target.value);
        applyFilters();
    });
    
    statusFilter.addEventListener('sl-clear', () => {
        console.log('Status filter cleared');
        applyFilters();
    });
}

if (dateFilter) {
    dateFilter.addEventListener('sl-change', (e) => {
        console.log('Date filter changed:', e.target.value);
        applyFilters();
    });
    
    dateFilter.addEventListener('sl-clear', () => {
        console.log('Date filter cleared');
        applyFilters();
    });
}

// Delete all functionality
document.addEventListener('DOMContentLoaded', function() {
    const deleteAllBtn = document.querySelector('.delete-all-btn');
    const deleteAllDialog = document.querySelector('.delete-all-dialog');
    const cancelBtn = document.querySelector('.dialog-cancel-btn');
    const confirmBtn = document.querySelector('.dialog-confirm-btn');
    
    if (deleteAllBtn) {
        deleteAllBtn.addEventListener('click', () => {
            deleteAllDialog.show();
        });
    }
    
    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
            deleteAllDialog.hide();
        });
    }
    
    if (confirmBtn) {
        confirmBtn.addEventListener('click', () => {
            const path = window.location.pathname;
            const pathParts = path.split('/');
            const webhookId = pathParts[pathParts.length - 1];
            
            fetch('/webhooks/delete_all', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ webhook_id: webhookId })
            })
            .then(response => response.json())
            .then(data => {
                if (data.message) {
                    location.reload();
                }
            })
            .catch(error => {
                console.error('Error deleting all requests:', error);
            })
            .finally(() => {
                deleteAllDialog.hide();
            });
        });
    }
    
    // Copy cURL button
    const copyCurlBtn = document.getElementById('copy-url-btn');
    if (copyCurlBtn) {
        copyCurlBtn.addEventListener('click', () => {
            const url = window.location.origin + '/' + document.querySelector('.endpoint-url').textContent.replace('/', '');
            const curl = `curl -X POST "${url}" -H "Content-Type: application/json" -d '{"test": "data"}'`;
            
            navigator.clipboard.writeText(curl).then(() => {
                copyCurlBtn.innerHTML = '<sl-icon slot="prefix" name="check"></sl-icon>Copied!';
                setTimeout(() => {
                    copyCurlBtn.innerHTML = '<sl-icon slot="prefix" name="clipboard"></sl-icon>Copy cURL';
                }, 2000);
            });
        });
    }
    
    // Format buttons
    const formatJsonBtn = document.getElementById('format-json');
    const formatRawBtn = document.getElementById('format-raw');
    
    if (formatJsonBtn && formatRawBtn) {
        formatJsonBtn.addEventListener('click', () => {
            if (currentRequestData) {
                const bodyContent = document.getElementById('body-content');
                const bodyContentText = document.getElementById('body-content-text');
                const codeElement = bodyContent.querySelector('code') || bodyContent;
                
                try {
                    const parsed = JSON.parse(currentRequestData.body);
                    const formatted = JSON.stringify(parsed, null, 2);
                    codeElement.textContent = formatted;
                    if (bodyContentText) {
                        bodyContentText.textContent = formatted;
                    }
                    highlightJSON(codeElement);
                } catch (e) {
                    console.error('Failed to format JSON:', e);
                }
            }
        });
        
        formatRawBtn.addEventListener('click', () => {
            if (currentRequestData) {
                const bodyContent = document.getElementById('body-content');
                const bodyContentText = document.getElementById('body-content-text');
                const codeElement = bodyContent.querySelector('code') || bodyContent;
                codeElement.textContent = currentRequestData.body;
                if (bodyContentText) {
                    bodyContentText.textContent = currentRequestData.body;
                }
            }
        });
    }
});
