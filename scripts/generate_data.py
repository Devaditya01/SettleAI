import csv
import os
import random
import argparse
from datetime import datetime, timedelta

GATEWAY_FILE = 'gateway.csv'
BANK_FILE = 'bank.csv'
LEDGER_FILE = 'ledger.csv'

# Constants
SCENARIOS = [
    'normal', 
    'gateway_failure', 
    'bank_delay', 
    'ledger_delay', 
    'amount_mismatch', 
    'missing_bank_record', 
    'retry_duplicate', 
    'long_processing'
]
SCENARIO_WEIGHTS = [0.65, 0.10, 0.05, 0.05, 0.03, 0.04, 0.05, 0.03]
PAYMENT_METHODS = ['UPI', 'CARD', 'NETBANKING', 'WALLET']
BANKS = ['BANK_A', 'BANK_B', 'BANK_C', 'BANK_D']
AMOUNTS = [100, 250, 500, 1000, 1500, 2500, 5000, 10000]

def random_delay_mins(min_m, max_m, skewed=False):
    if skewed:
        # Beta distribution pushes values towards the lower end
        val = random.betavariate(2, 5)
        return min_m + (max_m - min_m) * val
    return random.uniform(min_m, max_m)

def generate_row_data(txn_id_num):
    txn_id = f"TXN{txn_id_num:06d}"
    scenario = random.choices(SCENARIOS, weights=SCENARIO_WEIGHTS, k=1)[0]
    
    # Gateway data
    gw_amount = random.choice(AMOUNTS)
    gw_method = random.choice(PAYMENT_METHODS)
    gw_retry = 0
    if scenario == 'retry_duplicate':
        gw_retry = random.randint(1, 3)
        
    gw_time = datetime(2026, 8, 1) + timedelta(minutes=random.randint(0, 45000)) # Random time in Aug/Sep 2026
    
    gw_status = 'SUCCESS'
    gw_response_code = '00'
    if scenario == 'gateway_failure':
        gw_status = 'FAILED'
        gw_response_code = random.choice(['05', '51', '91']) # Some error codes
        
    gateway_row = {
        'transaction_id': txn_id,
        'gateway_timestamp': gw_time.strftime('%Y-%m-%d %H:%M:%S'),
        'gateway_status': gw_status,
        'gateway_response_code': gw_response_code,
        'amount': gw_amount,
        'payment_method': gw_method,
        'retry_count': gw_retry
    }
    
    bank_row = None
    ledger_row = None
    
    # Bank & Ledger Data
    if scenario != 'gateway_failure' and scenario != 'missing_bank_record':
        bank_recv_delay = random_delay_mins(0.1, 10, skewed=True)
        bank_recv_time = gw_time + timedelta(minutes=bank_recv_delay)
        
        bank_name = random.choice(BANKS)
        bank_amount = gw_amount
        
        if scenario == 'amount_mismatch':
            # Create a mismatch (e.g. partial capture or incorrect fee deduction)
            mismatch_type = random.choice(['short', 'excess'])
            if mismatch_type == 'short':
                bank_amount = gw_amount - random.randint(1, 5) * 10
            else:
                bank_amount = gw_amount + random.randint(1, 5) * 10
                
        if scenario == 'bank_delay':
            bank_status = 'PROCESSING'
            bank_response_code = 'PENDING'
            bank_update_delay = random_delay_mins(10, 60) # Just updated recently, still processing
            bank_upd_time = bank_recv_time + timedelta(minutes=bank_update_delay)
        else:
            bank_status = 'SETTLED'
            bank_response_code = '00'
            if scenario == 'long_processing':
                # Settles after 1-7 days
                bank_update_delay = random_delay_mins(1440, 10000)
            elif scenario == 'bank_delay': # Handled above
                pass
            else:
                # Normal settlement latency: 5 mins to 120 mins
                # Let's make normal and delayed overlap. Normal can be up to 120, delay can start at 60.
                bank_update_delay = random_delay_mins(5, 120, skewed=True)
                
            bank_upd_time = bank_recv_time + timedelta(minutes=bank_update_delay)
            
        bank_row = {
            'transaction_id': txn_id,
            'bank_received_at': bank_recv_time.strftime('%Y-%m-%d %H:%M:%S.%f'),
            'bank_updated_at': bank_upd_time.strftime('%Y-%m-%d %H:%M:%S.%f'),
            'bank_status': bank_status,
            'bank_response_code': bank_response_code,
            'settlement_amount': float(bank_amount),
            'bank_name': bank_name
        }

    # Ledger generation
    if scenario != 'gateway_failure':
        # Default ledger state if bank is not settled or missing
        ledger_status = 'PENDING'
        ledger_time = gw_time + timedelta(minutes=random_delay_mins(1, 60))
        
        if scenario == 'normal' or scenario == 'retry_duplicate' or scenario == 'long_processing':
            ledger_status = 'POSTED'
            ledger_post_delay = random_delay_mins(1, 30, skewed=True)
            ledger_time = datetime.strptime(bank_row['bank_updated_at'], '%Y-%m-%d %H:%M:%S.%f') + timedelta(minutes=ledger_post_delay)
            
        elif scenario == 'ledger_delay':
            # Bank is settled, but ledger is still pending or severely delayed
            is_delayed_posted = random.choice([True, False])
            if is_delayed_posted:
                ledger_status = 'POSTED'
                ledger_post_delay = random_delay_mins(60, 1440) # Overlaps with normal
                ledger_time = datetime.strptime(bank_row['bank_updated_at'], '%Y-%m-%d %H:%M:%S.%f') + timedelta(minutes=ledger_post_delay)
            else:
                ledger_status = 'PENDING'
                ledger_time = datetime.strptime(bank_row['bank_updated_at'], '%Y-%m-%d %H:%M:%S.%f') + timedelta(minutes=random_delay_mins(10, 120))
                
        # amount_mismatch, missing_bank_record, bank_delay will remain PENDING
        
        ledger_row = {
            'transaction_id': txn_id,
            'ledger_timestamp': ledger_time.strftime('%Y-%m-%d %H:%M:%S.%f'),
            'ledger_status': ledger_status,
            'ledger_amount': float(gw_amount)
        }
        
    return gateway_row, bank_row, ledger_row

def print_stats():
    if not os.path.exists(GATEWAY_FILE):
        print("No existing datasets found.")
        return
        
    print("--- Current Dataset Output ---")
    
    gw_count = 0
    max_id = 0
    with open(GATEWAY_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            gw_count += 1
            txn_num = int(row['transaction_id'].replace('TXN', ''))
            if txn_num > max_id:
                max_id = txn_num
                
    bank_count = sum(1 for _ in open(BANK_FILE)) - 1 if os.path.exists(BANK_FILE) else 0
    ledger_count = sum(1 for _ in open(LEDGER_FILE)) - 1 if os.path.exists(LEDGER_FILE) else 0
    
    print(f"Gateway Records: {gw_count}")
    print(f"Bank Records:    {bank_count}")
    print(f"Ledger Records:  {ledger_count}")
    print(f"Max Transaction ID: TXN{max_id:06d}")
    print("------------------------------")
    return max_id

def append_data(num_to_add, start_id):
    gateway_exists = os.path.exists(GATEWAY_FILE)
    
    with open(GATEWAY_FILE, 'a', newline='') as f_gw, \
         open(BANK_FILE, 'a', newline='') as f_bk, \
         open(LEDGER_FILE, 'a', newline='') as f_ld:
        
        gw_writer = csv.DictWriter(f_gw, fieldnames=['transaction_id', 'gateway_timestamp', 'gateway_status', 'gateway_response_code', 'amount', 'payment_method', 'retry_count'])
        bk_writer = csv.DictWriter(f_bk, fieldnames=['transaction_id', 'bank_received_at', 'bank_updated_at', 'bank_status', 'bank_response_code', 'settlement_amount', 'bank_name'])
        ld_writer = csv.DictWriter(f_ld, fieldnames=['transaction_id', 'ledger_timestamp', 'ledger_status', 'ledger_amount'])
        
        if not gateway_exists:
            gw_writer.writeheader()
            bk_writer.writeheader()
            ld_writer.writeheader()
            
        print(f"Generating {num_to_add} new transactions...")
        for i in range(num_to_add):
            txn_id_num = start_id + i
            gw_row, bk_row, ld_row = generate_row_data(txn_id_num)
            
            gw_writer.writerow(gw_row)
            if bk_row:
                bk_writer.writerow(bk_row)
            if ld_row:
                ld_writer.writerow(ld_row)
                
        print(f"Successfully added {num_to_add} transactions.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synthetic Transaction Data Generator")
    parser.add_argument('--add', type=int, default=0, help="Number of new transactions to generate and append")
    parser.add_argument('--status', action='store_true', help="Show current dataset stats")
    
    args = parser.parse_args()
    
    max_id = print_stats() or 0
    
    if args.add > 0:
        append_data(args.add, max_id + 1)
        print_stats() # print new stats
    elif not args.status:
        # Default behavior if no args passed: show stats and prompt
        print("Run with '--add N' to append N more transactions, e.g., 'python generate_data.py --add 1000'")
