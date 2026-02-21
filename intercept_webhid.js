/*
 * INTERCEPT WebHID commands from the X68PRO HE web driver.
 *
 * ISTRUZIONI:
 * 1. Apri il web driver della tastiera nel browser (Chrome/Edge)
 * 2. Premi F12 per aprire DevTools
 * 3. Vai alla tab "Console"
 * 4. Incolla TUTTO questo script e premi Enter
 * 5. Ora attiva il toggle "Simulation" nel web driver
 * 6. Lo script loggerà TUTTI i comandi inviati/ricevuti
 */

(function() {
    console.log('%c=== WebHID Interceptor for X68PRO HE ===', 'color: #00ff88; font-size: 16px; font-weight: bold;');
    console.log('%cListening for ALL WebHID traffic...', 'color: #ffcc00;');

    const logs = [];

    function hexDump(buffer) {
        const arr = new Uint8Array(buffer instanceof ArrayBuffer ? buffer : buffer.buffer);
        return Array.from(arr).map(b => b.toString(16).padStart(2, '0')).join(' ');
    }

    function logEntry(type, reportId, data) {
        const hex = hexDump(data);
        const timestamp = performance.now().toFixed(1);
        const entry = { type, reportId, hex, timestamp, raw: Array.from(new Uint8Array(data instanceof ArrayBuffer ? data : data.buffer)) };
        logs.push(entry);

        const colors = {
            'SEND_REPORT': 'color: #ff4444; font-weight: bold;',
            'SEND_FEATURE': 'color: #ff8800; font-weight: bold;',
            'RECV_FEATURE': 'color: #44ff44; font-weight: bold;',
            'INPUT_REPORT': 'color: #4488ff;',
        };
        console.log(`%c[${timestamp}ms] ${type} (ID=${reportId}, ${hex.split(' ').length} bytes)`, colors[type] || 'color: white;');
        console.log(`  ${hex}`);

        // Highlight non-zero bytes
        const arr = Array.from(new Uint8Array(data instanceof ArrayBuffer ? data : data.buffer));
        const nonZero = arr.reduce((acc, v, i) => { if (v !== 0) acc.push(`[${i}]=${v}`); return acc; }, []);
        if (nonZero.length > 0 && nonZero.length < 30) {
            console.log(`  Non-zero: ${nonZero.join(', ')}`);
        }
    }

    // Patch all existing HID devices
    function patchDevice(device) {
        console.log(`%cPatching device: ${device.productName} (VID:0x${device.vendorId.toString(16)} PID:0x${device.productId.toString(16)})`, 'color: #00ccff;');
        for (const col of device.collections) {
            console.log(`  Collection: UsagePage=0x${col.usagePage.toString(16)} Usage=0x${col.usage.toString(16)}`);
        }

        // Intercept sendReport
        const origSendReport = device.sendReport.bind(device);
        device.sendReport = async function(reportId, data) {
            logEntry('SEND_REPORT', reportId, data);
            return origSendReport(reportId, data);
        };

        // Intercept sendFeatureReport
        const origSendFeature = device.sendFeatureReport.bind(device);
        device.sendFeatureReport = async function(reportId, data) {
            logEntry('SEND_FEATURE', reportId, data);
            return origSendFeature(reportId, data);
        };

        // Intercept receiveFeatureReport
        const origRecvFeature = device.receiveFeatureReport.bind(device);
        device.receiveFeatureReport = async function(reportId) {
            const result = await origRecvFeature(reportId);
            logEntry('RECV_FEATURE', reportId, result.buffer);
            return result;
        };

        // Listen for input reports
        device.addEventListener('inputreport', (event) => {
            logEntry('INPUT_REPORT', event.reportId, event.data.buffer);
        });
    }

    // Patch navigator.hid.requestDevice to catch new connections
    const origRequest = navigator.hid.requestDevice.bind(navigator.hid);
    navigator.hid.requestDevice = async function(options) {
        console.log('%cWebHID requestDevice called', 'color: #ffcc00;', options);
        const devices = await origRequest(options);
        for (const d of devices) patchDevice(d);
        return devices;
    };

    // Patch already-connected devices
    navigator.hid.getDevices().then(devices => {
        console.log(`%cFound ${devices.length} already-connected HID device(s)`, 'color: #00ccff;');
        for (const d of devices) {
            patchDevice(d);
            // If device is already opened, great. If not, patch open too.
            const origOpen = d.open.bind(d);
            d.open = async function() {
                console.log(`%cDevice opened: ${d.productName}`, 'color: #00ff88;');
                const result = await origOpen();
                return result;
            };
        }
    });

    // Export logs for easy copy
    window.__webhid_logs = logs;
    window.__webhid_export = function() {
        const json = JSON.stringify(logs, null, 2);
        console.log('%cExporting logs...', 'color: #ffcc00;');
        console.log(json);
        // Also copy to clipboard
        navigator.clipboard.writeText(json).then(() => {
            console.log('%cLogs copied to clipboard!', 'color: #00ff88; font-weight: bold;');
        }).catch(() => {
            console.log('%cClipboard copy failed. Use copy(JSON.stringify(__webhid_logs, null, 2))', 'color: #ff4444;');
        });
        return json;
    };

    console.log('%c\nREADY! Now toggle "Simulation" in the web driver.', 'color: #00ff88; font-size: 14px;');
    console.log('%cAfter done, run: __webhid_export() to get all captured commands.', 'color: #ffcc00;');
    console.log('%cOr access window.__webhid_logs directly.', 'color: #888;');
})();
