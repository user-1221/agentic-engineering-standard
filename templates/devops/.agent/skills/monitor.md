# Skill: Monitor Service

## Purpose

Monitor a deployed service by checking health endpoints, error rates, latency percentiles, and resource usage.

## When to Run

- After deploy completes successfully
- After rollback to verify recovery
- On-demand health check requested

## How It Works

1. Poll health endpoint every 10 seconds
2. Collect error rate from logs/metrics
3. Measure latency p50, p95, p99
4. Check CPU and memory usage
5. Compare against thresholds for duration
6. Report final health status

## Decision Tree

```
Monitor for duration_seconds:
  ├── Health endpoint down? → Status: unhealthy
  ├── Error rate > 1%? → Status: degraded
  ├── Latency p99 > threshold? → Status: degraded
  ├── CPU > 80% or Memory > 85%? → Status: degraded
  └── All metrics normal? → Status: healthy

After monitoring:
  ├── Healthy? → Confirm deployment
  ├── Degraded? → Trigger rollback consideration
  └── Unhealthy? → Immediate rollback
```

## Error Handling

- **Health endpoint unreachable**: Mark unhealthy immediately
- **Metrics collection failure**: Log warning, continue with available data
- **Threshold breach**: Alert and recommend rollback
