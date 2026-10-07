(() => {
    const statusBox = document.getElementById('riderOfflineStatus');
    if (!statusBox || !window.indexedDB) return;

    const databaseName = 'jaunpur-rider-offline-v1';
    const storeName = 'pending-updates';
    const endpoint = statusBox.dataset.endpoint;

    function openDatabase() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(databaseName, 1);
            request.onupgradeneeded = () => request.result.createObjectStore(storeName, { keyPath: 'id' });
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async function withStore(mode, callback) {
        const db = await openDatabase();
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(storeName, mode);
            const store = transaction.objectStore(storeName);
            const result = callback(store);
            transaction.oncomplete = () => { db.close(); resolve(result && result.result); };
            transaction.onerror = () => { db.close(); reject(transaction.error); };
            transaction.onabort = () => { db.close(); reject(transaction.error); };
        });
    }

    async function getPending() {
        const db = await openDatabase();
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(storeName, 'readonly');
            const request = transaction.objectStore(storeName).getAll();
            request.onsuccess = () => resolve(request.result.sort((a, b) => a.createdAt - b.createdAt));
            request.onerror = () => reject(request.error);
            transaction.oncomplete = () => db.close();
        });
    }

    function announce(text, isError = false) {
        statusBox.textContent = text;
        statusBox.classList.toggle('is-error', isError);
        statusBox.classList.add('is-visible');
    }

    async function updateQueueMessage() {
        try {
            const pending = await getPending();
            if (pending.length) {
                announce(`${pending.length} delivery update(s) waiting to sync. Keep this page open while reconnecting.`);
            } else {
                announce(navigator.onLine ? 'Connected. Offline capture is ready if the network drops.' : 'You are offline. Delivery updates will be saved on this device.');
            }
        } catch (error) {
            announce('Offline storage is unavailable in this browser. Keep the page open and restore the connection before submitting.', true);
        }
    }

    function payloadFrom(form, submitter) {
        const formData = new FormData(form, submitter);
        const proof = formData.get('proof_photo');
        return {
            id: (window.crypto && crypto.randomUUID) ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`,
            assignmentId: formData.get('assignment_id'),
            action: formData.get('action'),
            csrfToken: formData.get('csrfmiddlewaretoken'),
            deliveredTo: formData.get('delivered_to') || '',
            note: formData.get('note') || '',
            proof: proof && proof.size ? proof : null,
            proofName: proof && proof.name ? proof.name : 'delivery-proof.jpg',
            createdAt: Date.now(),
        };
    }

    async function saveOffline(payload) {
        await withStore('readwrite', store => store.put(payload));
        await updateQueueMessage();
    }

    async function sendPayload(payload) {
        const formData = new FormData();
        formData.append('csrfmiddlewaretoken', payload.csrfToken);
        formData.append('assignment_id', payload.assignmentId);
        formData.append('action', payload.action);
        formData.append('delivered_to', payload.deliveredTo);
        formData.append('note', payload.note);
        if (payload.proof) formData.append('proof_photo', payload.proof, payload.proofName);
        const response = await fetch(endpoint, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'X-Rider-Offline-Sync': '1' },
            body: formData,
        });
        if (!response.headers.get('content-type')?.includes('application/json')) {
            throw new Error('Your rider session may have expired. Sign in again before syncing saved updates.');
        }
        const result = await response.json();
        if (!response.ok || !result.accepted) throw new Error(result.error || 'The server did not accept this delivery update. Review it and try again.');
    }

    async function syncPending() {
        if (!navigator.onLine) return;
        let completed = 0;
        try {
            const pending = await getPending();
            for (const payload of pending) {
                try {
                    await sendPayload(payload);
                    await withStore('readwrite', store => store.delete(payload.id));
                    completed += 1;
                } catch (error) {
                    announce(error.message, true);
                    break;
                }
            }
            if (completed) {
                announce(`${completed} saved delivery update(s) synced successfully.`);
                window.setTimeout(() => window.location.reload(), 900);
            } else {
                await updateQueueMessage();
            }
        } catch (error) {
            announce('Could not read the offline queue. Keep this page open and try again.', true);
        }
    }

    document.querySelectorAll('.rider-update-form').forEach(form => {
        form.addEventListener('submit', async event => {
            event.preventDefault();
            const payload = payloadFrom(form, event.submitter);
            if (payload.action === 'delivered' && !payload.deliveredTo.trim()) {
                announce('Enter who received the order before confirming delivery.', true);
                return;
            }
            if (payload.action === 'failed' && !payload.note.trim()) {
                announce('Add a short note about the failed attempt.', true);
                return;
            }
            if (payload.proof && payload.proof.size > 5 * 1024 * 1024) {
                announce('Choose a proof photo smaller than 5 MB.', true);
                return;
            }
            if (!navigator.onLine) {
                await saveOffline(payload);
                announce('Saved on this device. It will sync when the connection returns. Keep this page open.', false);
                return;
            }
            try {
                await sendPayload(payload);
                announce('Delivery update saved. Refreshing your route…');
                window.location.reload();
            } catch (error) {
                if (error instanceof TypeError || !navigator.onLine) {
                    await saveOffline(payload);
                    announce('Connection dropped. Update saved on this device for later sync. Keep this page open.', false);
                } else {
                    announce(error.message, true);
                }
            }
        });
    });

    window.addEventListener('online', syncPending);
    window.addEventListener('offline', updateQueueMessage);
    updateQueueMessage().then(syncPending);
    if ('serviceWorker' in navigator && document.currentScript) {
        const workerUrl = new URL('rider-sw.js', document.currentScript.src);
        navigator.serviceWorker.register(workerUrl).catch(() => {});
    }
})();
