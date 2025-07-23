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

// Handle new webhook request notifications
socket.on('new_webhook_request', function(data) {
    console.log('Received new_webhook_request event:', data);
    
    // Update the request count for the specific webhook
    const webhookElement = document.querySelector(`a[href*="${data.webhook_id}"]`);
    if (webhookElement) {
        const countElement = webhookElement.parentElement.querySelector('.request-count');
        if (countElement) {
            const currentCount = parseInt(countElement.textContent) || 0;
            countElement.textContent = currentCount + 1;
        }
        
        // If we're on the details page for this webhook, reload it
        const currentPath = window.location.pathname.split('/').pop();
        if (currentPath === data.webhook_id) {
            console.log('Reloading details page...');
            location.reload();
        }
    } else {
        // If we can't find the specific element, just reload the whole page
        console.log('Reloading page to show new request...');
        location.reload();
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

/* JS code to handle opening and closing of webhook generator dialog */

function openPopup() {
    document.querySelector('.dialog-overview').show();
}

function closePopup() {
    document.querySelector('.dialog-overview').hide();
    location.reload();
}

/* JS code to generate a webhook by taking name from user and send the data to backend to register a new webhook in the database */

function generateWebhook() {
    const name = document.getElementById('webhook-name').value;
    if (name) {
        fetch('/add_webhook', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name })
        })
            .then(response => response.json())
            .then(data => {
                document.getElementById('webhook-url').textContent = `Name: ${data.name}, URL: ${data.url}`;
                // Add the new webhook to the list
                const newItem = document.createElement('li');
                newItem.className = 'webhook-item';
                newItem.innerHTML = `<a href="${data.url}" target="_blank">${data.name} - ${data.url}</a>`;
                document.getElementById('webhook-list').appendChild(newItem);
            });
    } else {
        alert("Please enter a name for the webhook.");
    }
}

/* JS code to handle search functionality on the main index page */

document.getElementById('searchBox').addEventListener('input', function () {
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

const deleteDialog = document.querySelector('.delete-dialog');
const pauseAlert = document.querySelector(`sl-alert[variant="warning"]`);
const deleteAlert = document.querySelector(`sl-alert[variant="danger"]`);
const activatedAlert = document.querySelector(`sl-alert[variant="success"]`);

/* JS code to handle deletion of a webhook; detect when trash icon is clicked and then send a delete request to the backend with the webhook URL path as payload */

document.querySelectorAll('#delete-webhook').forEach(function (element) {
    element.addEventListener('click', function () {
        webhookItemToDelete = element.closest('.webhook-item');
        deleteDialog.show();
    });
});

document.querySelector('.confirm-delete').addEventListener('click', function () {
    if (webhookItemToDelete) {
        const webhookHref = webhookItemToDelete.querySelector('.webhook-link').getAttribute('href');

        fetch('/delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: webhookHref })
        }).then(response => {
            if (response.ok) {
                webhookItemToDelete.remove();
                deleteDialog.hide();
                deleteAlert.toast();
            }
        });
    }
});

document.querySelector('.cancel-delete').addEventListener('click', function () {
    deleteDialog.hide();
});

/* JS code to handle pausing of a webhook; detect when pause icon is clicked and then send a pause request to the backend with the webhook URL path as payload */

document.querySelectorAll('#pause-webhook').forEach(function (element) {
    element.addEventListener('click', function () {
        const webhookItem = element.closest('.webhook-item');
        const webhookHref = webhookItem.querySelector('.webhook-link').getAttribute('href');

        fetch('/pause', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: webhookHref })
        }).then(response => response.json())
            .then(data => {
                if (data.status !== undefined) {
                    if (data.status) {
                        element.setAttribute('variant', 'warning');
                        element.querySelector('sl-icon').setAttribute('name', 'pause');
                        activatedAlert.toast();
                    } else {
                        element.setAttribute('variant', 'success');
                        element.querySelector('sl-icon').setAttribute('name', 'play');
                        pauseAlert.toast();
                    }
                }
            });
    });
});