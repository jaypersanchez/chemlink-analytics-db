# Risk Register – TraderSensei Gateway & Orbit

## Phase 0 – Gateway (GNIM Bridge & Access Control)
| Risk | Impact | Likelihood | Mitigation |
| --- | --- | --- | --- |
| Price discovery gaps (no LP) | Mispriced conversions, arbitrage | Medium | Manual KYC, whitelist, configurable rates, withdrawal caps |
| Treasury custody failure | Loss of GNIM reserves | Low | Multisig + HSM policies, audits, incident runbooks |
| Compliance breach | Regulatory penalties | Low/Med | Enforce KYC registry, logging, manual review before mint/burn |
| Bridge contract bug | Locked funds/exploit | Low | External audits, staged rollout, pause switch |

## Phase 1 – Orbit L3 Deployment
| Risk | Impact | Likelihood | Mitigation |
| --- | --- | --- | --- |
| Sequencer downtime | Network stall | Medium | Redundant sequencers, failover, monitoring/alerting |
| Misconfigured gas token | Failed txs | Low | Testnet rehearsal, config reviews, emergency upgrade keys |
| Bridge extension flaw | Supply mismatch | Low/Med | Simulations, dual audits, sandbox testing |
| Insider misconfig | Unauthorized upgrades | Low | Role-based access, multisig approvals, change logs |

## Phase 2 – Protocol Rollout & Pilots
| Risk | Impact | Likelihood | Mitigation |
| --- | --- | --- | --- |
| Pilot onboarding delays | Slow adoption | Medium | Dedicated support, sandbox envs, clear docs |
| Multi-tenant isolation bug | Data leakage | Low/Med | Contract audits, permission tests, bug bounty |
| Gas scarcity | Failed txs | Medium | Ensure G-Impact liquidity, automated top-ups, price alerts |
| Regulatory shifts | Compliance gap | Medium | Legal review cadence, configurable controls |

## Phase 3 – Scale & Liquidity
| Risk | Impact | Likelihood | Mitigation |
| --- | --- | --- | --- |
| Liquidity shocks | GNIM volatility | Medium | Treasury market-making, dynamic fees, reserves |
| Open bridge exploit | Treasury drain | Low/Med | Configurable rate limits, monitoring, circuit breakers |
| Sequencer centralization | Governance capture | Medium | Add operators, staking/slashing, transparency |
| FX/DeFi module failure | Smart-contract loss | Low/Med | Phased rollout, audits, feature flags |
