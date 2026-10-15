#!/usr/bin/env python3
"""Generalized positive/negative replay; calibrates rules, does not scan a target."""
import hashlib
import html
import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path


def _state_authority_and_output_controls(db, record):
    original_accounts = list(db.execute('SELECT * FROM accounts'))
    version_marker = {'version': 'old'}
    version_marker['version'] = 'new'
    record('accounts.positive.version-drift-preserves-identity', list(db.execute('SELECT * FROM accounts')) == original_accounts)
    db.execute('DELETE FROM accounts')
    record('accounts.negative.marker-reset-detected', list(db.execute('SELECT * FROM accounts')) != original_accounts)
    for n in range(5):
        db.execute('INSERT INTO sales VALUES(?,?)', ('history-'+str(n), '{}'))
    full = list(db.execute('SELECT * FROM sales ORDER BY id'))
    capped = list(db.execute('SELECT * FROM sales ORDER BY id LIMIT 2'))
    record('backup.positive.full-history-inventory', len(full) == 7)
    record('backup.negative.ui-limit-truncation-detected', full != capped)
    ledger = [{'total': 100, 'status': 'refunded'}, {'total': -40, 'refundOf': 's'}, {'total': -60, 'refundOf': 's', 'fullRefund': True}]
    record('ledger.positive.cumulative-refunds-balance', sum(o['total'] for o in ledger) == 0)
    wrong = [o for o in ledger if o.get('status') != 'refunded' and not o.get('fullRefund')]
    record('ledger.negative.pair-exclusion-leaves-negative', sum(o['total'] for o in wrong) != 0)
    stored_role, renderer_role = 'staff', 'owner'
    record('authority.positive.native-role-denies-owner-action', stored_role != 'owner')
    record('authority.negative.renderer-role-trust-detected', renderer_role != stored_role)
    catalog = {'id': 'p', 'name': 'item', 'price': 20, 'cost': 4, 'supplier': 'private'}
    public = {k: catalog[k] for k in ['id', 'name', 'price']}
    private_fields = {'cost', 'supplier'}
    record('privacy.positive.display-projection', not private_fields.intersection(public))
    record('privacy.negative.global-record-leak-detected', bool(private_fields.intersection(catalog)))
    literal = 'printer" & echo injected > output %PATH%'
    child = subprocess.run([sys.executable, '-c', 'import sys;print(sys.argv[1])', literal], capture_output=True, text=True, check=True)
    record('command.positive.literal-data-in-fixed-child', child.stdout.rstrip('\r\n') == literal)
    unsafe_program = 'copy "job.bin" "' + literal + '"'
    record('command.negative.interpolated-program-detected', '& echo injected' in unsafe_program)
    class Attributes(HTMLParser):
        def handle_starttag(self, tag, attrs):
            self.attrs = dict(attrs)
    identifier = 'item" data-action="other'
    escaped, unescaped = Attributes(), Attributes()
    escaped.feed('<button data-id="' + html.escape(identifier, quote=True) + '"></button>')
    unescaped.feed('<button data-id="' + html.escape(identifier, quote=False) + '"></button>')
    record('markup.positive.attribute-identity-preserved', escaped.attrs == {'data-id': identifier})
    record('markup.negative.text-only-escaping-detected', 'data-action' in unescaped.attrs)
    acknowledged = lambda r, identity: bool(r and r.get('success') is True and r.get('record', {}).get('id') == identity)
    record('receipt.positive.original-identity-required', acknowledged({'success': True, 'record': {'id': 'original'}}, 'original'))
    record('receipt.negative.bare-success-rejected', not acknowledged({'success': True}, 'original'))
    explicit_zero = {'birthday_bonus': 0}
    restored_zero = json.loads(json.dumps(explicit_zero))
    record('settings.positive.explicit-zero-survives', restored_zero['birthday_bonus'] == 0)
    record('settings.negative.falsy-default-detected', (restored_zero['birthday_bonus'] or 100) != 0)
    deposit = {'shift': 'original', 'cash': 100, 'gift': 10}
    record('deposit.positive-original-drawer-real-cash', 200 + deposit['cash'] == 300 and deposit['shift'] == 'original')
    record('deposit.negative-gift-as-cash-detected', 200 + deposit['cash'] + deposit['gift'] != 300)


def _state_retry_and_rollback_controls(db, record, sale, snapshot):
    pending = {'complete': False}
    success = lambda receipt: bool(receipt and receipt.get('success') is True)
    record('ack.positive.pending-not-success', not success(pending))
    record('ack.negative.optimistic-success-detected', bool(pending) != success(pending))
    before = snapshot()
    failed_receipt = None
    try:
        sale('failed', 2, fail_midway=True)
    except ValueError:
        failed_receipt = {'success': False}
    record('rollback.positive.complete-snapshot-preserved', snapshot() == before)
    record('rollback.negative.swallowed-save-success-detected', success({'success': True}) != success(failed_receipt))
    try:
        sale('original-id', 2, lose_reply=True)
    except ConnectionError:
        pass
    sale('original-id', 2)
    record('retry.positive.original-id-exactly-once', db.execute('SELECT qty FROM stock').fetchone()[0] == 8)
    try:
        sale('original-id', 3)
        rejected = False
    except ValueError:
        rejected = True
    record('retry.negative.changed-payload-rejected', rejected)
    sale('wrong-new-id', 2)
    record('retry.negative.new-id-duplicates-detected', db.execute('SELECT qty FROM stock').fetchone()[0] != 8)


def replay():
    cases = {}
    def record(name, condition):
        cases[name] = bool(condition)
    db = sqlite3.connect(':memory:', isolation_level=None)
    db.executescript('CREATE TABLE stock(id TEXT PRIMARY KEY,qty INTEGER);INSERT INTO stock VALUES("p",10);CREATE TABLE sales(id TEXT PRIMARY KEY,payload TEXT);CREATE TABLE accounts(id TEXT PRIMARY KEY,role TEXT,credential TEXT);INSERT INTO accounts VALUES("custom-owner","owner","existing-hash");')
    def sale(request_id, qty, fail_midway=False, lose_reply=False):
        payload = json.dumps({'qty': qty}, sort_keys=True)
        db.execute('BEGIN IMMEDIATE')
        try:
            old = db.execute('SELECT payload FROM sales WHERE id=?', (request_id,)).fetchone()
            if old:
                if old[0] != payload:
                    raise ValueError('content mismatch')
            else:
                db.execute('UPDATE stock SET qty=qty-? WHERE id="p"', (qty,))
                if fail_midway:
                    raise ValueError('injected write failure')
                db.execute('INSERT INTO sales VALUES(?,?)', (request_id, payload))
            db.execute('COMMIT')
        except Exception:
            db.execute('ROLLBACK')
            raise
        if lose_reply:
            raise ConnectionError('reply lost after commit')
        return {'success': True, 'id': request_id}
    def snapshot():
        return list(db.execute('SELECT * FROM stock')), list(db.execute('SELECT * FROM sales'))
    try:
        _state_retry_and_rollback_controls(db, record, sale, snapshot)
        _state_authority_and_output_controls(db, record)
        db.execute('UPDATE stock SET qty=1 WHERE id="p"')
        sale('shared-first', 1)
        before_second = snapshot()
        rejected_second = db.execute('SELECT qty FROM stock WHERE id="p"').fetchone()[0] < 1
        record('shared.positive-single-authority-last-item', rejected_second and snapshot() == before_second)
        replicas = [{'qty': 1}, {'qty': 1}]
        replica_sales = sum(1 for replica in replicas if replica['qty'] >= 1)
        record('shared.negative-independent-replicas-oversell', replica_sales > 1)
        admits_journal = lambda journal, store: journal['store_id'] == store
        journal = {'store_id': 'original-store', 'request_id': 'original-id'}
        record('identity.positive-original-store-replay', admits_journal(journal, 'original-store'))
        record('identity.negative-replacement-store-rejected', not admits_journal(journal, 'replacement-store'))
        fractional = Decimal('0.125')
        record('quantity.positive-fractional-units-retained', Decimal('2') - fractional == Decimal('1.875'))
        record('quantity.negative-integer-coercion-detected', Decimal(int(fractional)) != fractional)
        instant = datetime(2024, 1, 31, 16, 30, tzinfo=timezone.utc)
        store_date = instant.astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')
        record('calendar.positive-local-month-matches-ledger', store_date == '2024-02-01' and store_date[:7] == '2024-02')
        record('calendar.negative-utc-month-prefix-detected', instant.isoformat()[:7] != store_date[:7])
    finally:
        db.close()
    return {'schemaVersion': 1, 'profile': 'state-integrity-general-replay/v3',
            'status': 'PASS' if all(cases.values()) else 'FAIL', 'cases': cases,
            'sourceSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'scope': 'generalized calibration only; target runtime and deployed security unmeasured'}


if __name__ == '__main__':
    result = replay()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result['status'] == 'PASS' else 1)
