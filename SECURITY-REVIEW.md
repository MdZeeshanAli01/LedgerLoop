# Security review

**Project:** LedgerLoop / Hisaabset  
**Review status:** Remediated findings verified in the repository  
**Review date:** 2026-10-18

## Scope and limitations

This review covered the application source, deployment templates, documentation,
and Git history reachable from the published `main` and `T2` branches. It did
not include authenticated inspection of an AWS or Cloudflare account. No live
deployment is claimed by this report.

## Findings

| # | Severity | File | Lines | Vulnerability | Confidence |
|---|----------|------|-------|---------------|------------|
| 1 | 🟠 HIGH | `src/auth.py` | authentication logic | Hardcoded Finance Lead credentials in application source | 10/10 |
| 2 | 🟠 HIGH | deployment documentation | deployment claims | Unverified plaintext public HTTP deployment claim | 9/10 |
| 3 | 🟡 MEDIUM | `deploy/aws/hisaabset-ses-task-policy.json` | policy statement | SES permissions used a wildcard resource and included unnecessary raw-email permission | 10/10 |
| 4 | 🔴 CRITICAL | Git history | historical commits | Historical application password remained reachable in published Git history | 10/10 |
| 5 | ⚪ LOW | AWS and Cloudflare account state | account verification | Account-level deployment and edge-security checks could not be verified without authorized access | 10/10 |

## Remediation

- Local authentication now requires a deployment-managed PBKDF2-HMAC-SHA256
  password hash and fails closed when the value is missing or malformed.
- The quick-login bypass and source-level default password were removed.
- The old password was removed from every commit tree reachable from the
  published `main` and `T2` branches. The rewritten histories were force-pushed
  after verification.
- The SES task policy now grants only `ses:SendEmail` and requires an
  identity-scoped ARN with deployment-time region, account, and verified
  identity values.
- Architecture documentation now shows HTTPS CloudFront/ALB ingress and
  ALB-only access to the ECS task. It no longer claims unrestricted public
  access to port 8501.
- Live AWS and Cloudflare state remains explicitly unverified; deployment must
  not be represented as complete until checked with an authorized identity.

## Verification performed

- `python -m pytest -q` — 84 passed.
- `python -m compileall -q app src backend tests` — passed.
- `git diff --check` — passed.
- Searched all commit trees reachable from published `main` and `T2`; the
  historical password literal is absent.
- Confirmed the working tree contains no AWS credentials, application
  passwords, or default login secret.

## Operational follow-up

If the historical password was ever used outside Git, rotate it in every
environment and secret store. Before deployment, verify AWS identity, SES
sender identity, IAM policies, ALB/CloudFront configuration, TLS certificates,
security groups, logging, and Cloudflare settings through the authorized
account tooling.
