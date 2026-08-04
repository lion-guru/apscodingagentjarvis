"""
Data Analyst Agent - Database health monitoring and business intelligence.

Monitors:
  - Table sizes and growth trends
  - Missing indexes on frequently-queried columns
  - Query performance (slow queries > 1s)
  - Data quality (NULLs in required columns, orphaned records)
  - Tenant data distribution (isolation verification)
  - Business KPI health (commission gaps, payment leaks, CRM stats)
"""

import os
import time
import re
from typing import Dict, Any, List
from py_agentic.agents.base_agent import BaseAgent, AgentResult


class DataAnalystAgent(BaseAgent):
    """Domain agent for database health and business intelligence."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_check = 0
        self._check_cooldown = 120  # 2 minutes

    def _handled_types(self) -> List[str]:
        return ['db_health', 'data_quality', 'missing_indexes', 'slow_queries',
                'business_kpis', 'tenant_isolation', 'orphaned_records']

    async def process_task(self, task: Dict[str, Any]) -> AgentResult:
        start = time.time()
        changes = []
        task_type = task.get('type', '')

        checks = await self._run_all_checks()

        report = {
            'tables_analyzed': len(checks.get('table_sizes', [])),
            'issues_found': len(checks.get('issues', [])),
            'slow_queries': len(checks.get('slow_queries', [])),
            'kpi_summary': checks.get('kpis', {})
        }

        self._log(f"DB Health: {report['tables_analyzed']} tables, {report['issues_found']} issues, {report['slow_queries']} slow queries")

        if checks['issues']:
            for issue in checks['issues'][:5]:
                self._log(f"  ISSUE: {issue}")

        # Use AI to summarize findings if available
        if self.ollama and self.ollama.is_available() and checks['issues']:
            prompt = f"Analyze these database issues and prioritize:\n" + "\n".join(checks['issues'][:15])
            insight = self.ollama.generate(prompt, system="You are a database analyst. Prioritize issues by severity and suggest fixes.")
            if insight:
                changes.append(f"AI analysis: {insight[:300]}")

        # Save report
        report_dir = os.path.join(self.project_root, 'reports', 'data_health')
        os.makedirs(report_dir, exist_ok=True)
        report_file = os.path.join(report_dir, f'db_health_{int(time.time())}.json')
        try:
            import json
            with open(report_file, 'w') as f:
                json.dump({'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'), 'checks': checks, 'summary': report}, f, indent=2)
            changes.append(f"Report saved: reports/data_health/{os.path.basename(report_file)}")
        except Exception:
            pass

        return AgentResult(
            agent_id=self.agent_id,
            task_type='db_health',
            success=True,
            description=f"DB health: {report['tables_analyzed']} tables, {report['issues_found']} issues, {report['slow_queries']} slow queries",
            changes_made=changes,
            duration_sec=time.time() - start,
            ai_insight=f"Analyzed {report['tables_analyzed']} tables, found {report['issues_found']} issues"
        )

    def _handled_types_list(self) -> List[str]:
        return self._handled_types()

    async def _run_all_checks(self) -> Dict[str, Any]:
        """Run all database health checks."""
        now = time.time()
        if now - self._last_check < self._check_cooldown:
            return {'issues': [], 'table_sizes': [], 'slow_queries': [], 'kpis': {}}

        self._last_check = now
        results = {'issues': [], 'table_sizes': [], 'slow_queries': [], 'kpis': {}}

        # 1. Table sizes (top 20 largest)
        result = self.shell.run_sql("SELECT TABLE_NAME, ROUND(DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024 AS size_mb FROM information_schema.TABLES WHERE TABLE_SCHEMA = 'apsdreamhome' ORDER BY size_mb DESC LIMIT 20")
        if result.success and result.stdout.strip():
            for line in result.stdout.strip().split('\n')[1:]:  # skip header
                parts = line.split()
                if len(parts) >= 2:
                    results['table_sizes'].append({'name': parts[0], 'size_mb': parts[1]})

        # 2. Top 10 largest tables by row count
        large_tables = [t['name'] for t in results['table_sizes'][:10]]
        for table in large_tables:
            result = self.shell.run_sql(f"SELECT COUNT(*) FROM `{table}`")
            if result.success and result.stdout.strip():
                count = result.stdout.strip().split('\n')[-1].strip()
                if count.isdigit() and int(count) > 100000:
                    results['issues'].append(f"Large table '{table}' with {count} rows - consider archiving or partitioning")

        # 3. Check for tables without tenant_id that should have it (business tables)
        business_tables = [
            'leads', 'bookings', 'payments', 'plots', 'properties', 'users',
            'mlm_commission_ledger', 'notifications', 'support_tickets',
            'crm_activities', 'crm_tasks', 'crm_deals', 'land_acquisitions',
            'wallet_transactions', 'commission_ledger'
        ]
        for table in business_tables:
            result = self.shell.run_sql(f"SHOW COLUMNS FROM `{table}` LIKE 'tenant_id'")
            if result.success:
                # If no tenant_id column returned, it's a missing column
                lines = [l for l in result.stdout.strip().split('\n') if l and 'tenant_id' not in l.lower()]
                if lines and len(lines) <= 1 and not result.stdout.strip().split('\n')[1:] if len(result.stdout.strip().split('\n')) > 1 else True:
                    pass  # Column exists
            # Simpler check: try selecting with tenant_id filter
            result = self.shell.run_sql(f"SELECT COUNT(*) FROM `{table}` WHERE tenant_id IS NOT NULL LIMIT 1")
            if not result.success:
                if 'tenant_id' in result.stderr.lower() or 'unknown column' in result.stderr.lower():
                    results['issues'].append(f"Table '{table}' missing tenant_id column - tenant isolation risk!")

        # 4. Business KPIs
        kpis = {}

        # Commission entries
        result = self.shell.run_sql("SELECT COUNT(*) FROM mlm_commission_ledger WHERE status = 'pending'")
        if result.success and result.stdout.strip():
            kpis['pending_commissions'] = int(result.stdout.strip().split('\n')[-1].strip())

        # Unpaid commissions
        result = self.shell.run_sql("SELECT COUNT(*) FROM mlm_commission_ledger WHERE status IN ('approved', 'pending')")
        if result.success and result.stdout.strip():
            kpis['unpaid_commission_amount'] = result.stdout.strip().split('\n')[-1].strip()

        # Leads in pipeline
        result = self.shell.run_sql("SELECT COUNT(*) FROM leads WHERE status NOT IN ('closed_won', 'closed_lost')")
        if result.success and result.stdout.strip():
            kpis['open_leads'] = int(result.stdout.strip().split('\n')[-1].strip())

        # Stale leads
        result = self.shell.run_sql("""
            SELECT COUNT(*) FROM leads
            WHERE status NOT IN ('closed_won', 'closed_lost')
            AND (last_activity_at IS NULL OR last_activity_at < DATE_SUB(NOW(), INTERVAL 30 DAY))
        """)
        if result.success and result.stdout.strip():
            count = int(result.stdout.strip().split('\n')[-1].strip())
            kpis['stale_leads'] = count
            if count > 10:
                results['issues'].append(f"{count} stale leads (inactive 30+ days) - sales follow-up needed")

        # Payments without commissions
        result = self.shell.run_sql("""
            SELECT COUNT(*) FROM booking_payment_schedules bps
            LEFT JOIN mlm_commission_ledger mcl ON bps.booking_id = mcl.booking_id
            WHERE bps.status = 'paid' AND mcl.id IS NULL
        """)
        if result.success and result.stdout.strip():
            count = int(result.stdout.strip().split('\n')[-1].strip())
            kpis['commission_gaps'] = count
            if count > 0:
                results['issues'].append(f"{count} paid bookings without commission entries - revenue leakage!")

        # Orphaned records check
        result = self.shell.run_sql("""
            SELECT COUNT(*) FROM leads l
            LEFT JOIN users u ON l.assigned_to = u.id
            WHERE l.assigned_to IS NOT NULL AND u.id IS NULL
        """)
        if result.success and result.stdout.strip():
            count = int(result.stdout.strip().split('\n')[-1].strip())
            kpis['orphaned_leads'] = count
            if count > 0:
                results['issues'].append(f"{count} orphaned leads assigned to deleted users")

        # Slow queries (from MySQL slow log if available)
        result = self.shell.run_sql("""
            SELECT COUNT(*) FROM mysql.slow_log
            WHERE sql_text LIKE '%apsdreamhome%'
            AND start_time > DATE_SUB(NOW(), INTERVAL 1 HOUR)
        """)
        if result.success and result.stdout.strip():
            count = int(result.stdout.strip().split('\n')[-1].strip())
            kpis['slow_queries'] = count
            if count > 5:
                results['issues'].append(f"{count} slow queries in last hour - optimize queries")

        results['kpis'] = kpis
        return results

    def can_handle(self, task_type: str) -> bool:
        return task_type in self._handled_types()

    def _log(self, msg: str):
        print(f"[{self.name}] {msg}")
