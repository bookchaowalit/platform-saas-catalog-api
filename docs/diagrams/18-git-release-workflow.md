# 18 — Git and release workflow

ไม่มี branch protection บน `main` (`gh api .../branches/main/protection` → 404 "Branch not protected") ใน 90 วันมีทั้ง PR (#1–#5, 2026-10-17 → 18) และ commit ตรงเข้า `main` (เช่น `282112e`, `21d5d41` ตาม SPEC-001 "Main-only: yes") plus merge commits ของ branch local (`a1357e8`, `a637c02`)

```mermaid
gitGraph
    commit id: "e75f0cc feat saas api"
    commit id: "fd1b37a standalone repo"
    commit id: "93bf3ad feat mcp"
    commit id: "b09ce76 rename"
    branch ci/devsecops-phase1
    commit id: "df38f0b"
    checkout main
    merge ci/devsecops-phase1 id: "ceebdb5 PR 1"
    branch feat/sentry
    commit id: "ecd6722"
    checkout main
    merge feat/sentry id: "f0a2e0d PR 2"
    branch fix/sentry-no-tracing
    commit id: "2611331"
    checkout main
    merge fix/sentry-no-tracing id: "4d4952e PR 3 deploy"
    branch docs/cd-github-wait-for-ci
    commit id: "862f88b"
    checkout main
    merge docs/cd-github-wait-for-ci id: "a1357e8 deploy"
    branch chore/iac-github-source
    commit id: "84d964c"
    checkout main
    merge chore/iac-github-source id: "a637c02 deploy"
    commit id: "282112e L2 baseline"
    commit id: "21d5d41 spec review deploy"
```

```mermaid
flowchart LR
    DEV["Local change"] --> HOW{"Path"}
    HOW -->|"PR"| PRR["pull_request CI"] --> MERGE["merge to main"]
    HOW -->|"direct push"| MAIN["push main"]
    MERGE --> MAINCI["push CI on main"]
    MAIN --> MAINCI
    MAINCI -->|"green"| RWD["Railway Wait for CI then deploy"]
    MAINCI -->|"red"| HOLD["no deploy"]
    RWD --> PROD["production"]
    PROD -->|"rollback"| RED["Redeploy earlier Railway deployment"]
```

gitGraph ย่อ commit ของแต่ละ branch เหลือ 1 จุด (feat/sentry มี 3 commits) PR #1–#3 ถูก squash merge (commit เดียวบน main มีเลข PR); #4–#5 เป็น merge commit (`Merge branch ...`) ไม่มี tag หรือ GitHub release

Sources: `git log --first-parent origin/main`, `gh pr list --state all`, `gh api .../branches/main/protection`, `gh api .../deployments`, `README.md` "Deploy", `.railway/railway.ts`, `specs/001-l2-baseline/spec.md`
