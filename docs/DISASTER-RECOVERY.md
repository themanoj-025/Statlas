# Disaster Recovery Runbook

## Overview
This document outlines the procedures for recovering from various failure scenarios.

## Recovery Time Objectives (RTO)
| Scenario | RTO | RPO |
|----------|-----|-----|
| Database corruption | 4 hours | 1 hour |
| Complete data center loss | 8 hours | 24 hours |
| Ransomware attack | 24 hours | 24 hours |
| Key personnel unavailable | 4 hours | N/A |

## Recovery Procedures

### 1. Database Recovery
1. Stop all application servers
2. Restore from latest backup: `pg_restore -d dbname backup.sql`
3. Verify data integrity
4. Restart application servers
5. Monitor for 30 minutes

### 2. Application Recovery
1. Check health endpoints: `curl /health`
2. If unhealthy, restart: `docker compose restart`
3. If still unhealthy, redeploy: `docker compose up -d --force-recreate`

### 3. Full Stack Recovery
1. Provision infrastructure (Terraform)
2. Deploy application (Docker Compose / Kubernetes)
3. Restore database from backup
4. Verify all services are healthy
5. Run smoke tests

## Backup Schedule
- Database: Daily at 02:00 UTC
- Configuration: On every change
- User uploads: Daily at 03:00 UTC

## Contacts
- Primary oncall: [TEAM]
- Escalation: [MANAGER]
