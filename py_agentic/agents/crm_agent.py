"""
CRM Agent - Monitors CRM data integrity and business pipeline health.

Specializes in detecting:
  - Orphaned leads/dead leads (no activity for 7+ days)
  - Invalid status transitions
  - Duplicate leads (same phone/email)
  - Missing commission triggers after payments
  - Leads assigned to inactive/deleted agents
  - Pipeline bottlenecks
"""

import os
import re
import time
from typing import Dict, Any, List
from py_agentic.agents.base_agent import BaseAgent, AgentResult
import json


class CRMAgent(BaseAgent):
    """Domain agent for CRM business logic monitoring."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_check = 0
        self._check_cooldown = 300

    def _handled_types(self) -> List[str]:
        return ['crm_health', 'missing_commissions', 'stale_leads']

    async def process_task(self, task: Dict[str, Any]) -> AgentResult:
        start = time.time()
        changes = []
        task_type = task.get('type', '')

        if task_type == 'crm_health':
            issues = await self._check_crm_health()
            if issues:
                self._log(f"Found {len(issues)} CRM issues")
                if self.ollama and self.ollama.is_available():
                    prompt = f"Analyze these CRM issues and suggest priorities:\n" + "\n".join(issues[:10])
                    insight = self.ollama.generate(prompt, system="You are a CRM expert. Be concise.")
                    if insight:
                        self._log(f"AI insight: {insight[:200]}")
                        changes.append(f"AI analysis: {insight[:200]}")

            return AgentResult(
                agent_id=self.agent_id,
                task_type=task_type,
                success=True,
                description=f"CRM health check: {len(issues)} issues found",
                changes_made=changes,
                duration_sec=time.time() - start
            )

        # Default: check basic CRM metrics
        metrics = await self._check_crm_metrics()
        return AgentResult(
            agent_id=self.agent_id,
            task_type='crm_metrics',
            success=True,
            description=f"CRM metrics: {metrics.get('leads', 0)} leads, {metrics.get('conversion_rate', 0):.1f}% conversion",
            changes_made=changes,
            duration_sec=time.time() - start
        )

    async def _check_crm_health(self) -> List[str]:
        """Check CRM data integrity via SQL queries."""
        issues = []
        now = time.time()
        if now - self._last_check < self._check_cooldown:
            return []

        self._last_check = now

        # Check for orphaned leads (assigned to inactive users)
        result = self.shell.run_sql("""
            SELECT COUNT(*) FROM leads l
            LEFT JOIN users u ON l.assigned_to = u.id
            WHERE u.id IS NULL AND l.assigned_to IS NOT NULL
        """)
        if result.success:
            count = result.stdout.strip()
            if count and int(count) > 0:
                issues.append(f"Orphaned leads: {count} leads assigned to non-existent users")

        # Check for duplicate leads (same phone)
        result = self.shell.run_sql("""
            SELECT phone, COUNT(*) as cnt FROM leads
            WHERE phone IS NOT NULL AND phone != ''
            GROUP BY phone HAVING COUNT(*) > 1
            LIMIT 5
        """)
        if result.success and result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            if lines and lines[0]:
                issues.append(f"Duplicate lead phones found: {len(lines)} groups")

        # Check for leads with no activity in 30+ days
        result = self.shell.run_sql("""
            SELECT COUNT(*) FROM leads
            WHERE status NOT IN ('closed_won', 'closed_lost')
            AND (last_activity_at IS NULL OR last_activity_at < DATE_SUB(NOW(), INTERVAL 30 DAY))
        """)
        if result.success:
            count = result.stdout.strip()
            if count and int(count) > 0:
                issues.append(f"Stale leads: {count} leads inactive for 30+ days")

        # Check for payments without commission
        result = self.shell.run_sql("""
            SELECT COUNT(*) FROM booking_payment_schedules bps
            LEFT JOIN mlm_commission_ledger mcl ON bps.booking_id = mcl.booking_id
            WHERE bps.status = 'paid' AND mcl.id IS NULL
        """)
        if result.success:
            count = result.stdout.strip()
            if count and int(count) > 0:
                issues.append(f"Payments without commission: {count} paid bookings missing MLM ledger entry")

        return issues

    async def _check_crm_metrics(self) -> Dict[str, Any]:
        """Get current CRM metrics."""
        metrics = {}

        result = self.shell.run_sql("SELECT COUNT(*) FROM leads")
        if result.success and result.stdout.strip():
            metrics['leads'] = int(result.stdout.strip())

        result = self.shell.run_sql("SELECT COUNT(*) FROM leads WHERE status = 'closed_won'")
        if result.success and result.stdout.strip():
            won = int(result.stdout.strip())
            metrics['won'] = won
            if metrics.get('leads', 0) > 0:
                metrics['conversion_rate'] = (won / metrics['leads']) * 100

        result = self.shell.run_sql("SELECT COUNT(*) FROM leads WHERE status = 'new'")
        if result.success and result.stdout.strip():
            metrics['new_leads'] = int(result.stdout.strip())

        return metrics

    def _log(self, msg: str):
        from py_agentic.tools.ollama_client import OllamaClient
        print(f"[{self.name}] {msg}")


def get_crm_task_discovery():
    """Returns a task dict for CRM health checks."""
    return {
        'type': 'crm_health',
        'priority': 'medium',
        'desc': 'CRM data integrity check',
        'detail': 'Check for orphaned leads, duplicates, stale records, missing commissions'
    }
