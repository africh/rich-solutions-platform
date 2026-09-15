# GOAL — Whitespace Capability Model & Agentic Software Factory Framework

## Objective
Build a client-facing consulting offering that (1) maps business capabilities (L1–L3) across target industries, (2) identifies whitespace where AI/automation adoption is low but AI readiness is high, and (3) provides an accelerated, human-gated path from whitespace to built solution via a software factory agent platform that will be built incrementally.

## Scope
- **Audience:** Consulting clients (whitespace = opportunity for client engagements / offerings)
- **Industries (wave 1):** Public Sector, Education, Nonprofit, Hospitality
- **Model depth:** L1 Domain → L2 Capability Group → L3 Capability
- **View:** Business capabilities only
- **Reference baseline:** APQC PCF (cross-industry) + industry references (e.g., FEA BRM / Federal Integrated Business Framework, CAUDIT HERM / Ed-Fi, HTNG / OpenTravel); nonprofit derived from APQC + sector research
- **Sources:** Web research permitted; all scores and claims cite sources

## Scoring rubric
**Market Coverage (1–5)** — current automation/AI adoption for the capability in the sector
1. Largely manual (paper, email, spreadsheets); AI adoption rare; few/no purpose-built AI products
2. Systems of record exist, little automation; isolated AI pilots
3. Workflow automation common; AI features in some mainstream products; moderate adoption
4. AI-enabled products mainstream; majority of mid/large orgs use them
5. Mature, commoditized AI automation widely deployed

**AI Readiness (1–5)** — feasibility of agentic AI today
1. Requires high judgment/physical presence, legal prohibition, or poor data
2. Significant barriers (highly sensitive data, policy constraints, inaccessible data)
3. Feasible with human-in-the-loop; data accessible with effort
4. Digital, document/text/rules-heavy; manageable regulation with HITL
5. Highly repeatable, digital, low-risk; proven LLM/agent patterns exist

**Whitespace Score** = AI Readiness × (6 − Market Coverage), range 1–25
- High ≥ 16 · Medium 9–15 · Low ≤ 8

## Accelerated solution path (HITL gate between every stage)
1. Whitespace Identification → 2. Pattern Selection → 3. Solution Blueprint & Reference Architecture → 4. Backlog & Agent Specification → 5. Factory Build (scaffold, code, test) → 6. Deploy & Operate

Outputs across the path: reference architectures, solution blueprints, user stories/backlogs, deployable scaffolds.

## Software factory
- Built over time (maturity roadmap)
- Agents span requirements, architecture, code generation, testing, deployment, operations
- Default constraints (assumed): cloud-agnostic; data residency and FedRAMP/StateRAMP/FERPA/PCI-aware controls; HITL mandatory; Claude as default model, swappable

## Agentic pattern library (shared tags)
P01 Document Intake & Extraction · P02 Eligibility / Rules Adjudication · P03 Case Triage & Routing · P04 Conversational Service Concierge · P05 Knowledge Retrieval & Policy Q&A · P06 Drafting & Content Generation · P07 Compliance Monitoring & Audit Evidence · P08 Forecasting & Resource Optimization · P09 Anomaly / Fraud / Risk Detection · P10 Cross-System Workflow Orchestration · P11 Personalized Guidance & Nudging · P12 Inspection & Field Operations Support · P13 Procurement & Vendor Analysis · P14 Stakeholder Feedback & Sentiment Synthesis

## Deliverable
Interactive HTML: cross-industry whitespace heatmap, drill-down L1–L3 model with scores and citations, top whitespace opportunities, pattern library, stage-gated framework, factory architecture and roadmap.

## Execution
Parallel research agents: one per industry + one for factory/pattern library → synthesis → HTML artifact.
