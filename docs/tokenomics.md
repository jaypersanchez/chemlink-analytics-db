# TraderSensei Tokenomics (GNIM ↔ G-Impact)

## Overview
- **GNIM**: L1/L2 treasury + governance token. Currently OTC, moving to L1 liquidity pools later.
- **G-Impact**: Native gas token on TraderSensei’s Arbitrum Orbit L3. Users convert GNIM → G-Impact through the bridge; supply expands/contracts with demand.

## Conversion Flow
1. Institution acquires GNIM OTC (L1) and passes KYC review.
2. GNIM deposited into L1↔L2 bridge → GNIM-L2 minted (if needed) → G-Impact minted when bridging to L3.
3. Conversion ratio (e.g., 1 GNIM = 10 G-Impact) and fees (e.g., 0.3%) are stored in configurable contracts.
4. Redeeming G-Impact burns it on L3 and mints GNIM on L2/L1 minus fees.

## Fee Distribution
- **Sequencer Rewards**: Portion of G-Impact gas fees + conversion fees.
- **TraderSensei Treasury**: Remainder of conversion fees + optional share of gas fees, earmarked for dev/ops.
- **Reserve Refill**: Swaps a slice of fees to ETH to pay Arbitrum One batch-posting costs.

## Incentives
- **GNIM Staking**: Institutions stake GNIM to unlock discounted gas or priority execution.
- **Liquidity Programs**: Once GNIM LPs launch on L1, offer liquidity mining or fee rebates.
- **G-Impact Rebates**: Early adopters receive a percentage of gas spent back as rewards to offset onboarding friction.

## Controls
- Whitelist + rate limits while GNIM lacks public liquidity; adjustable via governance to “flip the switch” later.
- Emergency pause on mint/burn; timelocked multisig for parameter changes.
- Audit trail of conversions for compliance reporting.

## Supply Management
- GNIM total supply governed on L1; OTC treasury manages allocations.
- G-Impact is elastic: minted upon GNIM deposits, burned upon withdrawals, keeping circulation aligned with L3 activity.
