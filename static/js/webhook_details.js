console.log('Initializing socket.io connection...');
const socket = io({
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 1000,
    timeout: 20000
});

socket.on('connect', function() {
    console.log('Socket.IO Connected!');
});

socket.on('connect_error', function(error) {
    console.error('Socket.IO Connection Error:', error);
});

socket.on('disconnect', function(reason) {
    console.log('Socket.IO Disconnected:', reason);
    if (reason === 'io server disconnect') {
        // Reconnect after a short delay
        setTimeout(() => {
            socket.connect();
        }, 1000);
    }
});

const webhookId = document.body.dataset.webhookId;
socket.on('new_webhook_request', function(data) {
    console.log('Received new_webhook_request event:', data);
    
    // Only process if this is for the current webhook
    if (data.webhook_id && data.webhook_id.toString() === webhookId) {
        console.log('New request for current webhook, reloading...');
        
        // Add a small delay to ensure the background job is complete
        setTimeout(() => {
            location.reload();
        }, 300);
    } else {
        console.log('Request is for a different webhook, ignoring...');
    }
});

// Debug: Log all socket events
const onevent = socket.onevent;
socket.onevent = function (packet) {
    const args = packet.data || [];
    onevent.call(this, packet);
    socket.emit('args', args);
};

socket.on('args', function(args) {
    console.log('Socket event received:', args);
});

/* JS code to fetch all the requests from the backend database and display them on the request details page */

function showRequest(requestId) {
    fetch(`/webhook/request/${requestId}`)
        .then(response => response.json())
        .then(data => {
            const details = document.getElementById('request-details');
            details.innerHTML = `
                        <sl-details summary="Headers">
                            <span id="header-json"><pre>${JSON.stringify(data.headers, null, 2)}</pre></span>
                            <sl-copy-button from="header-json"></sl-copy-button>
                        </sl-details>
                        <sl-details summary="Body" open>
                            <span id="body-json"><pre>${data.body}</pre></span>
                            <sl-copy-button from="body-json"></sl-copy-button>
                        </sl-details>
                        <h3>Timestamp</h3>
                        <pre>${data.timestamp}</pre>
                    `;
        });
}

/* change background color of a request block when it is clicked */

const lis = document.querySelectorAll("li");

lis.forEach(function (li) {
    li.addEventListener("click", function () {
        if (li.style.backgroundColor === '#81e8ff') {
            li.style.backgroundColor = "";
        } else {
            lis.forEach(function (otherLi) {
                if (otherLi !== li) {
                    otherLi.style.backgroundColor = "";
                }
            });
            li.style.backgroundColor = "#81e8ff";
        }
    });
});

/* apply backgournd color to first request block when the details page opens
window.onload = function () {
    document.querySelectorAll("li")[0].style.backgroundColor = "#81e8ff";
};
*/
/* JS code resposible to deleting a request from the request details page */
document.addEventListener('DOMContentLoaded', function () {
    // Get all trash icons
    const trashIcons = document.querySelectorAll('.deleteRequest');

    // Add event listener to each trash icon
    trashIcons.forEach(icon => {
        icon.addEventListener('click', function (event) {
            // Prevent default action
            event.preventDefault();

            // Find the closest 'req' div and remove it
            const reqDiv = icon.closest('.req');
            const close_li = reqDiv.querySelector('li.request-item').getAttribute("onclick").match(/\(([^)]+)\)/)[1]; /* getting the id from the function parameter defined in onclick attribute of each li element*/
            fetch('/delete_request', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ id: close_li })
            }).then(response => {
                if (response.ok) {
                    reqDiv.remove();
                    
                }
            });
           // location.reload();
        });
    });

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
                    // Refresh the page to show the updated list
                    location.reload();
                }
            })
            .finally(() => {
                deleteAllDialog.hide();
            });
        });
    }
});                


/* JS code to handle search functionality on the request details page */

const searchBox = document.getElementById('searchBox');
if (searchBox) {
    searchBox.addEventListener('input', function () {
        var filter = this.value.toLowerCase();
        var items = document.querySelectorAll('li');

        items.forEach(function (item) {
            if (item.textContent.toLowerCase().includes(filter)) {
                item.classList.remove('hidden');
            } else {
                item.classList.add('hidden');
            }
        });
    });
}