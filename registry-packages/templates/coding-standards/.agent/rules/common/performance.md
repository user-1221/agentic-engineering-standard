---
name: performance
scope: common
priority: medium
overridable_fields:
  - cache_ttl_default
defaults:
  cache_ttl_default: "300s"
---

# Performance Standards

## No N+1 Queries
- Fetch related data in bulk (joins, batch queries) rather than one row at a time in a loop
- Use eager loading for known associations; switch to lazy loading only for rarely accessed relations
- Profile database queries in development — flag any endpoint that exceeds 5 queries

## Lazy Loading
- Defer expensive computation and resource loading until the result is actually needed
- Use pagination for list endpoints — never return unbounded result sets
- Stream large files instead of loading them entirely into memory

## Caching
- Cache frequently read, rarely changing data at the appropriate layer (in-memory, CDN, database)
- Default cache TTL: ${cache_ttl_default} — adjust per resource based on staleness tolerance
- Always implement cache invalidation alongside caching; stale caches cause subtle bugs
- Use cache-aside (lazy population) as the default strategy

## Resource Efficiency
- Close database connections, file handles, and HTTP clients when done — use context managers or `defer`
- Set timeouts on all outbound network calls; never wait indefinitely
- Avoid unnecessary allocations in hot paths — prefer reuse and pooling
- Measure before optimizing: profile first, then target the bottleneck
