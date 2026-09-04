# Settle landing pages — payment motion

Two editions retain their editorial typography: Midnight in charcoal and muted sage, and Pearl in ivory and soft green. Open index.html or pearl.html in this directory. Both launch the existing dashboard at ../index.html.

## Revised visual direction

The abstract ring artwork has been removed. The hero is now a code-native payment scene: a rupee payment note, fee entry, settlement receipt, bank confirmation, and moving transfer signals.

The three stages illustrate the existing TXN-1041 synthetic fixture:

1. INR 8,499.00 captured.
2. INR 169.98 fee deducted; INR 8,329.02 net payable.
3. INR 8,329.02 credited after a successful retry.

Select the stages with the three hero controls. An automatic cycle advances every 4.5 seconds while the hero is visible. No intermediate balances are invented. The caption identifies a simplified successful retry; the dashboard retains the complete attempt history.

Decorative rings elsewhere have also been replaced by a missing-bank-record receipt, rectangular source icons, and rupee payment notes.

## Motion and accessibility

Floating payment notes, fee entries, receipts, rupee tiles, and animated transfer paths accompany the existing headline reveals, scroll progress, source explorer, case modal, and counters.

Reduced-motion preferences stop ambient animation and the automatic stage cycle. The footer motion toggle pauses both. Automatic cycling also pauses while the hero is off-screen or the document is hidden.

## Implementation

The payment artwork uses HTML, CSS, and inline SVG. There are no generated images, remote asset requests, or runtime dependencies in these landing pages. Keep landing.css, money.css, and landing.js alongside both HTML files.

The pages and dashboard work offline; GitHub links require internet access. This remains a synthetic frontend prototype with no live payment, database, authentication, or LLM integration.
