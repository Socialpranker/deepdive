# Benchmark — postgres-replication-vs-cdc

## Question
Trade-offs between Postgres logical replication and dedicated CDC tooling (Debezium/Fivetran) for streaming changes to a warehouse — which to choose for a 50-table OLTP DB feeding analytics?

## Genre (expected)
decision

## Depth
medium

## Why this question (for the judge)
Supports an architecture decision. Good = clear conditional verdict, both options steel-manned, real failure modes (DDL changes, replication slot bloat) covered.

## Configs to compare
- A: default routing
- B: all-opus
- C: cheap-mode
(run_ids: postgres-replication-vs-cdc-A / postgres-replication-vs-cdc-B / postgres-replication-vs-cdc-C)
