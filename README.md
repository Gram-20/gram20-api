# Gram-20 API

Simple API to provide Gram-20 essential data over REST endpoints.

To run:
1. Prepare DB config in db.env:
````sh
PGDATABASE=ton_index
PGUSER=username
PGPASSWORD=password
PGHOST=postgres
````
2. Build and run:
````sh
docker compose build
docker compose up -d
````

## Endpoints:

### /v1/gram20/balance/{address}/{tick}

Current balance for _address_ and _tick_.

### /v1/gram20/balance/{address}

Current balances for _address_ and any tick.

### /v1/gram20/history/{address}/{tick}

Transfer history (wihtout mints) for _address_ and _tick_.
For pagination, please use query param _max_id_

### /v1/gram20/tick/{tick}

Basic information about any _tick_.

### /v1/gram20/check

Allows you to check if message hash has been accepted by the ledger or not.
