'use strict';

const fs = require('node:fs');
const path = require('node:path');
const dataset = require('../data/demo-fixtures.js');

const outputDirectory = path.resolve(__dirname, '..', 'data');
const sourceColumns = {
  gateway: ['merchant_id','transaction_id','settlement_id','attempt_id','source_record_id','event_type','status','amount_minor','currency','occurred_at','scheduled_for'],
  bank: ['merchant_id','transaction_id','settlement_id','attempt_id','source_record_id','event_type','status','amount_minor','currency','occurred_at','reason_code','bank_reference'],
  ledger: ['merchant_id','transaction_id','settlement_id','attempt_id','source_record_id','event_type','status','amount_minor','currency','occurred_at']
};

function cell(value) {
  const text = String(value ?? '');
  return `"${text.replaceAll('"','""')}"`;
}

function toCsv(rows, columns) {
  return [columns.join(','), ...rows.map(row=>columns.map(column=>cell(row[column])).join(','))].join('\r\n')+'\r\n';
}

for (const [source, columns] of Object.entries(sourceColumns)) {
  fs.writeFileSync(path.join(outputDirectory, `${source}.csv`),toCsv(dataset.sources[source],columns),'utf8');
}

const summaryColumns=['merchant_id','transaction_id','settlement_id','customer','payment_date','captured_minor','currency','scenario'];
fs.writeFileSync(path.join(outputDirectory,'demo_transactions.csv'),toCsv(dataset.transactions,summaryColumns),'utf8');
console.log(`Generated ${dataset.transactions.length} canonical transactions in ${outputDirectory}`);
