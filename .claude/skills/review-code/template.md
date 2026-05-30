# 1. N+1 Query in someRandomGoFunc()

## Diagnostic:

**PERFORMANCE**

## Explanation:

`someRandomGoFunc()` iterates over a list and makes N queries to the database.

## Suggest:

Use a `JOIN`.
