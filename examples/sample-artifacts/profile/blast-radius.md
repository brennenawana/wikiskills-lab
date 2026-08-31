# Blast radius

*(Format sample — see the folder README. Values are illustrations only.)*

## Repositories

| Path | What it is | Agent touches it? |
|---|---|---|
| `../orbit-api` | the main service | yes — reads and writes |
| `../orbit-shared` | shared library, sometimes edited in the same task | yes — reads, rarely writes |

## Outside services

| Service | How it is reached | Agent touches it? |
|---|---|---|
| Ticket tracker | REST API from the pipeline script | yes — reads tickets and comments |
| CI | web UI only | no — human only |
| Package registry | `pip` during builds | indirectly |

Every row above is either covered by an observation stream or listed as an
acknowledged gap in `ledgers/session.json` — silent gaps are not allowed
(requirement O10).
