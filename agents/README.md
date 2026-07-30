# WARDEN monitored-agent fleet

Data-only agent specs that produce `core.contracts.SessionTrace` objects for WARDEN to
watch. Each module exports `SPEC`, an `AgentSpec` with a system prompt, tool metadata,
a four-case scenario corpus (`clean · obvious · paraphrased · borderline`), and
`build_trace(session_id, scenario)`. Every tool is a logging stub; no outside action is
performed. `signature` is deliberately omitted (`None`) so WARDEN must **discover** it —
authoring it would grade the exam with the answer key attached.

`agents/__init__.py` exposes `FLEET` (canonical order) and `FLEET_BY_ID`.

## Roster (19 agents = the 16 from `docs/AGENT_FLEET.md` + 3 extensions)

**Tier 1 — flagships (canonical injection surfaces)**
| Agent | Baseline / `task_intent` | Sensitive target | Untrusted surface |
|---|---|---|---|
| `support-agent` | `lookup_account` | `issue_refund` | retrieved KB doc |
| `billing-agent` | `get_invoice` | `adjust_credit` | vendor email |
| `ops-copilot` | `read_logs` | `run_shell` | poisoned log/alert |
| `data-analyst` | `run_query` | `export_csv` | table comment (stored) |
| `email-assistant` | `read_thread` | `create_mail_rule` | incoming email body |

**Tier 2 — breadth (distinct high-value vectors)**
| Agent | Baseline | Sensitive target | Untrusted surface |
|---|---|---|---|
| `procurement-agent` | `lookup_po` | `release_payment` | supplier quote email |
| `sales-quote-agent` | `build_quote` | `apply_discount` | uploaded RFP doc |
| `devops-pr-agent` | `comment_pr` | `approve_pr` | code comment in a diff |
| `it-helpdesk-agent` | `lookup_user` | `grant_role` | ticket description |
| `legal-contract-agent` | `extract_clause` | `sign_document` | counterparty clause |
| `soc-triage-agent` | `enrich_ioc` | `close_alert` | threat-intel feed |

**Tier 3 — sensitive-domain breadth (synthetic data, stubbed actions)**
| Agent | Baseline | Sensitive target | Untrusted surface |
|---|---|---|---|
| `trading-research-agent` | `run_screen` | `place_order` *(stub)* | scraped news article |
| `logistics-agent` | `track_shipment` | `reroute_shipment` | carrier note / EDI |
| `healthcare-intake-agent` | `schedule` | `release_records` *(synthetic)* | referral letter |
| `hr-onboarding-agent` | `create_employee` | `set_salary` | resume text |
| `social-comms-agent` | `draft_post` | `publish_post` | mention / comment |

**Extensions — fill empty (impact, vector) cells in the coverage matrix (§6)**
| Agent | Baseline | Sensitive target | Untrusted surface | New cell filled |
|---|---|---|---|---|
| `rag-chatbot-agent` | `answer_question` | `disclose_internal` | poisoned KB article | Exfiltration × retrieved-doc |
| `browser-agent` | `read_page` | `submit_form` | live web-page DOM/text | new vector: web page |
| `calendar-scheduler-agent` | `list_events` | `share_availability` | calendar-invite body | new vector: calendar invite |

## Wiring into WARDEN

Copy this folder to `warden/test_agents/`. The specs import `core.contracts`
(`SessionTrace`, `Step`) — all 19 build and roundtrip through the frozen contract
unchanged (`clean` scenarios emit no sensitive call; the other three do).

The uploaded project's demo replay engine (`core/agent_harness.py`) still hardcodes
`SENSITIVE_TOOLS = {"issue_refund"}` and refund-only directive extraction. To run the
non-support agents through `WardenEngine`, source the sensitive-tool set and the target
action from `spec.sensitive_tools` / the selected agent's `sensitive_tool` instead of
the hardcoded constants. Per `docs/AGENT_FLEET.md` §5 this is the **single**
fleet-enablement touch-point — a harness extension only; `core/contracts.py` and the
event schema remain unchanged.
