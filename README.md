# Bankito CLI

Bankito is a small but fully interactive PostgreSQL banking shell built on top of Python's `cmd` module. It is designed to demo how isolation levels, row locks, and transfer workflows behave under concurrent load while still being practical enough to explore accounts, transactions, and transfers in a real database.

## Highlights
- Interactive prompt (`src/cmd.py`) with friendly logging, tabular output, and helpful `help` text for every command.
- Controller + model split (`src/controller.py`, `src/model.py`) that enforces logins, performs server-side validation, and coordinates data access.
- Direct PostgreSQL access through `psycopg2` with configurable isolation levels and optional lock-skipping flags to reproduce concurrency issues.
- Transfer workflow stores both sides of every movement, enabling quick inspection of balances, audit trails, and failure scenarios.
- Packaged CLI entry point (`cli.py`) plus a ready-to-customize PyInstaller spec (`cli.spec`) if you want to ship precompiled binaries (a macOS build lives in `dist/bankito`).

## Requirements
- Python 3.11+ (3.10 should also work, but the project is developed with 3.11).
- Access to a PostgreSQL instance that contains the expected `users`, `accounts`, and `transactions` tables.
- `psycopg2-binary`, `tabulate`, and the rest of the libraries listed in `requirements.txt`.

## Installation
```bash
git clone https://github.com/jcbages/bankito.git
cd bankito
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Minimum Database Schema
The model layer only touches a handful of columns, so your database can be minimal. The snippet below matches what `src/model.py` expects—feel free to enrich it with extra indexes, constraints, or seed data.

```sql
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL
);

CREATE TABLE accounts (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  name TEXT NOT NULL,
  balance NUMERIC(12,2) NOT NULL DEFAULT 0,
  currency TEXT NOT NULL DEFAULT 'USD',
  status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE transactions (
  id SERIAL PRIMARY KEY,
  account_id INTEGER NOT NULL REFERENCES accounts(id),
  type TEXT NOT NULL CHECK (type IN ('credit', 'debit')),
  amount NUMERIC(12,2) NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  balance_after NUMERIC(12,2) NOT NULL,
  reference_id UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

Seed at least one user, account, and some transactions so the CLI has something to display. Account balances are stored as `NUMERIC`, which keeps transfer math precise.

## Running the CLI
1. Activate your virtual environment (`source .venv/bin/activate`).
2. Start the app: `python cli.py`.
3. When prompted, paste your PostgreSQL connection URI (example: `postgresql://bankito:secret@localhost:5432/bankito`).
4. Use `login` to authenticate (the credentials must match the `users` table).
5. Explore balances, change isolation levels, or issue transfers.

All output is formatted through `tabulate`, so lists render as nice ASCII tables, and `src/logger.py` adds color-coded logging to highlight warnings/errors while you're experimenting.

### Available Commands

| Command | Description |
| --- | --- |
| `login` | Prompt for username/password and start a session. Required before touching accounts. |
| `logout` | Clear the session and reset the prompt to `[anonymous] >`. |
| `set_isolation_level LEVEL` | Switch between `READ_COMMITTED`, `REPEATABLE_READ`, or `SERIALIZABLE`. Applies immediately (see `controller.py:get_isolation_level`). |
| `get_isolation_level` | Display the current psycopg2 isolation level. |
| `list_accounts` | Show every account owned by the logged-in user with balances, currency, status, and creation date. |
| `list_transactions ACCOUNT_NAME` | Fetch the latest transactions for the named account. |
| `list_transfers ACCOUNT_NAME` | Display paired debit/credit entries for any transfer that touched the account. |
| `transfer SCENARIO FROM_ACCOUNT TO_ACCOUNT_ID AMOUNT` | Move funds while optionally toggling lock behavior (details below). |
| `exit` | Close the CLI gracefully. |

Use the built-in `help` command (e.g., `help transfer`) at any time for inline docs that stay in sync with `src/cmd.py`.

### Isolation Levels & Transfer Scenarios

- `set_isolation_level` delegates to `psycopg2` (see `BankModel.set_isolation_level`) so you are exercising real PostgreSQL isolation semantics.
- `transfer` accepts a `SCENARIO` token which becomes a feature flag checked inside `BankModel.transfer`:
  - `skip_consistent_lock` – locks accounts in the order you pass them instead of a sorted order. This increases the chance of deadlocks when several users target overlapping pairs.
  - `skip_for_update` – bypasses the `SELECT ... FOR UPDATE` locks entirely, letting you observe phantom reads/overdrafts under lower isolation levels.
  - Any other token (for example `default`) keeps the safe path: consistent locking order + explicit row locks.

Because both scenarios intentionally bend the rules, the CLI logs warnings right before things get risky so you can see exactly which step you changed.

### Sample Session

```
$ python cli.py
Enter your database URI:
[anonymous] > login
Enter your username:
Enter your password:
[alice] > set_isolation_level SERIALIZABLE
[alice] > list_accounts
[alice] > transfer default checking 12 100
[alice] > list_transfers checking
[alice] > logout
[anonymous] > exit
```

## Building a Standalone Binary

The repo includes `cli.spec`, so you can ship the CLI without asking teammates to set up Python:

```bash
pip install pyinstaller
pyinstaller cli.spec
```

The resulting executable lands in `dist/bankito`. A prebuilt macOS (arm64) binary is already committed for convenience; rebuild on your own machine if you need a different platform.

## Development Tips
- Logging helpers live in `src/logger.py`. Tweak the colors or levels there if you prefer a different experience.
- Exceptions derive from `AppException`/`DBException`, which keeps controller logic readable and CLI-friendly—bubble up meaningful messages instead of raw traces.
- Concurrency tests often benefit from two terminal windows pointed at the same database; try running one shell with `skip_consistent_lock` while the other stays on the default path to trigger blocking/rollbacks.

Happy hacking, and feel free to open issues/PRs if you extend the CLI with new workflows!
