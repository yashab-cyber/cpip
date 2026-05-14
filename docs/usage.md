# Advanced Usage & Agents

## Daemon Management

`cpip` uses a background daemon to maintain the WebSocket connection to the cloud, allowing for async metadata synchronization and faster execution startup.

- Start the daemon: `cpip daemon start`
- Stop the daemon: `cpip daemon stop`
- Check status: `cpip daemon status`

## Cache Management

Packages, layers, and pre-built wheels are cached locally. You can monitor your cache utilization using the runtime dashboard:

```bash
cpip runtime
```

If you need to force a reinstall and bypass the cache:
```bash
cpip install --force pandas
```

## AI Agent Integration

`cpip` was built with AI orchestration in mind. The `agent` package provides native tools to allow LLMs to manage the system autonomously.

### Using the Built-in Tools

You can expose the `cpip` capabilities to an OpenAI-compatible agent via the tool bindings:

```python
from agent.tools import tools

# Get the JSON schema for the tools
schema = tools.get_tool_definitions()

# These can be passed directly to the OpenAI API:
# response = openai.ChatCompletion.create(
#     model="gpt-4",
#     messages=[...],
#     tools=schema
# )
```

### Browser Automation

Because Playwright cannot be easily installed on Termux natively, `cpip` provides cloud-proxied browser automation:

```python
from agent.browser import browser_agent
import asyncio

async def main():
    # This executes Playwright on the cloud backend and streams the HTML back
    result = await browser_agent.navigate("https://github.com")
    print(result["html"])

asyncio.run(main())
```
