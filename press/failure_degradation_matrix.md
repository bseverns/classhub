# Failure And Degradation Matrix

## Summary
This is the compact source for explaining how the remote helper path fails without taking the classroom down.

| Failure class | Lease state after detection | Helper routing result | Classroom-visible effect | Evidence produced |
| --- | --- | --- | --- | --- |
| Remote path still warming | `requested` or `starting` | stay local/default | helper stays usable, no remote acceleration yet | readiness probe timestamps, status detail |
| Warm probe timeout | `starting` or `degraded` depending on prior state | stay local/default | slower/smaller helper path, no hard outage | `last_readiness_reason_code`, ready-probe event |
| Auth failure | `degraded` | local retry | helper answer can still return on local/default backend | fallback count, degraded transition, reason-coded event |
| Upstream unavailable | `degraded` | local retry | classroom flow continues with baseline helper path | fallback event, degraded transition, provider-unreachable count |
| Malformed remote response | `degraded` | local retry | bounded failure with staff-visible evidence | fallback count, degraded transition |
| Provider reports off during refresh | `off` | no remote routing | class returns to baseline path | reconciliation event |
| Lease expiry reached | `off` after auto-stop if shutdown succeeds | no remote routing | class returns to baseline path | auto-stop count, expiry event, leased minutes |
| Idle timeout reached | `off` after auto-stop if shutdown succeeds | no remote routing | class returns to baseline path | auto-stop count, idle-stop event |
| Stop request fails | `error` | no remote routing | staff sees bounded error; students still do not get provider controls | error state, stop-failure event |

## Core sentence

The classroom stays usable when the special path fails.
