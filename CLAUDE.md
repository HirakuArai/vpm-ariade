# CLAUDE.md

## 🧠 AI-First Philosophy (ABSOLUTE RULE - NEVER VIOLATE)

**🔥 CRITICAL: This is a TRUE AI-FIRST Virtual Project Manager**

### ❌ FORBIDDEN (Non-AI Elements):
* Pattern matching: `if "keyword" in user_input`  
* Complex conditional chains: `if/elif/elif/else`
* Hardcoded rules or predefined patterns
* Fixed response mappings

### ✅ REQUIRED (True AI Elements):
* Unified AI decision making for ALL user interactions
* Contextual understanding over surface-level keywords  
* Learning from every conversation
* Emergent responses to novel situations

**📖 Complete guidelines: docs/AI_FIRST_PHILOSOPHY.md**

---

## 🌟 North Star

Kai VPM delivers an **idempotent, self‑evolving AI Project Manager** that can turn any vague human intention into a well‑defined project, guide it with consistent prioritisation and risk awareness, and learn from every outcome while keeping the system continuously usable.

### Core Principles

1. **Universality** – Every goal, from daily chores to large programmes, is treated as a project.
2. **Persona‑First** – Understanding & judgement outrank automation; execution plugins remain replaceable.
3. **Transparency** – All constraints, decisions and artefacts live as human‑readable files tracked in Git.
4. **Incremental Evolution** – The system rewrites itself module‑by‑module without downtime.

---

## 🏛️ Architectural Layers

| Layer                   | Purpose                                     | Key Artefacts                                               |
| ----------------------- | ------------------------------------------- | ----------------------------------------------------------- |
| **Meta (Framework)**    | Define what a *project* is                  | `core/v2/charter_schema.yaml`, lifecycle DSL, doc templates |
| **Persona (Judgement)** | Convert Charter into priorities, risks, WBS | `persona/decision_core.py`                                  |
| **Agent (Execution)**   | Optional automation plugins                 | `plugins/*`, connectors                                     |

**Compatibility Rule**  Everything currently in `core/` & `scripts/` is **v1 (legacy)**. New code lands in `core/v2/` and may call legacy until migration is finished.

---

## 🔄 Lifecycle Overview

```
Define  →  Instantiate Persona  →  Plan  →  Operate  →  Review
(Stage‑0)     (Boot)              (P2)     (P3)        (P4)
```

### Definition Phase (Stage‑0 & Stage‑1)

1. **Hearing (Stage‑0)** – The AI interviews the user in natural language.
2. **Charter Generation (Stage‑1)** – Answers are mapped to `charter_YYYYMMDD.yaml` following the schema below.

```yaml
# core/v2/charter_schema.yaml
name:
purpose:
outcomes:
scope:
  in:
  out:
stakeholders:
constraints:
  budget:
  deadline:
  tools:
milestones:
success_metrics:
risks:
```

The helper script `scripts/gen_charter.py` conducts the dialogue, writes the file, and commits it.

---

## 🗺️ Migration Roadmap (v1 ➜ v2)

| Milestone | Target                                                     | Completion Criteria                  |
| --------- | ---------------------------------------------------------- | ------------------------------------ |
| **M0**    | Charter schema & generator committed                       | `pytest tests/test_charter.py` green |
| **M1**    | Persona v2 reads Charter and returns priorities/risks JSON | `tests/test_persona.py` green        |
| **M2**    | Streamlit UI shows Charter + Persona output                | smoke test passes                    |
| **M3**    | Legacy decision code fully replaced                        | no `core/` legacy import remains     |

All new modules **must** live under `core/v2/` or `persona/`, and be registered in `docs/kai_capabilities.json` when production‑ready.

---

## 🔧 Claude Code Directives

* Run `claude-code map --ignore core/v2/` to analyse legacy dependencies.
* Propose PRs that **move or rewrite one module at a time** into v2.
* Never modify `charter_schema.yaml` without a PR titled `schema-change:` and an accompanying migration script.
* Keep public APIs (`run_kai_self_check`, `append_log`, …) stable during migration.

## 🤖 AI Model Requirements (ABSOLUTE)

**🚨 CRITICAL: GPT-4.1 ONLY - NO EXCEPTIONS**

* ALL OpenAI API calls MUST use GPT-4.1 exclusively
* Import `get_openai_model()` from `core.v2.openai_config` - never hardcode models
* Use `create_chat_completion()` for consistent API calls
* Any deviation from GPT-4.1 will cause system failure
* This requirement is absolute and must be maintained for ALL future additions

---

## 📜 Git & Docs Rules (inherited)

* **1 document = 1 commit**.
* Four information categories: 常時参照型 / オンデマンド参照型 / 再構成型 / 生成型.
* Code changes must be mirrored by DSL or doc updates when applicable.

---

*Last updated: 2025‑06‑07 (v2 charter‑first migration kick‑off)*
