// router_poll.js — log Marvin's AirLink cellular signal during a latency run (2026-10-15).
//
// Run inside the ACEmanager tab AFTER the user has logged in (reach it with
// `ssh -L 9443:192.168.13.31:9443 dinosaur@100.93.121.3`, then https://localhost:9443/).
// It reuses that tab's login session; it never handles the password.
//
// 1. Open Status -> Cellular once and note which request returns the RSRP/SINR
//    values (DevTools Network tab, or the Chrome extension's network reader).
// 2. Paste this file into the console (or javascript_tool), then:
//      __routerPoll.start('/path/of/that/request')       // poll every 5 s
//      __routerPoll.csv()                                 // CSV text for analyze_latency.py --router
//      __routerPoll.stop()
// Requests go one at a time: the router's web server returns 503 on parallel
// requests. Each poll travels back over Marvin's cellular upload, so keep the
// interval >= 5 s (a few KB per poll).
(() => {
  const P = window.__routerPoll || {};
  P.rows = P.rows || [];
  P.everyMs = 5000;
  // Regexes run on the response text (HTML, XML or JSON). Adjust after seeing the response.
  P.fields = {
    rsrp: /RSRP(?:<[^>]*>|[^-\d<]){0,80}(-?\d+(?:\.\d+)?)/i,
    rsrq: /RSRQ(?:<[^>]*>|[^-\d<]){0,80}(-?\d+(?:\.\d+)?)/i,
    sinr: /SINR(?:<[^>]*>|[^-\d<]){0,80}(-?\d+(?:\.\d+)?)/i,
    rssi: /RSSI(?:<[^>]*>|[^-\d<]){0,80}(-?\d+(?:\.\d+)?)/i,
    cell: /Cell\s*ID(?:<[^>]*>|[^\w<]){0,80}([0-9A-Fa-f]{2,})/i,
    band: /\bBand(?:<[^>]*>|[^\w<]){0,80}(\d+)/i,
    tech: /\b(LTE-A(?: Pro)?|LTE|5G NR|NR5G|NSA|SA|UMTS|HSPA\+?)\b/,
  };
  let timer = null;
  let busy = false;

  async function pollOnce() {
    if (busy) return;  // never overlap requests
    busy = true;
    const row = { wall: (Date.now() / 1000).toFixed(2) };
    try {
      const r = await fetch(P.url, { credentials: 'include', cache: 'no-store' });
      const text = await r.text();
      row.http = r.status;
      for (const [k, re] of Object.entries(P.fields)) {
        const m = text.match(re);
        row[k] = m ? m[1] : '';
      }
      P.lastText = text.slice(0, 4000);  // for checking the regexes
    } catch (e) {
      row.http = 'err';
      row.error = String(e).slice(0, 80);
    }
    P.rows.push(row);
    busy = false;
  }

  P.start = (url, everyMs) => {
    P.stop();
    P.url = url;
    if (everyMs) P.everyMs = Math.max(5000, everyMs);
    pollOnce();
    timer = setInterval(pollOnce, P.everyMs);
    return `polling ${url} every ${P.everyMs} ms`;
  };
  P.stop = () => { if (timer) clearInterval(timer); timer = null; return `${P.rows.length} rows`; };
  P.csv = () => {
    const cols = ['wall', 'http', ...Object.keys(P.fields), 'error'];
    return [cols.join(',')]
      .concat(P.rows.map(r => cols.map(c => (r[c] ?? '').toString().replace(/,/g, ';')).join(',')))
      .join('\n');
  };
  P.last = () => P.rows[P.rows.length - 1];
  window.__routerPoll = P;
  return 'router poller loaded';
})();
