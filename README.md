# bankito

[![No Maintenance Intended](http://unmaintained.tech/badge.svg)](http://unmaintained.tech/)
[![License](https://img.shields.io/github/license/mashape/apistatus.svg)](LICENSE)

:bank: A tiny PostgreSQL banking CLI to play with race conditions, isolation levels and row locks on transactions.

## Usage
```
pip install -r requirements.txt
python cli.py
```

Paste a PostgreSQL connection URI when prompted (it expects `users`, `accounts` and `transactions` tables, see `src/model.py`), then `login` and try commands like `list_accounts`, `set_isolation_level SERIALIZABLE` or `transfer default checking 12 100`. Run `help` for the full list.

Use `skip_consistent_lock` or `skip_for_update` as the transfer scenario to reproduce deadlocks and overdrafts under concurrent sessions.
