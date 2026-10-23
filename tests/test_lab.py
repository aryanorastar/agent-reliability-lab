import json, tempfile, unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from lab import Ledger, run_demo

class IntegrationTests(unittest.TestCase):
    def test_demo_acceptance(self):
        self.assertTrue(all(x['pass'] for x in run_demo() if 'pass' in x))

    def test_concurrent_webhook_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger=Ledger(Path(tmp)/'state.sqlite')
            payload={'event':'call_ended','call':{'call_id':'same-call'}}
            with ThreadPoolExecutor(max_workers=6) as pool:
                rows=list(pool.map(lambda _:ledger.webhook('tenant-a',payload),range(12)))
            self.assertEqual(sum(not r['duplicate'] for r in rows),1)
            self.assertTrue(all(r['phase']==2 for r in rows))

    def test_malformed_webhook_has_no_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger=Ledger(Path(tmp)/'state.sqlite')
            for payload in [{'event':'unknown','call':{'call_id':'x'}},{'event':'call_ended','call':{}},{'event':'call_started','call':[]}]:
                with self.assertRaises(ValueError):ledger.webhook('a',payload)
            with ledger.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM events').fetchone()[0],0)

    def test_approval_cannot_silently_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger=Ledger(Path(tmp)/'state.sqlite');ledger.approve('a','x',{'value':1})
            with self.assertRaises(ValueError):ledger.approve('a','x',{'value':2})

if __name__=='__main__':unittest.main()
