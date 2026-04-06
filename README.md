# nekte

> NEKTE Protocol — Token-efficient agent-to-agent coordination (Python SDK)

## Install

```bash
pip install nekte
```

## Quick Start

```python
from nekte import NekteClient, HttpTransport, InMemoryCacheStore, CapabilityCache

async with NekteClient(
    "http://localhost:4001",
    transport=HttpTransport("http://localhost:4001"),
    cache=CapabilityCache(store=InMemoryCacheStore()),
) as client:
    catalog = await client.catalog()
    result = await client.invoke("sentiment", input={"text": "Great product!"})
    print(result.out)
```

## Architecture

Hexagonal + DDD with 4 explicit layers:

```
domain/       Pure logic, zero I/O (types, state machine, SIEVE, hashing)
ports/        Interfaces (Transport, CacheStore, AuthHandler, StreamWriter)
application/  Orchestration (NekteClient, CapabilityCache, TaskRegistry)
adapters/     I/O implementations (HttpTransport, InMemoryCacheStore)
```

## License

MIT — [BaronTech Labs](https://barontech.io)
