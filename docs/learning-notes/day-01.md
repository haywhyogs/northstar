# Day 1 learning notes

## Glossary (plain English)

| Term | Meaning |
|---|---|
| Asynchronous processing | Accept the request now, finish the work later in the background |
| Transaction | A group of database changes that succeed or fail **together** (all or nothing) |
| Outbox | A database table of "messages waiting to be posted", saved in the same transaction as the debit |
| Dispatcher | Small program that posts outbox messages to Service Bus |
| Service Bus queue | Azure's "post office" holding messages until the worker collects them |
| At-least-once delivery | A message may arrive more than once; never assume exactly once |
| Idempotency | Doing something twice has the same effect as doing it once ("PAID" stamp) |
| Peek-lock | Worker borrows a message, and only deletes it after the work succeeds |
| Dead-letter queue | "Undeliverable mail" pile for messages that failed too many times |
| T-SQL | Microsoft's flavour of SQL used by SQL Server / Azure SQL |
| ODBC driver | Translator between Python and the database (like a printer driver) |
| Entra ID | Microsoft's identity service (who are you, what may you do) |
| Container image | Our app packaged with everything it needs |
| AKS | Azure-managed Kubernetes; runs and restarts our containers |
| Workload identity | A passwordless Azure "staff badge" for each pod |
| ADR | Architecture Decision Record: why we chose something |

## Tools installed today

| Tool | Why we need it |
|---|---|
| Homebrew | macOS package manager, used to install everything else |
| GitHub CLI (`gh`) | Create repos, PRs and reviews from the terminal |
| Azure CLI (`az`) | Talk to Azure: log in, check costs, inspect resources |
| Terraform | Describe Azure infrastructure as code |
| uv | Fast Python installer and project manager; gives us Python 3.12 |
| Node.js | Build the React frontend |
| Docker Desktop | Run containers locally (SQL Server, Service Bus emulator, our app) |
| SSH key (ed25519) | Passwordless, key-based login from Git to GitHub |

## Git and GitHub authentication (fundamentals)

**Git** is the version-control tool on your laptop. **GitHub** is a website that hosts Git repositories.
When you `git push`, GitHub must know **who you are**. There are two ways to prove it:

| Method | How it works | Analogy |
|---|---|---|
| **HTTPS + token** | The URL looks like `https://github.com/...`. GitHub stopped accepting account **passwords** for Git in 2021, so you use a personal access token, or let `gh auth login` store one in the macOS keychain for you | Showing an ID card at the door every time (the token is a temporary ID card) |
| **SSH key** (our choice) | The URL looks like `git@github.com:...`. You create a **key pair**: the **private key** stays on your Mac, and the **public key** is uploaded to GitHub | A padlock and key. You give GitHub the **padlock** (public key). Only your **key** (private key) can open it, and it never leaves your Mac |

- **`gh` CLI** is separate from Git. It talks to GitHub's **API** to create repos, open PRs and approve things.
  It needs its own login (`gh auth login`), and we tell it to use SSH for Git operations.
- One SSH public key can only be attached to **one** GitHub account. That's one reason the reviewer account doesn't use this Mac's key.
- **Commit email:** every commit permanently records an email. In a public repo, use GitHub's
  `ID+username@users.noreply.github.com` address to keep your real one private.

### Two accounts, realistically
| Account | Role | What it does | Needs SSH/clone? |
|---|---|---|---|
| Main | Engineer (author) | Writes code, pushes branches, opens PRs, triggers deployments | Yes |
| Second | Independent reviewer | Reviews and approves PRs and staging deployments **in the browser** | No |

GitHub won't let a PR's author approve their own PR. That's exactly why a second identity makes the review genuine.

## ✍️ In my own words (fill this in yourself)

1. Why does the outbox row have to be saved in the **same transaction** as the debit?
   >
2. What would go wrong without idempotency in the worker?
   >
3. Why is a budget alert the first thing we create in Azure?
   >
