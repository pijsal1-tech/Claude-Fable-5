

# Project Memory — .hRhRhRhRhRhR
> 252 notes | Score threshold: >40

## Safety — Never Run Destructive Commands

> Dangerous commands are actively monitored.
> Critical/high risk commands trigger error notifications in real-time.

- **NEVER** run `rm -rf`, `del /s`, `rmdir`, `format`, or any command that deletes files/directories without EXPLICIT user approval.
- **NEVER** run `DROP TABLE`, `DELETE FROM`, `TRUNCATE`, or any destructive database operation.
- **NEVER** run `git push --force`, `git reset --hard`, or any command that rewrites history.
- **NEVER** run `npm publish`, `docker rm`, `terraform destroy`, or any irreversible deployment/infrastructure command.
- **NEVER** pipe remote scripts to shell (`curl | bash`, `wget | sh`).
- **ALWAYS** ask the user before running commands that modify system state, install packages, or make network requests.
- When in doubt, **show the command first** and wait for approval.

**Stack:** Dart/JavaScript/Python/Rust · Flask + Flutter

## Project Standards

- 🟢 Edited ..............................................................................................................شغل فريق/genspark_API_Key_chat — confirmed 3x
- 🟢 Edited ..............................................................................................................شغل فريق/0-team_runner.py (9 c — confirmed 3x
- 🟢 Edited ..............................................................................................................شغل فريق/00-All-Responses.md ( — confirmed 3x
- 🟢 Edited AI_Parallel_Runner/wats_plus_PART_v_17/مراجعه/1 (35 changes, 7min) — confirmed 3x
- 🟢 Edited ..............................................................................................................شغل فريق/Genspark API_Key/acco — confirmed 4x
- 🟢 Edited Y_Your_Parking_Space/number_numbers/create_accounts.py (19 changes, 140min) — confirmed 3x
- what-changed in accounts_genspark_API_Key.json — confirmed 29x
- 🟢 Edited ..............................................................................................................شغل فريق/genspark_API_Key_chat — confirmed 3x

## Learned Patterns

- Always: 🟢 Edited ..............................................................................................................شغل فريق/genspark_API_Key_chat — confirmed 3x (seen 2x). Also: Duration: 5 minutes; Duration: 2 minutes
- Always: 🟢 Edited ..............................................................................................................شغل فريق/genspark_API_Key_chat — confirmed 3x (seen 3x). Also: Duration: 2 minutes; Duration: 5 minutes
- Avoid: Dispose controllers in StatefulWidget.dispose() (seen 2x)
- Agent generates new migration for every change (squash related changes)
- Agent installs packages without checking if already installed

### 📚 Core Framework Rules: [tinybirdco/tinybird-python-sdk-guidelines]
# Tinybird Python SDK Guidelines

Guidance for using the `tinybird-sdk` package to define Tinybird resources in Python.

## When to Apply

- Installing or configuring tinybird-sdk
- Defining datasources, pipes, or endpoints in Python
- Creating Tinybird clients in Python
- Using data ingestion or queries in Python
- Running tinybird dev/build/deploy commands for Python projects
- Migrating from legacy .datasource/.pipe files to Python
- Defining connections (Kafka, S3, GCS)
- Creating materialized views, copy pipes, or sink pipes

## Rule Files

- `rules/getting-started.md`
- `rules/configuration.md`
- `rules/defining-datasources.md`
- `rules/defining-endpoints.md`
- `rules/client.md`
- `rules/low-level-api.md`
- `rules/cli-commands.md`
- `rules/connections.md`
- `rules/materialized-views.md`
- `rules/copy-sink-pipes.md`
- `rules/tokens.md`

## Quick Reference

- Install: `pip install tinybird-sdk`
- Initialize: `tinybird init`
- Dev mode: `tinybird dev` (uses configured `dev_mode`, typically branch)
- Build: `tinybird build` (builds against configured dev target)
- Deploy: `tinybird deploy` (deploys to main/production)
- Preview in CI: `tinybird preview`
- Migrate: `tinybird migra...
(truncated)


### 📚 Core Framework Rules: [czlonkowski/n8n-code-python]
# Python Code Node (Beta)

Expert guidance for writing Python code in n8n Code nodes.

---

## ⚠️ Important: JavaScript First

**Recommendation**: Use **JavaScript for 95% of use cases**. Only use Python when:
- You need specific Python standard library functions
- You're significantly more comfortable with Python syntax
- You're doing data transformations better suited to Python

**Why JavaScript is preferred:**
- Full n8n helper functions ($helpers.httpRequest, etc.)
- Luxon DateTime library for advanced date/time operations
- No external library limitations
- Better n8n documentation and community support

---

## Quick Start



### Essential Rules

1. **Consider JavaScript first** - Use Python only when necessary
2. **Access data**: `_input.all()`, `_input.first()`, or `_input.item`
3. **CRITICAL**: Must return `[{"json": {...}}]` format
4. **CRITICAL**: Webhook data is under `_json["body"]` (not `_json` directly)
5. **CRITICAL LIMITATION**: **No external libraries** (no requests, pandas, numpy)
6. **Standard library only**: json, datetime, re, base64, hashlib, urllib.parse, math, random, statistics

---

## Mode Selection Guide

Same as JavaScript - choose based on your use ca...
(truncated)


## Available Tools (ON-DEMAND only)
- `sys_core_01(q)` — Deep search when stuck
- `sys_core_05(query)` — Full-text lookup
> Context above IS your context. Do NOT call sys_core_14() at startup.
