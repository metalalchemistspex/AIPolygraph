# AIPOL - AIPolygraph

AIPolygraph - Autonomous IR Agent

<img width="392" height="584" alt="image (6)" src="https://github.com/user-attachments/assets/ff46053d-4544-4183-9dee-46ee671a9a6b" />

# 🦙 AIPolygraph 2.0 - Autonomous Incident Response Agent

**FIND EVIL! AI Cybersecurity Hackathon 2026 Submission**

An autonomous AI-powered incident response system that combines 13 specialized detection modules with LLM-driven analysis to detect, triage, and respond to multi-vector cyber threats at machine speed.

---

## 🎯 Overview

AIPolygraph 2.0 is an autonomous incident response agent that processes security events through 13 specialized "Animal" detection modules, each targeting specific attack vectors, and uses a local LLM (Ollama + Llama 3.1) to generate executive-level incident reports with MITRE ATT&CK mapping.

---

## ✨ Key Capabilities

| Capability | Description |
|------------|-------------|
| **Autonomous Detection** | 13 specialized modules covering reconnaissance, exploitation, persistence, and data exfiltration |
| **Self-Correcting Analysis** | LLM-powered incident correlation with rule-based fallback |
| **Immutable Forensics** | Evidence preservation with cryptographic hashing (SHA-256) |
| **Real-Time Response** | Automated containment actions (IP blocking, account lockdown, process quarantine) |
| **MITRE ATT&CK Mapping** | Automatic tactic identification for SOC integration |
| **Rate Limiting Protection** | Built-in DDoS/scanning mitigation (20 events/IP/sec) |

---

## 🏗️ Architecture
<img width="389" height="387" alt="Architecture_Diagram_ AiPol" src="https://github.com/user-attachments/assets/045f3aff-315f-4090-ab4d-a4d819f6d5a3" />

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- Ollama (for LLM analysis) - Download from https://ollama.com/download
- Llama 3.1 model - Run: `ollama pull llama3.1:8b`

### Installation
Clone the repository

### Example Output
======================================================================
LLM SIFT ANALYST - INCIDENT REPORT
======================================================================
Time: 2026-06-15T23:25:39
Total alerts: 8
----------------------------------------------------------------------
SEVERITY SCORE: 8/10
ATTACK PATTERN: Lateral Movement, Brute Force
Analysis Method: ollama_llama3.1:8b
----------------------------------------------------------------------
EXECUTIVE SUMMARY:
   Multiple security incidents detected across the network.
   Threat actors may be attempting to gain unauthorized access
   and persistence.
----------------------------------------------------------------------
MITRE ATT&CK TACTICS:
   • T1110: Brute Force
   • T1021: Remote Services
   • T1190: Exploit Public Application
----------------------------------------------------------------------
RECOMMENDED ACTIONS:
   1. Investigate Hobotnica/Octopus and Školjka/Shell modules
   2. Isolate affected accounts
   3. Implement multi-factor authentication
======================================================================

AIPolygraph2.0/
├── app.py                    # Main application
├── aipolygraph.db            # SQLite database (auto-generated)
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── LICENSE                   # MIT License
├── execution_log.txt         # Agent execution logs
├── isolation_log.txt         # Simulated isolation logs
├── meduza_immutable.log      # Immutable forensic log
└── architecture_diagram_AiPol.png  # Architecture diagram

### Technologies Used
Category	Technologies
Language	Python 3.8+
Database	SQLite (WAL mode)
LLM	Ollama + Llama 3.1:8b
Security	SHA-256 hashing, MITRE ATT&CK
Platform	Windows 10/11, Linux (SIFT compatible)

### Demo Attack Simulation
The system includes a built-in test that simulates 13 attack events:

Event Type	Module Triggered	Response
HTTP request (no auth)	Školjka	IP block
Login failures (3x)	Hobotnica	Account lock
WMI subscription	Kornjača	Host quarantine
File modification	Termit	Auto-restore
Log tampering	Meduza	Immutable storage
SQL error response	Krtica	IP block
Compromised email	Hvatač snova	Password reset
RWX memory region	Jegulja	Memory dump

### Requirements
requirements.txt

### License
This project is licensed under the MIT License - see the LICENSE file for details.

### Author
Created for SANS FIND EVIL! AI Cybersecurity Hackathon 2026

### Find evil at machine speed. 


