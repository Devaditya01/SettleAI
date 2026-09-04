import json
import os
import sys
import pandas as pd
from datetime import datetime, timedelta

# Add parent to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.loader import load_data

def convert_amount(amt):
    try:
        return int(float(amt) * 100)
    except:
        return 0

def format_date(dt):
    if pd.isna(dt):
        return None
    # Add +05:30 offset
    return dt.strftime('%Y-%m-%dT%H:%M:%S+05:30')

def format_day(dt):
    if pd.isna(dt):
        return '2026-09-04'
    return dt.strftime('%Y-%m-%d')

def run():
    print("Loading data...")
    data = load_data("data")
    
    gateway_df = data["gateway"]
    bank_df = data["bank"]
    ledger_df = data["ledger"]
    
    merchant_id = "merchant_imported_records"
    merchant_name = "Imported Records"

    merged = gateway_df.join(bank_df.drop(columns=['transaction_id']), how='left')
    merged = merged.join(ledger_df.drop(columns=['transaction_id']), how='left')
    
    # Ensure amount exists
    merged['amount'] = merged['amount'].fillna(0)
    
    print(f"Total transactions: {len(merged)}")
    
    transactions = []
    gateway_events = []
    bank_events = []
    ledger_events = []
    
    for i, (tx_id, row) in enumerate(merged.iterrows()):
        amt_minor = convert_amount(row['amount'])
        fee_minor = 0
        payable_minor = amt_minor - fee_minor
        settlement_id = f"SET-{tx_id}"
        
        gw_ts = row['gateway_timestamp']
        day = format_day(gw_ts)
        
        # Meta
        transactions.append({
            "merchant_id": merchant_id,
            "transaction_id": tx_id,
            "settlement_id": settlement_id,
            "currency": "INR",
            "customer": f"Transaction {tx_id}",
            "payment_date": day,
            "captured_minor": amt_minor,
            "scenario": "unknown"
        })
        
        # Gateway events
        if pd.notna(gw_ts):
            gateway_events.append({
                "merchant_id": merchant_id,
                "transaction_id": tx_id,
                "settlement_id": settlement_id,
                "currency": "INR",
                "source": "gateway",
                "source_record_id": f"G-{tx_id}-01",
                "event_type": "payment_captured",
                "status": "captured",
                "amount_minor": amt_minor,
                "occurred_at": format_date(gw_ts),
                "attempt_id": ""
            })
            
            # Settlement Initiated
            init_time = gw_ts + timedelta(minutes=10)
            gateway_events.append({
                "merchant_id": merchant_id,
                "transaction_id": tx_id,
                "settlement_id": settlement_id,
                "currency": "INR",
                "source": "gateway",
                "source_record_id": f"G-{tx_id}-02",
                "event_type": "settlement_initiated",
                "status": "initiated",
                "amount_minor": payable_minor,
                "occurred_at": format_date(init_time),
                "attempt_id": f"ATT-{tx_id}-1"
            })

        # Bank events
        bk_ts = row.get('bank_updated_at')
        if pd.isna(bk_ts):
            bk_ts = row.get('bank_received_at')
        
        bk_status = str(row.get('bank_status', '')).upper()
        
        if pd.notna(bk_ts) and bk_status != 'NAN':
            status = 'credited' if bk_status == 'SETTLED' else 'rejected' if bk_status == 'FAILED' else 'processing'
            if status != 'processing':
                bank_reason = row.get('bank_response_code', '')
                reason_code = '' if pd.isna(bank_reason) else str(bank_reason)
                bank_events.append({
                    "merchant_id": merchant_id,
                    "transaction_id": tx_id,
                    "settlement_id": settlement_id,
                    "currency": "INR",
                    "source": "bank",
                    "source_record_id": f"B-{tx_id}-01",
                    "event_type": "settlement_outcome",
                    "status": status,
                    "amount_minor": convert_amount(row.get('settlement_amount', payable_minor / 100.0)),
                    "occurred_at": format_date(bk_ts),
                    "attempt_id": f"ATT-{tx_id}-1",
                    "reason_code": reason_code,
                    "bank_reference": f"UTR_{tx_id}" if status == 'credited' else ''
                })

        # Ledger events
        lg_ts = row.get('ledger_timestamp')
        lg_status = str(row.get('ledger_status', '')).upper()
        
        if pd.notna(gw_ts):
            ledger_events.append({
                "merchant_id": merchant_id,
                "transaction_id": tx_id,
                "settlement_id": settlement_id,
                "currency": "INR",
                "source": "ledger",
                "source_record_id": f"L-{tx_id}-01",
                "event_type": "captured_receivable",
                "status": "posted",
                "amount_minor": amt_minor,
                "occurred_at": format_date(gw_ts + timedelta(seconds=2)),
                "attempt_id": ""
            })
            ledger_events.append({
                "merchant_id": merchant_id,
                "transaction_id": tx_id,
                "settlement_id": settlement_id,
                "currency": "INR",
                "source": "ledger",
                "source_record_id": f"L-{tx_id}-02",
                "event_type": "fee_deduction",
                "status": "posted",
                "amount_minor": fee_minor,
                "occurred_at": format_date(gw_ts + timedelta(seconds=3)),
                "attempt_id": ""
            })
            
        if pd.notna(lg_ts) and lg_status == 'POSTED':
            ledger_events.append({
                "merchant_id": merchant_id,
                "transaction_id": tx_id,
                "settlement_id": settlement_id,
                "currency": "INR",
                "source": "ledger",
                "source_record_id": f"L-{tx_id}-03",
                "event_type": "settlement_posted",
                "status": "posted",
                "amount_minor": convert_amount(row.get('ledger_amount', payable_minor / 100.0)),
                "occurred_at": format_date(lg_ts),
                "attempt_id": f"ATT-{tx_id}-1"
            })
            
    as_of = datetime(2026, 9, 4, 18, 0, 0).strftime('%Y-%m-%dT%H:%M:%S+05:30')
    output = {
        "schema_version": "1.0.0",
        "merchant_id": merchant_id,
        "merchant_name": merchant_name,
        "as_of": as_of,
        "transactions": transactions,
        "sources": {
            "gateway": gateway_events,
            "bank": bank_events,
            "ledger": ledger_events
        }
    }
    
    js_content = f"""(function (root, factory) {{
  const dataset = factory();
  if (typeof module === 'object' && module.exports) module.exports = dataset;
  if (root) root.SettleRealData = dataset;
}})(typeof globalThis !== 'undefined' ? globalThis : this, function () {{
  'use strict';
  return {json.dumps(output, indent=2)};
}});
"""
    
    out_path = os.path.join("data", "real-data.js")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(js_content)
    
    print(f"Successfully compiled {len(transactions)} transactions to {out_path} ({os.path.getsize(out_path)/1024/1024:.2f} MB)")

if __name__ == '__main__':
    run()
