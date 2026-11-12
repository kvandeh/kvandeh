---
title: Running untrusted student code in a disposable container
summary: How AlgoStudio isolates each submission with Docker and gVisor, and which gap remains.
author: Kieran van der Heijde
avatar: assets/kieran.jpg
date: 2026-11-11
---

AlgoStudio runs Python and C# code from students against test cases. The code can contain errors, infinite loops or malicious instructions. Thus each run must stay isolated from the database, the network and the code of other students.

## Design

Each submission runs in a new Docker container. The platform deletes the container and its files after the run. This is the call, from the AlgoStudio backend:

```python
container = client.containers.run(
    runtime=_runtime,             # "runsc" (gVisor) by default
    image=self.image,
    command=self.command,
    network_mode="none",
    mem_limit=self.mem_limit,
    nano_cpus=50_000_000,         # approximately 5% of one core
    pids_limit=128,
    read_only=self.read_only,
    detach=True,
)
container.wait()
```

| Restriction | Value |
| --- | --- |
| Network | None |
| Memory | 100 MB (Python), 512 MB (C#) |
| CPU | Approximately 5% of one core |
| Processes | 128 maximum |
| File system | Read-only for Python |

A normal container shares the kernel of the host. A kernel vulnerability can let code leave the container. For this reason, the default runtime is gVisor (`runsc`). gVisor puts a user-space kernel between the container and the host.

The code writes its result to one JSON file. If the file does not exist, the backend returns the container logs. Thus a crash gives a clear message, not an empty result.

## Known gap

The sandbox has no wall-clock time limit yet. An infinite loop blocks until an operator removes the container. The CPU limit decreases the damage, but it does not stop the loop. The documentation states this gap, so teachers know the risk.

## Conclusion

The sandbox uses only standard tools: Docker, gVisor and container resource limits. Each limit removes one class of risk. The remaining gap is documented, not hidden.
