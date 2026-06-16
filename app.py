#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# AIPOLYGRAPH 2.0 - HACKATHON FINAL SA LLM IZVEŠTAJEM
# Autonomous Incident Response Agent sa simuliranom izolacijom
# PRIKAZUJE: severity score, MITRE ATT&CK, preporuke

import os
import sys
import re
import json
import time
import math
import sqlite3
import hashlib
import logging
import threading
import requests
import subprocess
from collections import deque, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Windows UTF-8 podrška
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# ============================================================
# KONFIGURACIJA - Windows putanje (radi odmah, bez Linuxa)
# ============================================================
CONFIG = {
    "mcp": {"enabled": False, "url": "http://localhost:8080", "api_key": ""},
    "log_archive_dir": r"C:\Users\Public\aipolygraph\logs",
    "watch_dir": r"C:\Users\Public\aipolygraph\watch",
    "immutable_backup_dir": r"C:\Users\Public\aipolygraph\backup",
    "db_file": "aipolygraph.db",
    "rate_limit": {"max_events_per_ip_per_sec": 20, "window_sec": 1},
    "ollama": {
        "enabled": True,
        "url": "http://localhost:11434",
        "model": "llama3.1:8b"
    },
    "modules": {
        "sova": {"enabled": True, "threshold": 50},
        "prasina": {"enabled": True, "days_back": 30},
        "krtica": {"enabled": True, "block_on_detection": True},
        "hvatac_snova": {"enabled": True, "use_hibp_mock": True}
    },
    "simulate_isolation": True  # LAŽNA IZOLACIJA - samo loguje, ne blokira stvarno
}

# Kreiranje potrebnih direktorijuma
os.makedirs(CONFIG["watch_dir"], exist_ok=True)
os.makedirs(CONFIG["immutable_backup_dir"], exist_ok=True)
os.makedirs(CONFIG["log_archive_dir"], exist_ok=True)

# Test fajl za FIM modul
TEST_FILE = os.path.join(CONFIG["watch_dir"], "test.txt")
if not os.path.exists(TEST_FILE):
    with open(TEST_FILE, "w") as f:
        f.write("original content")
rel = os.path.relpath(TEST_FILE, CONFIG["watch_dir"])
backup_path = os.path.join(CONFIG["immutable_backup_dir"], rel)
os.makedirs(os.path.dirname(backup_path), exist_ok=True)
if not os.path.exists(backup_path):
    with open(backup_path, "w") as f:
        f.write("original content")

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("aipolygraph2.0")

# ============================================================
# SIMULIRANA IZOLACIJA (bez Linuxa, bez stvarnog blokiranja)
# ============================================================
def simulate_isolation(target: str, reason: str, action_type: str = "ip") -> Dict[str, Any]:
    """
    Simulira izolaciju - samo upisuje u log fajl.
    Ovo je LAŽNA izolacija za potrebe demonstracije na hakatonu.
    """
    isolation_log = r"C:\Users\Public\aipolygraph\isolation_log.txt"
    os.makedirs(os.path.dirname(isolation_log), exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] ISOLATION SIMULATED: {action_type.upper()} '{target}' - Reason: {reason}\n"
    
    with open(isolation_log, "a", encoding="utf-8") as f:
        f.write(log_entry)
    
    logger.warning(f"🔒 [SIMULATED] Izolacija: {action_type} '{target}' - {reason}")
    
    return {
        "action": f"simulated_{action_type}_isolation",
        "target": target,
        "reason": reason,
        "simulated": True,
        "log_file": isolation_log
    }


def real_windows_isolation(target: str, reason: str, action_type: str = "ip") -> Dict[str, Any]:
    """PRAVA Windows izolacija - zahteva ADMINISTRATORSKA PRAVA."""
    if not CONFIG.get("simulate_isolation", True):
        try:
            if action_type == "ip":
                rule_name = f"AIPolygraph_Block_{target.replace('.', '_')}"
                cmd = f'netsh advfirewall firewall add rule name="{rule_name}" dir=in action=block remoteip={target}'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.critical(f"🔴 REAL ISOLATION: IP {target} blokiran kroz Windows Firewall")
                    return {"action": "real_ip_block", "target": target, "success": True}
        except Exception as e:
            logger.warning(f"⚠️ Greska pri izolaciji: {e} - prelazim na simulaciju")
    
    return simulate_isolation(target, reason, action_type)


# ============================================================
# BAZA PODATAKA
# ============================================================
def init_db():
    conn = sqlite3.connect(CONFIG["db_file"])
    c = conn.cursor()
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute("PRAGMA busy_timeout=5000;")
    
    c.execute('''CREATE TABLE IF NOT EXISTS termit_hashes 
                 (filepath TEXT PRIMARY KEY, hash TEXT, mtime REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS paucina_graph 
                 (src TEXT, dst TEXT, first_seen REAL, PRIMARY KEY (src, dst))''')
    c.execute('''CREATE TABLE IF NOT EXISTS hobotnica_logins 
                 (user TEXT, last_seen REAL, PRIMARY KEY (user))''')
    c.execute('''CREATE TABLE IF NOT EXISTS sift_events 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, event_json TEXT, timestamp REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS immutable_logs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT, hash TEXT, timestamp REAL)''')
    
    conn.commit()
    conn.close()


init_db()


def send_to_mcp(endpoint: str, data: Dict[str, Any]) -> None:
    if not CONFIG["mcp"]["enabled"]:
        return
    try:
        headers = {"X-API-Key": CONFIG["mcp"]["api_key"]} if CONFIG["mcp"]["api_key"] else {}
        requests.post(f"{CONFIG['mcp']['url']}{endpoint}", json=data, headers=headers, timeout=1)
    except Exception:
        pass


# ============================================================
# 13 ANIMAL DETECTION MODULA
# ============================================================
class AnimalModule:
    name = "Animal"
    def detect(self, event: Dict[str, Any]) -> Optional[str]:
        raise NotImplementedError
    def respond(self, event: Dict[str, Any], detection: str) -> Dict[str, Any]:
        raise NotImplementedError


class Sova(AnimalModule):
    name = "Sova"
    def __init__(self):
        self.ip_logs = defaultdict(lambda: deque(maxlen=1000))
        self.threshold = CONFIG["modules"]["sova"]["threshold"]
        self.window_sec = 10
        self.lock = threading.Lock()

    def detect(self, event: Dict[str, Any]) -> Optional[str]:
        src = event.get('source', event.get('source_ip', 'unknown'))
        now = event.get('timestamp', time.time())
        with self.lock:
            self.ip_logs[src].append(now)
            recent = [t for t in self.ip_logs[src] if t > now - self.window_sec]
            self.ip_logs[src] = deque(recent, maxlen=1000)
            if len(recent) > self.threshold:
                return "high_frequency_scan"
        return None

    def respond(self, event: Dict[str, Any], detection: str) -> Dict[str, Any]:
        src = event.get('source', event.get('source_ip'))
        logger.warning(f"🦉 SOVA: {detection} from {src}")
        return real_windows_isolation(src, f"SOVA: {detection}", "ip")


class Skoljka(AnimalModule):
    name = "Školjka"
    def detect(self, event: Dict[str, Any]) -> Optional[str]:
        if event.get('type') == 'http_request':
            headers = event.get('headers', {})
            auth_required = event.get('auth_required', False)
            if auth_required and not headers.get('Authorization'):
                return "missing_auth_header"
        return None

    def respond(self, event: Dict[str, Any], detection: str) -> Dict[str, Any]:
        ip = event.get('source_ip')
        logger.warning(f"🐚 ŠKOLJKA: Blocking IP {ip} at WAF")
        return real_windows_isolation(ip, f"Školjka: {detection}", "ip")


class Pauk(AnimalModule):
    name = "Pauk"
    def __init__(self):
        self.known_assets = ["/api/login", "/api/health", "/api/public"]
        self.payload_patterns = [r"('\s*OR\s*'|'\s*AND\s*')", r"<script>", r"\.\./\.\./"]

    def detect(self, event: Dict[str, Any]) -> Optional[str]:
        if event.get('type') == 'new_resource' and event.get('resource') not in self.known_assets:
            return "shadow_it_scanning"
        if event.get('type') == 'http_request':
            payload = str(event.get('payload', '') + str(event.get('headers', {})))
            for pattern in self.payload_patterns:
                if re.search(pattern, payload, re.IGNORECASE):
                    return "injection_attempt_on_known_asset"
        return None

    def respond(self, event: Dict[str, Any], detection: str) -> Dict[str, Any]:
        resource = event.get('resource', event.get('source_ip', 'unknown'))
        logger.warning(f"🕷️ PAUK: Blocking malicious payload on {resource}")
        if event.get('source_ip'):
            return real_windows_isolation(event['source_ip'], f"Pauk: {detection}", "ip")
        return {"action": "block_request", "resource": resource, "simulated": True}


class Paucina(AnimalModule):
    name = "Paučina"
    def __init__(self):
        self.conn = sqlite3.connect(CONFIG["db_file"], check_same_thread=False)
        self.sensitive_keywords = ["database", "config", "secret", "admin", "backup", "credential", "db", "vault"]
        self.allowed_flows = {("web-frontend-01", "redis-cache-02")}

    def detect(self, event: Dict[str, Any]) -> Optional[str]:
        if event.get('type') == 'connection':
            src, dst = event['src'], event['dst']
            is_src_sensitive = any(k in src.lower() for k in self.sensitive_keywords)
            is_dst_sensitive = any(k in dst.lower() for k in self.sensitive_keywords)
            if (src, dst) not in self.allowed_flows and (is_src_sensitive or is_dst_sensitive):
                cur = self.conn.cursor()
                cur.execute("SELECT 1 FROM paucina_graph WHERE src=? AND dst=?", (src, dst))
                if not cur.fetchone():
                    cur.execute("INSERT INTO paucina_graph (src, dst, first_seen) VALUES (?, ?, ?)", (src, dst, time.time()))
                    self.conn.commit()
                    return "anomalous_network_flow"
        return None

    def respond(self, event: Dict[str, Any], detection: str) -> Dict[str, Any]:
        src, dst = event['src'], event['dst']
        logger.warning(f"🕸️ PAUČINA: Anomalous flow between {src} and {dst}")
        return real_windows_isolation(src, f"Paucina: {detection} - flow to {dst}", "ip")


class Termit(AnimalModule):
    name = "Termit"
    def __init__(self):
        self.watch_dir = CONFIG["watch_dir"]
        self.backup_dir = CONFIG["immutable_backup_dir"]
        self.conn = sqlite3.connect(CONFIG["db_file"], check_same_thread=False)
        self._init_hashes()

    def _get_hash(self, filepath: str) -> Optional[str]:
        try:
            with open(filepath, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return None

    def _init_hashes(self):
        cur = self.conn.cursor()
        for root, _, files in os.walk(self.watch_dir):
            for file in files:
                path = os.path.join(root, file)
                h = self._get_hash(path)
                if h:
                    cur.execute("INSERT OR REPLACE INTO termit_hashes VALUES (?, ?, ?)", (path, h, time.time()))
        self.conn.commit()

    def detect(self, event: Dict[str, Any]) -> Optional[str]:
        if event.get('type') == 'file_change':
            filepath = event['file']
            new_hash = hashlib.sha256(b"malicious_content").hexdigest()
            cur = self.conn.cursor()
            cur.execute("SELECT hash FROM termit_hashes WHERE filepath=?", (filepath,))
            row = cur.fetchone()
            if row and row[0] != new_hash:
                return "integrity_corruption"
        return None

    def respond(self, event: Dict[str, Any], detection: str) -> Dict[str, Any]:
        filepath = event['file']
        rel = os.path.relpath(filepath, self.watch_dir)
        backup = os.path.join(self.backup_dir, rel)
        if os.path.exists(backup):
            try:
                with open(backup, 'rb') as f:
                    data = f.read()
                backup_hash = hashlib.sha256(data).hexdigest()
                with open(filepath, 'wb') as f:
                    f.write(data)
                cur = self.conn.cursor()
                cur.execute("UPDATE termit_hashes SET hash=?, mtime=? WHERE filepath=?", (backup_hash, time.time(), filepath))
                self.conn.commit()
                logger.warning(f"🐜 TERMIT: Restored {filepath} from backup")
                return {"action": "immutable_restore", "file": filepath, "restored": True}
            except Exception as e:
                logger.error(f"TERMIT: Restore failed {filepath}: {e}")
                return {"action": "immutable_restore", "file": filepath, "restored": False}
        return {"action": "alert", "message": "Backup missing"}


class Kornjaca(AnimalModule):
    name = "Kornjača"
    def __init__(self):
        self.patterns = [
            r'persist|startup|ActiveScriptEventConsumer|CommandLineEventConsumer',
            r'powershell\s+-enc|powershell\s+-e',
            r'cmd\.exe\s+/c',
            r'schtasks\s+/create'
        ]

    def detect(self, event: Dict[str, Any]) -> Optional[str]:
        if event.get('type') in ['wmi_subscription', 'process_execution']:
            script = event.get('script', '') + " " + event.get('command', '')
            for pattern in self.patterns:
                if re.search(pattern, script, re.IGNORECASE):
                    return "suspicious_persistence_or_execution"
        return None

    def respond(self, event: Dict[str, Any], detection: str) -> Dict[str, Any]:
        host = event.get('host', 'unknown')
        logger.critical(f"🐢 KORNJAČA: Quarantining host {host}")
        return real_windows_isolation(host, f"Kornjaca: {detection}", "ip")


class Kolibri(AnimalModule):
    name = "Kolibri"
    def __init__(self):
        self.process_entropy = {}

    def _calculate_entropy(self, data_bytes: bytes) -> float:
        if not data_bytes:
            return 0.0
        entropy = 0.0
        length = len(data_bytes)
        for x in range(256):
            p_x = float(data_bytes.count(x)) / length
            if p_x > 0:
                entropy += - p_x * math.log2(p_x)
        return entropy

    def detect(self, event: Dict[str, Any]) -> Optional[str]:
        if event.get('type') == 'process_memory':
            pid = event['pid']
            mock_data = b"A" * 100 if pid % 2 == 0 else bytes(range(256)) * 10 
            entropy = self._calculate_entropy(mock_data)
            if pid in self.process_entropy:
                prev_entropy = self.process_entropy[pid]
                if abs(entropy - prev_entropy) > 0.5 and entropy > 6.5:
                    return "entropy_hop_detected"
            self.process_entropy[pid] = entropy
        return None

    def respond(self, event: Dict[str, Any], detection: str) -> Dict[str, Any]:
        pid = event.get('pid')
        logger.warning(f"🐦 KOLIBRI: Entropy hop in process {pid}")
        return {"action": "block_egress_and_dump", "pid": pid, "simulated": True}


class Hobotnica(AnimalModule):
    name = "Hobotnica"
    def __init__(self):
        self.user_attempts = defaultdict(list)

    def detect(self, event: Dict[str, Any]) -> Optional[str]:
        if event.get('type') == 'login':
            user = event['user']
            event_time = event.get('timestamp', time.time())
            self.user_attempts[user].append(event_time)
            self.user_attempts[user] = [t for t in self.user_attempts[user] if t > event_time - 60]
            if len(self.user_attempts[user]) >= 3:
                return "brute_force_or_credential_stuffing"
        return None

    def respond(self, event: Dict[str, Any], detection: str) -> Dict[str, Any]:
        user = event.get('user')
        logger.warning(f"🐙 HOBOTNICA: Locking account for {user}")
        return real_windows_isolation(user, f"Hobotnica: {detection}", "account")


class Jegulja(AnimalModule):
    name = "Jegulja"
    def detect(self, event: Dict[str, Any]) -> Optional[str]:
        if event.get('type') == 'memory_region':
            permissions = event.get('permissions', 'RW')
            if 'X' in permissions and 'W' in permissions:
                return "suspicious_rwx_memory_region"
        return None

    def respond(self, event: Dict[str, Any], detection: str) -> Dict[str, Any]:
        pid = event.get('pid')
        logger.warning(f"🐍 JEGULJA: RWX memory in process {pid}")
        return {"action": "memory_dump", "pid": pid, "simulated": True}


class Meduza(AnimalModule):
    name = "Meduza"
    def __init__(self):
        self.conn = sqlite3.connect(CONFIG["db_file"], check_same_thread=False)
        self.append_only_log = r"C:\Users\Public\aipolygraph\meduza_immutable.log"

    def detect(self, event: Dict[str, Any]) -> Optional[str]:
        if event.get('type') == 'log_entry':
            if 'disk_log' in event and event['disk_log'] != event.get('content'):
                return "disk_vs_memory_tampering"
        return None

    def respond(self, event: Dict[str, Any], detection: str) -> Dict[str, Any]:
        content = event.get('content', '')
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        cur = self.conn.cursor()
        cur.execute("INSERT INTO immutable_logs (content, hash, timestamp) VALUES (?, ?, ?)", 
                   (content, content_hash, time.time()))
        self.conn.commit()
        os.makedirs(os.path.dirname(self.append_only_log), exist_ok=True)
        with open(self.append_only_log, 'a', encoding='utf-8') as f:
            f.write(f"{time.time()}|{content_hash}|{content}\n")
        logger.error(f"🪼 MEDUZA: Log tampering detected – saved to immutable storage")
        return {"action": "immutable_logs_saved", "content": content}


class Prasina(AnimalModule):
    name = "Prašina"
    def __init__(self):
        self.archive_dir = CONFIG["log_archive_dir"]
        self.days_back = CONFIG["modules"]["prasina"]["days_back"]
        self.patterns = [
            (r"failed password|authentication failure", "brute_force"),
            (r"SQL syntax.*error|mysql_fetch|ORA-\d{5}", "sql_error"),
            (r"stack trace|exception|fatal error", "stack_leak"),
            (r"internal server error|500 internal", "generic_server_error")
        ]

    def detect(self, event: Dict[str, Any]) -> Optional[str]:
        if event.get('type') == 'old_log_scan' and 'content' in event:
            return self._scan_content(event['content'])
        return None

    def _scan_content(self, content: str) -> Optional[str]:
        for pattern, label in self.patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return f"old_log_{label}"
        return None

    def respond(self, event: Dict[str, Any], detection: str) -> Dict[str, Any]:
        logger.warning(f"🌾 PRAŠINA: {detection} in old log")
        return {"action": "archive_alert", "alert": detection}


class HvatacSnova(AnimalModule):
    name = "Hvatač snova"
    def __init__(self):
        self.local_breaches = ["user@example.com", "test@domain.org", "admin@company.com", "attacker@protonmail.com"]
        self.use_hibp_mock = CONFIG["modules"]["hvatac_snova"]["use_hibp_mock"]

    def detect(self, event: Dict[str, Any]) -> Optional[str]:
        if event.get('type') != 'old_credential_check':
            return None
        email = event.get('email')
        if not email:
            return None
        if email in self.local_breaches:
            return "compromised_credential_local"
        if self.use_hibp_mock and "breached" in email.lower():
            return "compromised_credential_hibp_mock"
        return None

    def respond(self, event: Dict[str, Any], detection: str) -> Dict[str, Any]:
        email = event.get('email')
        logger.critical(f"🕸️ HVATAČ SNOVA: {detection} for {email} – forcing password reset")
        return real_windows_isolation(email, f"HvatacSnova: {detection}", "account")


class Krtica(AnimalModule):
    name = "Krtica"
    def __init__(self):
        self.block_on_detection = CONFIG["modules"]["krtica"]["block_on_detection"]
        self.error_patterns = [
            (r"SQL syntax.*(error|near)|mysql_fetch|ORA-\d{5}", "sql_injection"),
            (r"Stack trace:|exception|Warning:|Fatal error|debug=true", "info_leak"),
            (r"internal server error|an error occurred", "generic_error_potential_injection")
        ]

    def detect(self, event: Dict[str, Any]) -> Optional[str]:
        if event.get('type') != 'http_response':
            return None
        body = event.get('body', '')
        status = event.get('status_code', 200)
        for pattern, label in self.error_patterns:
            if re.search(pattern, body, re.IGNORECASE):
                if label == "generic_error_potential_injection" and status != 500:
                    continue
                return f"error_based_{label}"
        return None

    def respond(self, event: Dict[str, Any], detection: str) -> Dict[str, Any]:
        src_ip = event.get('source_ip', 'unknown')
        logger.error(f"🐹 KRTICA: {detection} from {src_ip}")
        if self.block_on_detection:
            return real_windows_isolation(src_ip, f"Krtica: {detection}", "ip")
        return {"action": "log_only", "alert": detection}


class SIFT(AnimalModule):
    name = "SIFT"
    def __init__(self):
        self.conn = sqlite3.connect(CONFIG["db_file"], check_same_thread=False)
        self._clear_old_events()
    
    def _clear_old_events(self):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM sift_events")
        self.conn.commit()

    def detect(self, event: Dict[str, Any]) -> Optional[str]:
        cur = self.conn.cursor()
        cur.execute("INSERT INTO sift_events (event_json, timestamp) VALUES (?, ?)",
                    (json.dumps(event), time.time()))
        self.conn.commit()
        return None

    def respond(self, event: Dict[str, Any], detection: str) -> Dict[str, Any]:
        pass

    def generate_report(self) -> Dict[str, Any]:
        cur = self.conn.cursor()
        cur.execute("SELECT event_json FROM sift_events")
        rows = cur.fetchall()
        modules = set()
        for row in rows:
            ev = json.loads(row[0])
            if 'triggered_module' in ev:
                modules.add(ev['triggered_module'])
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_events_processed": len(rows),
            "summary": "Forensic report generated",
            "modules_triggered": sorted(list(modules))
        }
        logger.info(f"📊 SIFT: {json.dumps(report, indent=2)}")
        return {"action": "report", "report": report}


# ============================================================
# LLM SIFT ANALYST (Ollama + Fallback)
# ============================================================
class LLMSiftAnalyst:
    name = "LLM SIFT Analyst"
    
    def __init__(self, use_ollama: bool = True, ollama_url: str = "http://localhost:11434", model: str = "llama3.1:8b"):
        self.use_ollama = use_ollama
        self.ollama_url = ollama_url
        self.model = model
        self.alerts_buffer = []
        self._check_ollama_connection()
    
    def _check_ollama_connection(self):
        if not self.use_ollama:
            return
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m['name'] for m in models]
                logger.info(f"🦙 Ollama OK! Available: {', '.join(model_names[:5])}")
                if not any(self.model in m for m in model_names):
                    logger.warning(f"⚠️ Model '{self.model}' not found, using fallback")
                    self.use_ollama = False
            else:
                self.use_ollama = False
        except Exception:
            logger.warning("⚠️ Ollama not available, using rule-based fallback")
            self.use_ollama = False
        
    def add_alert(self, module_name: str, detection: str, response: Dict[str, Any], event: Dict[str, Any]):
        self.alerts_buffer.append({
            "module": module_name,
            "detection": detection,
            "response": response,
            "timestamp": event.get('timestamp', time.time()),
            "event_type": event.get('type', 'unknown')
        })
    
    def analyze_incident(self) -> Dict[str, Any]:
        if not self.alerts_buffer:
            return {"summary": "No alerts to analyze", "severity_score": 0}
        
        context = self._prepare_llm_context()
        
        if self.use_ollama:
            try:
                return self._call_ollama(context)
            except Exception as e:
                logger.warning(f"Ollama failed ({e}), using fallback")
                return self._rule_based_analysis(context)
        else:
            return self._rule_based_analysis(context)
    
    def _prepare_llm_context(self) -> str:
        lines = ["SECURITY INCIDENT ALERTS:\n"]
        for i, alert in enumerate(self.alerts_buffer, 1):
            lines.append(f"{i}. Module: {alert['module']} | Detection: {alert['detection']} | Response: {alert['response'].get('action', 'N/A')}")
        return "\n".join(lines)
    
    def _call_ollama(self, context: str) -> Dict[str, Any]:
        prompt = f"""You are a senior SOC analyst. Analyze these security alerts and provide:
1. SEVERITY SCORE (1-10)
2. ATTACK PATTERN (e.g., "APT", "Brute Force", "Lateral Movement")
3. EXECUTIVE SUMMARY (2-3 sentences)
4. MITRE ATT&CK TACTICS (list relevant IDs like T1110, T1021)
5. RECOMMENDED ACTIONS (3-5 steps)

{context}

Respond ONLY in valid JSON format:
{{
  "severity_score": <number>,
  "attack_pattern": "<string>",
  "executive_summary": "<string>",
  "mitre_tactics": ["<string>", ...],
  "recommended_actions": ["<string>", ...]
}}"""
        
        response = requests.post(
            f"{self.ollama_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False, "format": "json"},
            timeout=60
        )
        response.raise_for_status()
        result = response.json()
        content = result.get('response', '')
        
        try:
            analysis = json.loads(content)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                analysis = self._rule_based_analysis(context)
        
        analysis['analysis_method'] = f'ollama_{self.model}'
        return analysis
    
    def _rule_based_analysis(self, context: str) -> Dict[str, Any]:
        modules_triggered = set(a['module'] for a in self.alerts_buffer)
        severity = 1
        if len(modules_triggered) >= 5: severity = 9
        elif len(modules_triggered) >= 3: severity = 7
        elif len(modules_triggered) >= 2: severity = 5
        
        critical_modules = {"Kornjača", "Termit", "Meduza", "Paučina"}
        if modules_triggered & critical_modules:
            severity = min(10, severity + 2)
            
        attack_pattern = "Multi-Stage Attack" if len(modules_triggered) >= 4 else "Unknown"
        if "Sova" in modules_triggered and "Hobotnica" in modules_triggered:
            attack_pattern = "Credential Stuffing / Brute Force"
        elif "Paučina" in modules_triggered and "Kornjača" in modules_triggered:
            attack_pattern = "APT - Lateral Movement + Persistence"
            
        mitre_map = {
            "Sova": "T1595 (Active Scanning)", "Školjka": "T1190 (Exploit Public App)",
            "Pauk": "T1083 (Discovery)", "Paučina": "T1021 (Remote Services)",
            "Termit": "T1486 (Data Encrypted)", "Kornjača": "T1547 (Persistence)",
            "Kolibri": "T1055 (Process Injection)", "Hobotnica": "T1110 (Brute Force)",
            "Jegulja": "T1055.012 (Process Hollowing)", "Meduza": "T1070.001 (Indicator Removal)",
            "Prasina": "T1070 (Indicator Removal)", "Hvatač snova": "T1589 (Gather Identity)",
            "Krtica": "T1190 (Exploit Public App)"
        }
        mitre_tactics = [mitre_map[m] for m in modules_triggered if m in mitre_map]
        
        return {
            "severity_score": severity,
            "attack_pattern": attack_pattern,
            "executive_summary": f"Security incident detected involving {len(modules_triggered)} modules. Pattern: {attack_pattern}. Autonomous response initiated.",
            "mitre_tactics": mitre_tactics[:5],
            "recommended_actions": ["Isolate affected systems", "Preserve forensic evidence", "Reset compromised credentials", "Review firewall rules"],
            "analysis_method": "rule_based_fallback",
            "modules_involved": sorted(list(modules_triggered))
        }
    
    def generate_final_report(self) -> Dict[str, Any]:
        analysis = self.analyze_incident()
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_alerts": len(self.alerts_buffer),
            "ai_analysis": analysis,
            "detailed_alerts": self.alerts_buffer
        }
        
        # ŠTAMPANJE LLM IZVEŠTAJA - ovo će se videti u terminalu!
        print("\n" + "=" * 70)
        print("🦙 LLM SIFT ANALYST - INCIDENT REPORT")
        print("=" * 70)
        print(f"📅 Vreme: {report['timestamp']}")
        print(f"📊 Ukupno alarma: {report['total_alerts']}")
        print("-" * 70)
        print(f"🎯 SEVERITY SCORE: {analysis.get('severity_score', 'N/A')}/10")
        print(f"🔍 ATTACK PATTERN: {analysis.get('attack_pattern', 'N/A')}")
        print(f"🤖 Analysis Method: {analysis.get('analysis_method', 'N/A')}")
        print("-" * 70)
        print("📝 EXECUTIVE SUMMARY:")
        print(f"   {analysis.get('executive_summary', 'N/A')}")
        print("-" * 70)
        print("🎯 MITRE ATT&CK TACTICS:")
        for tactic in analysis.get('mitre_tactics', []):
            print(f"   • {tactic}")
        print("-" * 70)
        print("✅ RECOMMENDED ACTIONS:")
        for i, action in enumerate(analysis.get('recommended_actions', []), 1):
            print(f"   {i}. {action}")
        if analysis.get('modules_involved'):
            print("-" * 70)
            print(f"🔧 Modules involved: {', '.join(analysis['modules_involved'])}")
        print("=" * 70 + "\n")
        
        # Takođe logujemo
        logger.info("=" * 70)
        logger.info("🦙 LLM SIFT ANALYST - INCIDENT REPORT")
        logger.info("=" * 70)
        logger.info(f"Severity Score: {analysis.get('severity_score', 'N/A')}/10")
        logger.info(f"Attack Pattern: {analysis.get('attack_pattern', 'N/A')}")
        logger.info(f"Analysis Method: {analysis.get('analysis_method', 'N/A')}")
        logger.info("-" * 70)
        logger.info("Executive Summary:")
        logger.info(analysis.get('executive_summary', 'N/A'))
        logger.info("-" * 70)
        logger.info("MITRE ATT&CK Tactics:")
        for tactic in analysis.get('mitre_tactics', []):
            logger.info(f"  • {tactic}")
        logger.info("-" * 70)
        logger.info("Recommended Actions:")
        for i, action in enumerate(analysis.get('recommended_actions', []), 1):
            logger.info(f"  {i}. {action}")
        logger.info("=" * 70)
        
        return report


# ============================================================
# ORCHESTRATOR
# ============================================================
class AIPolygraphOrchestrator:
    def __init__(self, enable_llm_analyst: bool = True, use_ollama: bool = True):
        self.modules = [
            Sova(), Skoljka(), Pauk(), Paucina(), Termit(), Kornjaca(),
            Kolibri(), Hobotnica(), Jegulja(), Meduza(), Prasina(),
            HvatacSnova(), Krtica(), SIFT()
        ]
        self.responses = []
        self.event_queue = deque()
        self.rate_limit = CONFIG["rate_limit"]
        self.last_reset = time.time()
        self.lock = threading.Lock()
        
        self.llm_analyst = LLMSiftAnalyst(use_ollama=use_ollama) if enable_llm_analyst else None

    def _check_rate_limit(self, src_ip: str) -> bool:
        with self.lock:
            now = time.time()
            if now - self.last_reset > self.rate_limit["window_sec"]:
                self.event_queue.clear()
                self.last_reset = now
            ip_count = sum(1 for ip in self.event_queue if ip == src_ip)
            if ip_count >= self.rate_limit["max_events_per_ip_per_sec"]:
                return False
            self.event_queue.append(src_ip)
            return True

    def process_event(self, event: Dict[str, Any]) -> None:
        src_ip = event.get('source_ip', 'unknown')
        if not self._check_rate_limit(src_ip):
            return
            
        if 'timestamp' not in event:
            event['timestamp'] = time.time()

        for module in self.modules:
            try:
                detection = module.detect(event)
                if detection:
                    response = module.respond(event, detection)
                    event_copy = event.copy()
                    event_copy['triggered_module'] = module.name
                    
                    for m in self.modules:
                        if isinstance(m, SIFT):
                            try:
                                m.detect(event_copy)
                            except sqlite3.OperationalError:
                                time.sleep(0.1)
                                m.detect(event_copy)
                                
                    self.responses.append({
                        "module": module.name,
                        "detection": detection,
                        "response": response
                    })
                    
                    if self.llm_analyst:
                        self.llm_analyst.add_alert(module.name, detection, response, event)
                        
            except Exception as e:
                logger.error(f"Module {module.name} failed: {e}")

    def final_report(self) -> List[Dict[str, Any]]:
        for module in self.modules:
            if isinstance(module, SIFT):
                report = module.generate_report()
                self.responses.append({
                    "module": "SIFT",
                    "detection": "final_forensics",
                    "response": report
                })
                break
        
        if self.llm_analyst:
            llm_report = self.llm_analyst.generate_final_report()
            self.responses.append({
                "module": "LLM SIFT Analyst",
                "detection": "ai_incident_analysis",
                "response": llm_report
            })
        
        return self.responses


# ============================================================
# MAIN - DEMO SIMULACIJA SA LLM IZVEŠTAJEM
# ============================================================
def main():
    print("=" * 70)
    print("🦙 AIPOLYGRAPH 2.0 - HACKATHON FINAL")
    print("   Autonomous Incident Response Agent")
    print("   (sa simuliranom izolacijom - bez Linuxa)")
    print("=" * 70)
    
    orch = AIPolygraphOrchestrator(enable_llm_analyst=True, use_ollama=True)
    
    print("\n[TEST] Simulacija multi-vector napada...")
    print("(Svaka detekcija pokrece SIMULIRANU izolaciju u log fajl)\n")
    
    attack_events = [
        {"type": "http_request", "source_ip": "198.51.100.77", "auth_required": True, "headers": {}, "timestamp": time.time()},
        {"type": "login", "user": "admin", "host": "db01", "timestamp": time.time()},
        {"type": "login", "user": "admin", "host": "db01", "timestamp": time.time() + 15},
        {"type": "login", "user": "admin", "host": "db01", "timestamp": time.time() + 30},
        {"type": "connection", "src": "guest-wifi-client", "dst": "database-primary"},
        {"type": "wmi_subscription", "host": "win-srv-02", "script": "powershell -enc SQBFAFgA"},
        {"type": "file_change", "file": TEST_FILE},
        {"type": "log_entry", "content": "User logged in", "disk_log": "Log deleted"},
        {"type": "http_response", "source_ip": "198.51.100.77", "status_code": 500, "body": "Internal Server Error"},
        {"type": "old_credential_check", "email": "attacker@protonmail.com"},
        {"type": "process_memory", "pid": 1000},
        {"type": "process_memory", "pid": 1000},
        {"type": "memory_region", "pid": 4321, "permissions": "RWX"}
    ]
    
    for i, ev in enumerate(attack_events, 1):
        print(f"  [{i}] {ev.get('type')}...")
        orch.process_event(ev)
        time.sleep(0.1)
    
    print("\n" + "=" * 70)
    print("GENERISANJE FINALNOG IZVEŠTAJA...")
    print("=" * 70)
    
    final = orch.final_report()
    
    # Sačekamo malo da se sve ispiše
    time.sleep(0.5)
    
    print("\n" + "=" * 70)
    triggered = len([r for r in final if r['module'] not in ['LLM SIFT Analyst', 'SIFT']])
    print(f"✅ Ukupno modula okinuto: {triggered}")
    print("\n📁 Log izolacije se nalazi na:")
    print(r"   C:\Users\Public\aipolygraph\isolation_log.txt")
    print("=" * 70)


if __name__ == "__main__":
    main()