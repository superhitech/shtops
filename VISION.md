# SHTops: Operational Independence Platform

## Core Thesis

**Own your context, own your choices.**

SHTops is not a dashboard. It is an operational independence layer that aggregates context from every system SuperHiTech depends on, makes that context queryable by humans and LLMs, and enables controlled automation—all without creating new lock-in.

The goal is simple: stop being trapped by the tools that were supposed to help you.

---

## The Problem

Every all-in-one platform follows the same arc:

1. Solves a real pain point
2. Becomes the place where context lives
3. Adds lock-in through integrations, history, and workflow dependency
4. Raises prices, stagnates features, restricts choices
5. Switching costs make leaving painful

RepairShopr. Vendor-locked payment processors. Monitoring tools that don't talk to each other. The pattern repeats.

**The escape is always the same:** build a layer you control, pull data out via API, reduce daily dependency, replace when ready—or don't, but now it's your choice.

---

## Three Layers

Build in this order. Each layer enables the next.

### 1. Context Layer

**Purpose:** Aggregate data from all systems into one queryable source of truth.

**Principle:** Read everything, depend on nothing.

| System | What it provides |
|--------|------------------|
| LibreNMS | Alerts, performance metrics, device health |
| Proxmox | VM state, cluster health, resource utilization |
| FreePBX | Call metrics, trunk health, PBX status |
| UniFi / UISP | Network device state, firmware versions |
| Hudu | Documentation, asset records, runbooks |
| RepairShopr | Tickets, customer history, invoices |
| QuickBooks | Financial data, payment records |
| Virtualmin | Web/email service health, SSL status |
| Backup systems | Job status, backup age, errors |

The context layer does not replace these systems. It indexes them.

### 2. Intelligence Layer

**Purpose:** LLM interface across all business planes.

**Principle:** Context makes the LLM useful; the LLM makes you faster.

The LLM is only as good as the context it can access. Once the context layer exists, the LLM can reason across domains:

| Business Plane | What the LLM can do |
|----------------|---------------------|
| Triage | Correlate alerts with recent changes, surface similar past incidents |
| Purchasing | Cross-reference asset lifecycle, warranty status, budget |
| Building | Reference existing topology, standards, past decisions |
| Automation | Identify manual processes worth automating, estimate ROI |
| Preventative Maintenance | Flag aging hardware, firmware drift, backup gaps |
| Business (high-level) | Morning briefings, trend summaries, risk highlights |

### 3. Automation Layer

**Purpose:** Controlled actions with guardrails.

**Principle:** Automate the boring, protect the dangerous.

Risk tiers:

| Risk Level | Examples | Guardrails |
|------------|----------|------------|
| **Low** | Linux updates, log rotation, service restarts, snapshots | Scheduled, logged |
| **Medium** | Proxmox rolling updates, VM migrations, PBX restarts | Time windows, pre-checks, backoff |
| **High** | Firewall firmware, router firmware, core PBX modules | Manual confirmation required |

All automation follows:
1. Pre-check
2. Execute
3. Validate
4. Rollback (where possible)
5. Log to Hudu

---

## Interaction Models

Multiple interfaces, one shared context.

| Interface | Use case |
|-----------|----------|
| **VS Code + Copilot** | Building, debugging, querying while coding. `@shtops what's the cluster state?` |
| **Dashboard chat** | Triage, investigation, visual context. "Why is this host alerting?" |
| **Slack/Teams bot** | Quick lookups away from workbench. "What needs updates this week?" |
| **CLI** | Scriptable, fast. `shtops ask "what needs attention?"` |
| **Ambient/Proactive** | Morning briefing pushed to you. "Three things worth attention today." |

The key: conversations persist across interfaces. Start in Slack, continue in VS Code, reference yesterday's triage in today's briefing.

---

## Decision Filter

Before building any feature or integration, ask:

1. **Does this add context I don't currently have unified access to?**
2. **Does this reduce dependency on a system I don't control?**
3. **Does this eliminate recurring manual work?**
4. **Can I build it without creating new lock-in?**

If it doesn't hit at least one, it's not a priority.

---

## Strategic Arc: Escaping Lock-In

The pattern applies everywhere:

| Domain | Locked system | SHTops role | End state |
|--------|---------------|-------------|-----------|
| Monitoring | Fragmented tools | Unified context layer | Single pane of glass |
| Documentation | Tribal knowledge | Hudu sync + LLM queryable | Living, accurate docs |
| CRM/Ticketing | RepairShopr | RS becomes data source | Replace when ready |
| Payments | RS-forced processor | Reconciliation automation | Choose any provider |
| Automation | Manual toil | Guardrailed orchestration | Predictable, logged ops |

You don't rip out locked systems. You reduce dependency until switching is a choice, not a crisis.

---

## Traps to Avoid

### "Building a better dashboard"
The dashboard is a view. The value is the context layer underneath and the LLM that reasons over it. Don't obsess over UI.

### "Boiling the ocean"
You don't need every collector on day one. Start with the systems that cause the most pain or have the most operational value. Expand from there.

### "Automating too early"
Read-only first. Understand what the data tells you before you start acting on it automatically. Premature automation creates new problems.

### "Creating new lock-in"
If SHTops becomes the thing you can't escape, you've failed. Keep it modular. Keep the data exportable. Own your own context.

---

## MVP: What to Build First

1. **Context layer foundation**
   - Collectors for: LibreNMS, Proxmox, FreePBX, UniFi
   - JSON state cache with defined TTLs
   - Python API clients for core systems

2. **Basic dashboard**
   - System tiles showing health summary
   - Update/reboot detection (read-only)
   - Links to native UIs

3. **Hudu sync**
   - Push inventory and basic attributes
   - Keep documentation current automatically

4. **LLM integration (simple)**
   - Chat panel in dashboard
   - Access to cached state
   - Natural language queries against current system status

---

## Principles

1. **Systems remain fully functional without SHTops.** It's an overlay, not a dependency.

2. **Read-only first, automation second.** Understand before you act.

3. **No destructive automation without human confirmation.** Guardrails are not optional.

4. **Separate concerns.** Dashboard, automation engine, and execution plane are distinct.

5. **Version control everything.** Code, config, and decisions live in Git.

6. **Document as you go.** If it's not in Hudu, it didn't happen.

---

## Why This Matters

A junior tech should be able to use SHTops to safely maintain the environment.

You should be able to answer "what needs attention?" in 30 seconds.

When a vendor raises prices or kills a feature, you should be able to leave.

That's operational independence.
