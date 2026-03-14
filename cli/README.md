# aes-cli

CLI tool for the [Agentic Engineering Standard](https://github.com/user-1221/agentic-engineering-standard) (AES) — an open standard for structuring, sharing, and discovering agentic engineering projects.

AES treats agent instructions, skills, permissions, and memory as **first-class engineering artifacts**, making them portable, composable, and shareable across AI coding tools.

## Installation

```bash
pipx install aes-cli

# Or inside a virtual environment
pip install aes-cli
```

### Upgrading

```bash
pipx upgrade aes-cli            # if installed with pipx
pip install --upgrade aes-cli   # if installed with pip
```

After upgrading, run `aes sync` in your project to regenerate tool-specific configs with the new version's sync logic. Your `.agent/` source files are not modified by the upgrade.

Requires Python 3.10+.

## Quick Start

### Initialize a new project

```bash
aes init
```

Interactive wizard that scaffolds a `.agent/` directory with agent config, skills, permissions, and memory. Supports multiple domains (web, ML, DevOps, research) and modes (dev-assist, agent-integrated).

### Validate a project

```bash
aes validate .
```

Checks `.agent/` files against the AES JSON Schema, validates dependency graphs, and reports errors/warnings.

### Sync to your AI tool

```bash
aes sync -t claude    # or: cursor, copilot, windsurf
```

Generates tool-specific config from your `.agent/` directory. Write once, use with any supported AI coding tool.

### Publish & install skills

```bash
aes publish ./my-skill    # share a skill or template to the AES registry
aes install user/skill    # install a skill into your project
aes search "deploy"       # search the registry
```

### Inspect a project

```bash
aes inspect .
```

Displays a summary of the project's agent configuration: skills, workflows, permissions, and dependencies.

## Commands

| Command     | Description                                    |
|-------------|------------------------------------------------|
| `init`      | Scaffold a new `.agent/` directory             |
| `validate`  | Validate against the AES spec                  |
| `sync`      | Generate tool-specific config                  |
| `publish`   | Publish a skill or template to the registry    |
| `install`   | Install a skill or template from the registry  |
| `search`    | Search the AES registry                        |
| `inspect`   | Inspect project agent configuration            |
| `status`    | Show sync status and drift                     |

## Links

- [Specification](https://github.com/user-1221/agentic-engineering-standard/tree/main/spec)
- [Examples](https://github.com/user-1221/agentic-engineering-standard/tree/main/examples)
- [Templates](https://github.com/user-1221/agentic-engineering-standard/tree/main/templates)
- [Registry](https://registry.aes-official.com)

## License

Apache 2.0
