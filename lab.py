"""Independent, synthetic agent integration demonstrations. Python 3.10+, stdlib only."""
import argparse, hashlib, json, sqlite3, tempfile, threading, urllib.request, subprocess, sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Ledger:
    def __init__(self, path):
        self.path = str(path)
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS actions (
              tenant TEXT, action_id TEXT, digest TEXT, status TEXT, receipt TEXT,
              PRIMARY KEY (tenant, action_id));
            CREATE TABLE IF NOT EXISTS deliveries (
              tenant TEXT, key TEXT, body TEXT, PRIMARY KEY (tenant, key));
            CREATE TABLE IF NOT EXISTS calls (
              tenant TEXT, call_id TEXT, phase INTEGER, transfer TEXT,
              PRIMARY KEY (tenant, call_id));
            CREATE TABLE IF NOT EXISTS events (
              tenant TEXT, call_id TEXT, event TEXT, PRIMARY KEY(tenant,call_id,event));
            ''')

    def connect(self):
        return sqlite3.connect(self.path, timeout=5, isolation_level='IMMEDIATE')

    def approve(self, tenant, action_id, args):
        digest = hashlib.sha256(json.dumps(args, sort_keys=True).encode()).hexdigest()
        with self.connect() as db:
            existing = db.execute('SELECT digest FROM actions WHERE tenant=? AND action_id=?', (tenant, action_id)).fetchone()
            if existing and existing[0] != digest:
                raise ValueError('action ID already bound to different arguments')
            db.execute('INSERT OR IGNORE INTO actions VALUES (?,?,?,"approved",NULL)', (tenant, action_id, digest))

    def execute(self, tenant, action_id, args, url, simulate_lost_response=False):
        digest = hashlib.sha256(json.dumps(args, sort_keys=True).encode()).hexdigest()
        with self.connect() as db:
            row = db.execute('SELECT digest,status,receipt FROM actions WHERE tenant=? AND action_id=?', (tenant, action_id)).fetchone()
        if not row or row[0] != digest:
            return {'status': 'denied', 'reason': 'approval missing or arguments changed'}
        if row[1] == 'succeeded':
            return {'status': 'succeeded', 'receipt': row[2], 'replayed': True}
        # The demo downstream honors a tenant-scoped idempotency key. This is a
        # required contract, not a claim that arbitrary third-party APIs do so.
        req = urllib.request.Request(url, data=json.dumps(args, sort_keys=True).encode(), headers={
            'Content-Type': 'application/json', 'X-Demo-Tenant': tenant,
            'Idempotency-Key': action_id}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=3) as response:
                result = json.load(response)
        except (OSError, ValueError):
            return {'status': 'unknown', 'reason': 'no validated downstream receipt; reconcile before claiming success'}
        if simulate_lost_response:
            return {'status': 'unknown', 'reason': 'response deliberately dropped after downstream commit'}
        if result.get('status') != 'succeeded' or not isinstance(result.get('receipt'), str) or not result['receipt']:
            return {'status': 'unknown', 'reason': 'invalid downstream receipt'}
        with self.connect() as db:
            db.execute('UPDATE actions SET status="succeeded",receipt=? WHERE tenant=? AND action_id=?', (result['receipt'], tenant, action_id))
        return {'status': 'succeeded', 'receipt': result['receipt'], 'replayed': False}

    def webhook(self, tenant, payload):
        # tenant must come from the authenticated route, not user-supplied metadata.
        event = payload.get('event')
        call = payload.get('call')
        valid = {'call_started': 1, 'call_ended': 2, 'call_analyzed': 3,
                 'transfer_started': 0, 'transfer_bridged': 0, 'transfer_cancelled': 0}
        if event not in valid or not isinstance(call, dict) or not isinstance(call.get('call_id'), str) or not call['call_id']:
            raise ValueError('invalid supported event envelope')
        call_id = call['call_id']
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            inserted = db.execute('INSERT OR IGNORE INTO events VALUES (?,?,?)', (tenant, call_id, event)).rowcount
            db.execute('INSERT OR IGNORE INTO calls VALUES (?,?,0,"none")', (tenant, call_id))
            if inserted:
                db.execute('UPDATE calls SET phase=MAX(phase,?) WHERE tenant=? AND call_id=?', (valid[event], tenant, call_id))
                if event.startswith('transfer_'):
                    # A late "started" must not replace an observed bridge/cancel.
                    current = db.execute('SELECT transfer FROM calls WHERE tenant=? AND call_id=?', (tenant, call_id)).fetchone()[0]
                    if event != 'transfer_started' or current == 'none':
                        db.execute('UPDATE calls SET transfer=? WHERE tenant=? AND call_id=?', (event, tenant, call_id))
            row = db.execute('SELECT phase,transfer FROM calls WHERE tenant=? AND call_id=?', (tenant, call_id)).fetchone()
        return {'phase': row[0], 'transfer': row[1], 'duplicate': not bool(inserted)}


def verify_outcome(case):
    """Structured trace assertion, not a natural-language or audio-quality judge."""
    errors = []
    if case['claim'] == 'completed':
        receipt = case.get('tool_receipt') or {}
        if receipt.get('status') != 'succeeded' or not receipt.get('id'):
            errors.append('completion has no successful tool receipt')
        if receipt.get('tenant') != case['tenant']:
            errors.append('receipt is not bound to the current tenant')
        if receipt.get('action') != case['action']:
            errors.append('receipt belongs to another action')
    if case.get('requires_approval') and not case.get('approved') and case.get('executed'):
        errors.append('side effect executed before approval')
    if case.get('transfer_claim') == 'connected' and case.get('transfer_event') != 'transfer_bridged':
        errors.append('human connection claimed without a bridged event')
    return errors


def downstream_server(ledger):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_POST(self):
            if self.path != '/deliver':
                self.send_error(404); return
            size = int(self.headers.get('Content-Length', '0'))
            if size > 10000:
                self.send_error(413); return
            raw = self.rfile.read(size).decode()
            tenant = self.headers.get('X-Demo-Tenant')
            key = self.headers.get('Idempotency-Key')
            if not tenant or not key:
                self.send_error(400); return
            with ledger.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                prior = db.execute('SELECT body FROM deliveries WHERE tenant=? AND key=?', (tenant, key)).fetchone()
                if prior and prior[0] != raw:
                    self.send_error(409); return
                db.execute('INSERT OR IGNORE INTO deliveries VALUES (?,?,?)', (tenant, key, raw))
            result = json.dumps({'status': 'succeeded', 'receipt': hashlib.sha256((tenant + ':' + key).encode()).hexdigest()[:20]}).encode()
            self.send_response(200); self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(result))); self.end_headers(); self.wfile.write(result)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def run_demo():
    results = []
    group = 'receipts'
    def check(name, actual, expected):
        results.append({'demo': group, 'case': name, 'actual': actual, 'expected': expected, 'pass': actual == expected})
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp)/'ledger.sqlite'
        ledger = Ledger(path)
        server = downstream_server(ledger)
        endpoint = f'http://127.0.0.1:{server.server_port}/deliver'
        try:
            args = {'ticket': 'synthetic-ticket-1', 'reply': 'Synthetic draft'}
            check('unapproved action blocked', ledger.execute('a','send-1',args,endpoint)['status'], 'denied')
            ledger.approve('a','send-1',args)
            check('cross-tenant approval blocked', ledger.execute('b','send-1',args,endpoint)['status'], 'denied')
            check('changed arguments blocked', ledger.execute('a','send-1',{'reply':'changed'},endpoint)['status'], 'denied')
            check('lost response remains unknown', ledger.execute('a','send-1',args,endpoint,True)['status'], 'unknown')
            child = subprocess.check_output([sys.executable, '-c',
                'import json,sys; from lab import Ledger; print(json.dumps(Ledger(sys.argv[1]).execute("a","send-1",json.loads(sys.argv[2]),sys.argv[3])))',
                str(path), json.dumps(args), endpoint], cwd=Path(__file__).parent, text=True)
            check('fresh process retries and obtains receipt', json.loads(child)['status'], 'succeeded')
            ledger = Ledger(path)
            check('replay returns stored receipt', ledger.execute('a','send-1',args,endpoint)['replayed'], True)
            with ledger.connect() as db:
                check('one downstream effect after ambiguous retry', db.execute('SELECT COUNT(*) FROM deliveries').fetchone()[0], 1)
            group = 'webhooks'
            for e in ['call_analyzed','call_started','call_ended','call_ended']:
                state = ledger.webhook('a',{'event':e,'call':{'call_id':'synthetic-call'}})
            check('late start never regresses analyzed state', state['phase'], 3)
            check('duplicate end deduplicated', state['duplicate'], True)
            check('other tenant has independent call state', ledger.webhook('b',{'event':'call_started','call':{'call_id':'synthetic-call'}})['phase'], 1)
            check('failed call can end without start', ledger.webhook('a',{'event':'call_ended','call':{'call_id':'never-connected'}})['phase'], 2)
            ledger.webhook('a',{'event':'transfer_cancelled','call':{'call_id':'synthetic-call'}})
            check('late transfer start does not imply connection', ledger.webhook('a',{'event':'transfer_started','call':{'call_id':'synthetic-call'}})['transfer'], 'transfer_cancelled')
            group = 'outcomes'
            cases = json.loads((Path(__file__).parent/'demos/outcome-cases.json').read_text())
            for case in cases:
                errors = verify_outcome(case)
                check(case['id'], bool(errors), case['should_flag'])
            # Broken baseline accepts a completed claim based only on its wording.
            unsafe = [c for c in cases if c['should_flag']]
            results.append({'demo':'outcomes','case':'broken baseline misses unsafe traces', 'missed':sum(c['claim']=='completed' for c in unsafe), 'unsafe_cases':len(unsafe), 'note':'Intentionally weak baseline; not measured model performance.'})
        finally:
            server.shutdown(); server.server_close()
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output', default='reports/results.json')
    parser.add_argument('--demo',choices=['all','receipts','webhooks','outcomes'],default='all')
    args = parser.parse_args(); rows = run_demo()
    rows = [r for r in rows if args.demo == 'all' or r['demo'] == args.demo]
    output = Path(args.output); output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({'scope':'Synthetic local HTTP + SQLite integration and deterministic trace checks; no hosted vendor APIs or live model calls.', 'results':rows},indent=2))
    checks = [r for r in rows if 'pass' in r]
    print(f'{sum(r["pass"] for r in checks)}/{len(checks)} assertions passed; report: {output}')
    raise SystemExit(0 if all(r['pass'] for r in checks) else 1)
