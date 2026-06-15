# AIPOL - AIPolygraph

AIPolygraph - Autonomous IR Agent

<img width="392" height="584" alt="image (6)" src="https://github.com/user-attachments/assets/ff46053d-4544-4183-9dee-46ee671a9a6b" />

# 🛡️ AIPolygraph 2.0 - Autonomous Incident Response Agent

**FIND EVIL! AI Cybersecurity Hackathon 2026 Submission**

An autonomous AI-powered incident response system that combines 13 specialized detection modules with LLM-driven analysis to detect, triage, and respond to multi-vector cyber threats at machine speed.

---

## 🎯 Overview

AIPolygraph 2.0 is an autonomous incident response agent built for the SANS SIFT Workstation environment. It processes security events through 13 specialized "Animal" detection modules, each targeting specific attack vectors, and uses a local LLM (Ollama + LLaMA 3.1) to generate executive-level incident reports with MITRE ATT&CK mapping.

### Key Capabilities
- **Autonomous Detection**: 13 specialized modules covering reconnaissance, exploitation, persistence, and data exfiltration
- **Self-Correcting Analysis**: LLM-powered incident correlation with rule-based fallback
- **Immutable Forensics**: Evidence preservation with cryptographic hashing (SHA-256)
- **Real-Time Response**: Automated containment actions (IP blocking, account lockdown, process quarantine)
- **MITRE ATT&CK Mapping**: Automatic tactic identification for SOC integration
- **Rate Limiting Protection**: Built-in DDoS/scanning mitigation (20 events/IP/sec)

---

## 🏗️ Architecture
┌─────────────────────────────────────────────────────────────┐
│ AIPolygraph Orchestrator │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ Event Processing Pipeline │ │
│ │ Rate Limiting → Module Detection → Response Actions │ │
│ └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
↓
┌─────────────────────────────────────────┐
│ 13 Animal Detection Modules │
├─────────────────────────────────────────┤
│ 🦉 Sova - Rate limiting/Scanning │
│ 🐚 Školjka - WAF/Auth bypass │
│ 🕷️ Pauk - Shadow IT/Injection │
│ 🕸️ Paučina - Network flow analysis │
│ 🐜 Termit - File integrity (FIM) │
│ 🐢 Kornjača - Persistence mechanisms │
│ 🐦 Kolibri - Process entropy │
│ 🐙 Hobotnica - Brute force detection │
│ 🐍 Jegulja - RWX memory regions │
│ 🪼 Meduza - Log tampering │
│ 🌾 Prašina - Historical log analysis │
│ 🕸️ Hvatač snova - Credential breaches │
│ 🐹 Krtica - Error-based injection │
└─────────────────────────────────────────┘
↓
┌─────────────────────────────────────────┐
│ SIFT Forensic Collector │
│ (SQLite-based event aggregation) │
│ Database: aipolygraph.db (WAL mode) │
└─────────────────────────────────────────┘
↓
┌─────────────────────────────────────────┐
│ 🦙 LLM SIFT Analyst (Ollama) │
│ • Severity scoring (1-10) │
│ • Attack pattern classification │
│ • MITRE ATT&CK mapping │
│ • Executive summary generation │
│ • Rule-based fallback (offline mode) │
│ • Model: llama3.1:8b (local) │
└─────────────────────────────────────────┘
