// Injected via page.add_init_script() BEFORE the DLS Flutter app's own
// scripts run, so it sees every WebSocket the app creates - including the
// WAMP connection to wss://connectanum.dls-gmbh.biz/wamp, which is what we
// actually care about (the "connectanum" substring check below).
//
// Why this exists at all: the portal's WAMP-CRA login signature (PBKDF2 +
// HMAC-SHA256 over a server challenge) couldn't be reproduced outside a
// real browser despite having a known-good example to check against - so
// instead of re-implementing the WAMP client, this just rides along on the
// browser's own, already-correct, already-authenticated connection and
// injects additional CALL messages onto it directly.
(function () {
  window.__wampReqId = 10000;
  window.__wampPending = {};
  window.__wampReady = false;
  window.__wampLastError = null;

  const OrigWebSocket = window.WebSocket;

  function PatchedWebSocket(url, protocols) {
    const ws = new OrigWebSocket(url, protocols);
    if (typeof url === "string" && url.includes("connectanum")) {
      window.__ws = ws;
      ws.addEventListener("message", function (ev) {
        try {
          const msg = JSON.parse(ev.data);
          const type = msg[0];
          if (type === 2) {
            // WELCOME
            window.__wampReady = true;
          } else if (type === 3) {
            // ABORT (auth failed etc.)
            window.__wampLastError = msg;
          } else if (type === 50 || type === 8) {
            // RESULT or ERROR - both carry the request id as msg[1]
            const reqId = msg[1];
            window.__wampPending[reqId] = msg;
          }
        } catch (e) {
          // not JSON / not something we care about - ignore
        }
      });
      ws.addEventListener("close", function () {
        window.__wampReady = false;
      });
    }
    return ws;
  }
  PatchedWebSocket.prototype = OrigWebSocket.prototype;
  PatchedWebSocket.CONNECTING = OrigWebSocket.CONNECTING;
  PatchedWebSocket.OPEN = OrigWebSocket.OPEN;
  PatchedWebSocket.CLOSING = OrigWebSocket.CLOSING;
  PatchedWebSocket.CLOSED = OrigWebSocket.CLOSED;
  window.WebSocket = PatchedWebSocket;

  // Call a WAMP procedure on the already-authenticated connection and
  // resolve with its RESULT (or reject with its ERROR/a timeout).
  window.__wampCall = function (procedure, args, kwargs) {
    return new Promise(function (resolve, reject) {
      if (!window.__ws || !window.__wampReady) {
        reject({ error: "not_connected" });
        return;
      }
      const reqId = window.__wampReqId++;
      window.__wampPending[reqId] = null;
      window.__ws.send(JSON.stringify([48, reqId, {}, procedure, args || [], kwargs || {}]));
      let elapsed = 0;
      const interval = setInterval(function () {
        const result = window.__wampPending[reqId];
        if (result) {
          clearInterval(interval);
          delete window.__wampPending[reqId];
          if (result[0] === 8) reject(result);
          else resolve(result);
          return;
        }
        elapsed += 100;
        if (elapsed > 15000) {
          clearInterval(interval);
          delete window.__wampPending[reqId];
          reject({ error: "timeout", procedure: procedure });
        }
      }, 100);
    });
  };
})();
