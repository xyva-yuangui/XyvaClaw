#!/usr/bin/env node
/**
 * xyvaClaw Install Telemetry Collector
 * =====================================
 * Lightweight server to track anonymous install counts.
 * 
 * Deploy this on any server (e.g. your VPS, Vercel, Railway, etc.)
 * 
 * Usage:
 *   node telemetry-server.js                    # Default port 9600
 *   PORT=8080 node telemetry-server.js          # Custom port
 * 
 * Data stored in: ./telemetry-data.json
 * 
 * Endpoints:
 *   POST /v1/setup-complete   — Record an install event
 *   GET  /v1/stats            — View install statistics (protected by ADMIN_KEY)
 */

const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = parseInt(process.env.PORT || '9600', 10);
const ADMIN_KEY = process.env.ADMIN_KEY || '';
const DATA_FILE = path.join(__dirname, 'telemetry-data.json');

function loadData() {
  try {
    return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
  } catch {
    return { total: 0, daily: {}, os: {}, versions: {}, events: [] };
  }
}

function saveData(data) {
  fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2));
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

const server = http.createServer((req, res) => {
  // CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    return res.end();
  }

  // POST /v1/setup-complete
  if (req.method === 'POST' && req.url === '/v1/setup-complete') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      try {
        const payload = body ? JSON.parse(body) : {};
        const data = loadData();

        const day = today();
        data.total++;
        data.daily[day] = (data.daily[day] || 0) + 1;

        const os = payload.os || 'unknown';
        data.os[os] = (data.os[os] || 0) + 1;

        if (payload.v) {
          data.versions[payload.v] = (data.versions[payload.v] || 0) + 1;
        }

        // Keep last 1000 events for debugging
        data.events.push({
          t: new Date().toISOString(),
          os,
          v: payload.v || '',
          mode: payload.mode || '',
        });
        if (data.events.length > 1000) {
          data.events = data.events.slice(-1000);
        }

        saveData(data);

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: true }));
      } catch {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: true }));
      }
    });
    return;
  }

  // GET /v1/stats
  if (req.method === 'GET' && req.url.startsWith('/v1/stats')) {
    const auth = req.headers['authorization'] || '';
    if (auth !== `Bearer ${ADMIN_KEY}`) {
      res.writeHead(401, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({ error: 'unauthorized' }));
    }

    const data = loadData();
    res.writeHead(200, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify({
      total_installs: data.total,
      by_os: data.os,
      by_version: data.versions,
      last_7_days: Object.fromEntries(
        Array.from({ length: 7 }, (_, i) => {
          const d = new Date();
          d.setDate(d.getDate() - i);
          const key = d.toISOString().slice(0, 10);
          return [key, data.daily[key] || 0];
        })
      ),
      recent_events: (data.events || []).slice(-20),
    }, null, 2));
  }

  // Health check
  if (req.url === '/health') {
    res.writeHead(200);
    return res.end('ok');
  }

  res.writeHead(404);
  res.end('not found');
});

server.listen(PORT, () => {
  console.log(`Telemetry collector running on port ${PORT}`);
  if (ADMIN_KEY) console.log(`Stats endpoint: http://localhost:${PORT}/v1/stats (use ADMIN_KEY env var)`);
});
