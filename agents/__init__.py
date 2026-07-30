"""WARDEN monitored-agent fleet, built on the frozen SessionTrace contract.

Sixteen agents from docs/AGENT_FLEET.md, plus three coverage-matrix extensions.
Every SPEC is a data-only AgentSpec; none touch core/ or perform real side effects.
"""

# --- Tier 1: flagships (canonical injection surfaces) ---------------------- #
from .support import SPEC as SUPPORT
from .billing import SPEC as BILLING
from .ops_copilot import SPEC as OPS_COPILOT
from .data_analyst import SPEC as DATA_ANALYST
from .email_assistant import SPEC as EMAIL_ASSISTANT

# --- Tier 2: breadth (distinct high-value vectors) ------------------------- #
from .procurement import SPEC as PROCUREMENT
from .sales_quote import SPEC as SALES_QUOTE
from .devops_pr import SPEC as DEVOPS_PR
from .it_helpdesk import SPEC as IT_HELPDESK
from .legal_contract import SPEC as LEGAL_CONTRACT
from .soc_triage import SPEC as SOC_TRIAGE

# --- Tier 3: sensitive-domain breadth (synthetic, stubbed actions) --------- #
from .trading_research import SPEC as TRADING_RESEARCH
from .logistics import SPEC as LOGISTICS
from .healthcare_intake import SPEC as HEALTHCARE_INTAKE
from .hr_onboarding import SPEC as HR_ONBOARDING
from .social_comms import SPEC as SOCIAL_COMMS

# --- Extensions: fill empty (impact, vector) cells in the coverage matrix --- #
from .rag_chatbot import SPEC as RAG_CHATBOT
from .browser_agent import SPEC as BROWSER
from .calendar_scheduler import SPEC as CALENDAR_SCHEDULER

# Canonical fleet order (mirrors docs/AGENT_FLEET.md §3, then extensions).
FLEET = (
    SUPPORT, BILLING, PROCUREMENT, SALES_QUOTE, TRADING_RESEARCH,
    OPS_COPILOT, DEVOPS_PR, LOGISTICS,
    DATA_ANALYST, EMAIL_ASSISTANT, HEALTHCARE_INTAKE,
    IT_HELPDESK, HR_ONBOARDING,
    SOCIAL_COMMS, LEGAL_CONTRACT,
    SOC_TRIAGE,
    RAG_CHATBOT, BROWSER, CALENDAR_SCHEDULER,
)

# Lookup by agent_id for the validation harness and Fleet screen.
FLEET_BY_ID = {spec.agent_id: spec for spec in FLEET}
