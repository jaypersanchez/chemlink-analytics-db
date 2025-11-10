# TraderSensei Gateway & Orbit – Execution Guide

## Vision
Deploy the full TraderSensei stack on an Arbitrum Orbit L3 tailored for large financial/investment institutions (“DeFi meets Forex”). The chain hosts Sensei Vaults, sleeves, and institution-specific Sensei Belt instances. **G-Impact** is the L3 gas token, minted via **GNIM** bridged from L1/L2.

---

## Phase 0 – Gateway (GNIM Bridge & Access Control)

### Goals
- Launch GNIM on L1 (OTC distribution) and provide a controlled L1↔L2 bridge.
- Enforce KYC/AML, whitelists, and rate limits while GNIM lacks public liquidity.
- Prepare GNIM→G-Impact conversion logic for future L3 usage.

### Key Tasks
- Deploy GNIM ERC-20 on L1 mainnet; manage supply via multisig treasury/HSM.
- Implement bridge contracts (L1↔L2) with configurable whitelist, per-address caps, and compliance registry.
- Define GNIM↔G-Impact conversion contract (adjustable rates/fees, pause switch).
- Stand up monitoring/auditing for OTC transfers and bridge activity.

---

## Phase 1 – Orbit L3 Deployment

### Goals
- Stand up an Arbitrum Orbit rollup anchored to Arbitrum One with G-Impact as native gas.
- Prepare sequencer/batch-poster infrastructure and extend GNIM bridge to L3.
- Deploy TraderSensei core contracts on the new chain.

### Key Tasks
- Orbit registration: deploy rollup/bridge/inbox contracts on Arbitrum One; fund deployer with ETH.
- Nitro chain config: set chain ID, genesis, gas token (G-Impact), sequencer + batch poster keys.
- Infra: provision sequencer nodes, batch poster, validators; add monitoring/alerting/failover.
- Bridge extension: allow GNIM→G-Impact mint/burn, maintain whitelist until L1 LPs exist.
- Deploy TraderSensei contracts (Sensei Vault factory, sleeve registry, Sensei Belt templates, per-FI proxy factories).
- Governance/compliance: multisigs for upgrades, onboarding policies, KYC gating for institution deployments.

---

## Phase 2 – Protocol Rollout & Pilot Onboarding

### Goals
- Onboard pilot FIs, each with its own Sensei Vault + sleeves on the L3.
- Validate DeFi↔Forex workflows (Sensei Belt customization, settlement flows).

### Key Tasks
- Mint initial G-Impact reserves; distribute via whitelisted faucet or OTC deals.
- Provision per-institution Sensei Belt instances via factory; enforce access controls.
- Build observability: RPC endpoints, indexer/subgraph, dashboards for vault/sleeve metrics.
- Run end-to-end tests (GNIM bridge, G-Impact gas, trading flows) with pilot partners.
- Capture feedback, iterate on UX/compliance tooling.

---

## Phase 3 – Scale, Liquidity & Decentralization

### Goals
- List GNIM on L1 liquidity pools and relax bridge restrictions.
- Expand sequencer decentralization and incentive programs.
- Integrate advanced TraderSensei modules (Forex instruments, cross-asset settlement).

### Key Tasks
- Seed GNIM pools on L1; update oracle feeds and conversion formulas.
- “Flip the switch” on bridge (remove/adjust whitelists, fees) via governance.
- Launch incentives: gas rebates for GNIM stakers, G-Impact liquidity mining, partner promotions.
- Plan sequencer decentralization (additional operators, staking/slashing, transparency tooling).
- Roll out new modules incrementally with audits and feature flags.

---

## Tokenomics Snapshot
- **GNIM**: L1/L2 treasury & governance token, OTC now, LP later.
- **G-Impact**: Orbit L3 gas token minted/burned during GNIM bridging; fee revenue funds sequencer + treasury.
- Conversion ratio & fees configurable; part of fees swapped to ETH for batch posting.
- Incentives: rebated gas for institutions staking GNIM, liquidity programs once GNIM pools exist.

---

## Execution Notes
- Bridge first, Orbit second: launching the gateway early lets institutions acquire GNIM/G-Impact even before L3 is live.
- All controls are configuration-driven (whitelists, rate limits, fees) so opening to the public post-LP is just a policy change.
- Maintain comprehensive monitoring/audit trails from day one to satisfy institutional compliance.
