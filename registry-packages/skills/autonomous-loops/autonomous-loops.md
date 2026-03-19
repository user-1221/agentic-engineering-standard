# Autonomous Loops

## Purpose

Patterns for long-running autonomous agent sessions: loop detection, progress tracking, graceful termination, and checkpoint recovery. Essential for 24/7 agents that operate continuously without human supervision.

## When to Use

- Running automated pipelines (data processing, monitoring, CI/CD)
- 24/7 assistant agents on messaging platforms
- Long-running research or analysis tasks
- Any task expected to run for more than 30 minutes

## Core Patterns

### 1. Loop Detection

Identify when the agent is stuck repeating the same actions without progress.

**Signals:**
- Same tool called 3+ times with identical arguments
- Error message repeated without change in approach
- Output unchanged after 5+ iterations
- Context growing without new information

**Response:**
1. Pause the current approach
2. Log the stuck state with context
3. Try an alternative approach (change strategy, not just retry)
4. If 3 alternatives fail, escalate to human or gracefully terminate

### 2. Progress Tracking

Maintain measurable checkpoints so progress is visible and recoverable.

**Implementation:**
- Define milestones at the start of each task
- Update `.agent/memory/operations.md` after each milestone
- Track: milestone name, timestamp, outcome, next step
- Calculate completion percentage from milestones achieved

**Checkpoint format:**
```
## Current Run: 2026-03-19T10:00Z
- [x] Data fetched (10:02Z) — 1,234 items
- [x] Validation complete (10:15Z) — 1,200 valid
- [ ] Processing — in progress (850/1,200)
- [ ] Report generation
- [ ] Notification
```

### 3. Graceful Termination

Clean shutdown with state preservation when stopping is needed.

**Triggers:**
- User sends stop signal
- Resource limits reached (memory, time, API quota)
- Unrecoverable error after retry exhaustion
- System shutdown (SIGTERM/SIGINT)

**Shutdown sequence:**
1. Finish current atomic operation (don't leave half-written files)
2. Save progress to checkpoint file
3. Write summary of completed work and remaining items
4. Release resources (close files, connections, locks)
5. Log termination reason and resume instructions

### 4. Checkpoint Recovery

Resume from the last known good state after interruption.

**On startup:**
1. Check for existing checkpoint file
2. If found, display summary: "Previous run stopped at step 3/5"
3. Validate checkpoint data is still current (files exist, state consistent)
4. Resume from last checkpoint, skip completed steps
5. If checkpoint is stale, offer to restart or resume

**State to preserve:**
- Current position in the pipeline
- Processed item IDs (avoid reprocessing)
- Accumulated results
- Error log from previous run
- Configuration at time of last run

## Decision Tree

```
Starting a long-running task?
  ├── Check for existing checkpoint → Resume if valid
  ├── Define milestones → Track progress
  └── During execution:
       ├── Progress stalled? → Loop detection
       │    ├── Same action 3x? → Try alternative
       │    └── 3 alternatives failed? → Escalate or terminate
       ├── Resource limit hit? → Graceful termination
       └── Task complete? → Clean up, report results
```

## Configuration

Key parameters to tune:
- `max_retries_before_alternative`: 3 (attempts before switching approach)
- `max_alternatives`: 3 (different approaches before escalating)
- `checkpoint_interval`: every milestone or every 10 minutes
- `heartbeat_interval`: 30 minutes (for 24/7 agents)
- `max_context_tokens`: threshold for context compaction

## Error Handling

- **Loop detected**: Log, try alternative, escalate if stuck
- **Checkpoint corrupt**: Restart from beginning, warn user
- **Resource exhaustion**: Save state, terminate cleanly, report
- **External service down**: Retry with backoff, checkpoint, wait for recovery
