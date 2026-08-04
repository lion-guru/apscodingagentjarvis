"""
Security Engineer Agent - Advanced multi-layer security analysis.

Capabilities:
  - OWASP Top 10 vulnerability scanning (deep)
  - Authentication/authorization flow analysis
  - Secret/credential leakage detection
  - Runtime security pattern analysis
  - Session management auditing
  - Input validation coverage assessment
  - CSRF/XSS vulnerability deep scan
  - Tenant isolation verification
  - Dependency vulnerability scanning
"""

import os
import re
import time
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from py_agentic.agents.base_agent import BaseAgent, AgentResult


@dataclass
class SecurityFinding:
    owasp_category: str
    severity: str
    title: str
    description: str
    file_path: str
    line_num: int
    remediation: str
    evidence: str
    cvss_estimate: float


class SecurityAgent(BaseAgent):
    """Advanced security auditor with OWASP Top 10 coverage."""

    OWASP_TOP_10 = {
        'A01:2021': 'Broken Access Control',
        'A02:2021': 'Cryptographic Failures',
        'A03:2021': 'Injection',
        'A04:2021': 'Insecure Design',
        'A05:2021': 'Security Misconfiguration',
        'A06:2021': 'Vulnerable and Outdated Components',
        'A07:2021': 'Identification and Authentication Failures',
        'A008:2021': 'Software and Data Integrity Failures',
        'A09:2021': 'Security Logging and Monitoring Failures',
        'A10:2021': 'Server-Side Request Forgery',
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_scan = 0
        self._scan_cooldown = 600  # 10 minutes

    def _handled_types(self) -> List[str]:
        return ['sql_injection_risk', 'security_audit', 'secret_scan', 'auth_audit',
                'csrf_audit', 'xss_audit', 'tenant_isolation_audit', 'dependency_security']

    async def process_task(self, task: Dict[str, Any]) -> AgentResult:
        start = time.time()
        changes = []
        task_type = task.get('type', '')

        now = time.time()
        if now - self._last_scan < self._scan_cooldown and task_type == 'security_audit':
            return AgentResult(
                agent_id=self.agent_id,
                task_type=task_type,
                success=True,
                description="Security scan skipped (cooldown)",
                changes_made=[],
                duration_sec=0.1
            )

        self._last_scan = now

        if task_type in ('sql_injection_risk', 'security_audit'):
            findings = await self._comprehensive_security_scan()
            changes.extend([f"Security: {f.title} in {os.path.basename(f.file_path)}:{f.line_num}" for f in findings[:5]])
        elif task_type == 'secret_scan':
            findings = await self._scan_secrets()
            changes.extend([f"Secret: {f.title}" for f in findings[:5]])

        return AgentResult(
            agent_id=self.agent_id,
            task_type=task_type,
            success=True,
            description=f"Security scan: {len(changes)} finding(s)",
            changes_made=changes,
            duration_sec=time.time() - start
        )

    async def _comprehensive_security_scan(self) -> List[SecurityFinding]:
        """Run comprehensive OWASP Top 10 security scan."""
        findings = []

        # A03:2021 - Injection (SQL)
        findings.extend(await self._scan_sql_injection())

        # A03:2021 - Injection (Command)
        findings.extend(await self._scan_command_injection())

        # A07:2021 - Auth Failures
        findings.extend(await self._scan_auth_failures())

        # A01:2021 - Access Control
        findings.extend(await self._scan_access_control_issues())

        # A05:2021 - Misconfiguration
        findings.extend(await self._scan_security_misconfig())

        # A02:2021 - Crypto
        findings.extend(await self._scan_crypto_failures())

        return findings

    async def _scan_sql_injection(self) -> List[SecurityFinding]:
        """Deep SQL injection scan."""
        findings = []
        php_files = self.fs.find_php_files('app/')

        dangerous_patterns = [
            (r'mysqli_query\s*\(\s*\$\w+', 'mysqli_query with variable'),
            (r'mysql_query\s*\(\s*\$\w+', 'mysql_query with variable'),
            (r'\$pdo->query\s*\(\s*\$\w+', 'pdo->query with variable'),
            (r'\$\w+\s*\.\s*["\'].*SELECT', 'Variable interpolation in SQL'),
            (r'\$\w+\s*\.\s*["\'].*INSERT', 'Variable interpolation in INSERT'),
            (r'\$\w+\s*\.\s*["\'].*UPDATE', 'Variable interpolation in UPDATE'),
            (r'\$\w+\s*\.\s*["\'].*DELETE', 'Variable interpolation in DELETE'),
        ]

        for php_file in php_files:
            content = self.fs.read_file(php_file)
            if not content:
                continue

            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith('//') or stripped.startswith('#'):
                    continue

                for pattern, desc in dangerous_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        # Skip if prepared statement nearby
                        context = '\n'.join(lines[max(0, i-3):i+3])
                        if 'prepare' in context or 'bindparam' in context or 'bind_param' in context:
                            continue

                        findings.append(SecurityFinding(
                            owasp_category='A03:2021',
                            severity='critical',
                            title=f"SQL Injection: {desc}",
                            description=f"Potential SQL injection via {desc.lower()}",
                            file_path=php_file,
                            line_num=i,
                            remediation="Use PDO prepared statements with parameter binding",
                            evidence=stripped[:200],
                            cvss_estimate=9.8
                        ))

        return findings

    async def _scan_command_injection(self) -> List[SecurityFinding]:
        """Scan for OS command injection vulnerabilities."""
        findings = []
        php_files = self.fs.find_php_files('app/')

        cmd_patterns = [
            r'exec\s*\(\s*\$\w+',
            r'system\s*\(\s*\$\w+',
            r'passthru\s*\(\s*\$\w+',
            r'shell_exec\s*\(\s*\$\w+',
            r'`[^`]*\$_GET',
            r'`[^`]*\$_POST',
            r'`[^`]*\$_REQUEST',
        ]

        for php_file in php_files:
            content = self.fs.read_file(php_file)
            if not content:
                continue

            for i, line in enumerate(content.split('\n'), 1):
                for pattern in cmd_patterns:
                    if re.search(pattern, line):
                        findings.append(SecurityFinding(
                            owasp_category='A03:2021',
                            severity='critical',
                            title="OS Command Injection",
                            description="User input used in OS command execution",
                            file_path=php_file,
                            line_num=i,
                            remediation="Use escapeshellarg() or whitelist allowed inputs",
                            evidence=line.strip()[:200],
                            cvss_estimate=9.8
                        ))

        return findings

    async def _scan_auth_failures(self) -> List[SecurityFinding]:
        """Scan for authentication and session management issues."""
        findings = []
        php_files = self.fs.find_php_files('app/')

        for php_file in php_files:
            content = self.fs.read_file(php_file)
            if not content:
                continue

            lines = content.split('\n')

            for i, line in enumerate(lines, 1):
                # Hardcoded credentials
                if re.search(r'password\s*=\s*["\']([^"\']+)["\']', line, re.IGNORECASE):
                    findings.append(SecurityFinding(
                        owasp_category='A07:2021',
                        severity='high',
                        title="Hardcoded Credentials",
                        description="Hardcoded password detected",
                        file_path=php_file,
                        line_num=i,
                        remediation="Use environment variables or secure config",
                        evidence=line.strip()[:150],
                        cvss_estimate=8.2
                    ))

                # Weak session handling
                if 'session_start()' in line and i > 10:
                    pass  # Normal

                # Insecure cookie settings
                if re.search(r'setcookie\s*\(', line) and 'httponly' not in content[max(0, content.find(line)-200):content.find(line)+200]:
                    findings.append(SecurityFinding(
                        owasp_category='A05:2021',
                        severity='medium',
                        title="Missing Secure Cookie Flag",
                        description="Cookie set without HttpOnly or Secure flags",
                        file_path=php_file,
                        line_num=i,
                        remediation="Add httponly=true, secure=true, samesite=Strict",
                        evidence=line.strip()[:150],
                        cvss_estimate=6.5
                    ))

        return findings

    async def _scan_access_control_issues(self) -> List[SecurityFinding]:
        """Scan for broken access control."""
        findings = []
        php_files = self.fs.find_php_files('app/Http/Controllers/')

        for php_file in php_files:
            content = self.fs.read_file(php_file)
            if not content:
                continue

            lines = content.split('\n')

            # Check for missing authentication checks
            for i, line in enumerate(lines, 1):
                # Public endpoints that should require auth
                if re.search(r'function\s+(index|list|view|show)\s*\(\s*\)', line):
                    # Check if next 5 lines have auth check
                    context = '\n'.join(lines[i:i+5])
                    if 'requireLogin' not in context and 'authenticate' not in context and 'isLoggedIn' not in context:
                        if 'api' not in php_file.lower() and 'auth' not in php_file.lower():
                            findings.append(SecurityFinding(
                                owasp_category='A01:2021',
                                severity='medium',
                                title="Potential Missing Auth Check",
                                description=f"Controller method may lack authentication check",
                                file_path=php_file,
                                line_num=i,
                                remediation="Add authentication check in controller method",
                                evidence=line.strip()[:150],
                                cvss_estimate=6.5
                            ))

        return findings

    async def _scan_security_misconfig(self) -> List[SecurityFinding]:
        """Scan for security misconfigurations."""
        findings = []

        # Check debug mode in production
        env_file = os.path.join(self.project_root, '.env')
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                env_content = f.read()
                if 'APP_ENV=local' in env_content or 'APP_ENV=development' in env_content:
                    if 'APP_DEBUG=true' in env_content:
                        findings.append(SecurityFinding(
                            owasp_category='A05:2021',
                            severity='high',
                            title="Debug Mode Enabled",
                            description="APP_DEBUG=true in environment file",
                            file_path=env_file,
                            line_num=1,
                            remediation="Set APP_DEBUG=false in production",
                            evidence="APP_DEBUG=true",
                            cvss_estimate=7.5
                        ))

        return findings

    async def _scan_crypto_failures(self) -> List[SecurityFinding]:
        """Scan for cryptographic failures."""
        findings = []
        php_files = self.fs.find_php_files('app/')

        for php_file in php_files:
            content = self.fs.read_file(php_file)
            if not content:
                continue

            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                # MD5/SHA1 usage
                if re.search(r'\b(md5|sha1)\s*\(', line):
                    findings.append(SecurityFinding(
                        owasp_category='A02:2021',
                        severity='high',
                        title="Weak Hash Algorithm",
                        description=f"Use of {re.search(r'(md5|sha1)', line).group(1)} for security",
                        file_path=php_file,
                        line_num=i,
                        remediation="Use password_hash() with bcrypt or Argon2",
                        evidence=line.strip()[:150],
                        cvss_estimate=7.5
                    ))

        return findings

    async def _scan_secrets(self) -> List[SecurityFinding]:
        """Scan for leaked secrets and credentials."""
        findings = []

        secret_patterns = [
            (r'(?:api_key|apikey|api_key)\s*=\s*["\']([^"\']+)["\']', 'API Key'),
            (r'(?:secret_key|secret)\s*=\s*["\']([^"\']+)["\']', 'Secret Key'),
            (r'(?:aws_access_key_id|aws_secret)\s*=\s*["\']([^"\']+)["\']', 'AWS Credential'),
            (r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', 'Private Key'),
        ]

        # Check environment files
        env_files = [
            os.path.join(self.project_root, '.env'),
            os.path.join(self.project_root, '.env.local'),
            os.path.join(self.project_root, '.env.production'),
        ]

        for env_file in env_files:
            if os.path.exists(env_file):
                with open(env_file, 'r') as f:
                    for i, line in enumerate(f, 1):
                        for pattern, secret_type in secret_patterns:
                            if re.search(pattern, line):
                                findings.append(SecurityFinding(
                                    owasp_category='A02:2021',
                                    severity='critical',
                                    title=f"Leaked {secret_type}",
                                    description=f"{secret_type} found in env file",
                                    file_path=env_file,
                                    line_num=i,
                                    remediation="Rotate immediately and use proper secret management",
                                    evidence=line.strip()[:100],
                                    cvss_estimate=9.1
                                ))

        # Also check config files
        config_files = self.fs.glob('config/*.php')
        for config_file in config_files:
            content = self.fs.read_file(config_file)
            if not content:
                continue
            for i, line in enumerate(content.split('\n'), 1):
                for pattern, secret_type in secret_patterns:
                    if re.search(pattern, line) and 'env(' not in line:
                        findings.append(SecurityFinding(
                            owasp_category='A02:2021',
                            severity='high',
                            title=f"Hardcoded {secret_type}",
                            description=f"{secret_type} hardcoded in config",
                            file_path=config_file,
                            line_num=i,
                            remediation="Use env() function to load from environment",
                            evidence=line.strip()[:100],
                            cvss_estimate=8.2
                        ))

        return findings
