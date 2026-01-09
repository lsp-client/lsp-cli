# LSP CLI

[![PyPI](https://img.shields.io/pypi/v/lsp-cli.svg)](https://pypi.org/project/lsp-cli/)
[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **⚠️ Windows Temporary Not Supported**  
> Due to implementation details, `lsp-cli` does not currently support Windows. Support for Windows will be added in the next version.

A powerful command-line interface for the [**Language Server Agent Protocol (LSAP)**](https://github.com/lsp-client/LSAP). `lsp-cli` provides a bridge between traditional [Language Server Protocol (LSP)](https://microsoft.github.io/language-server-protocol/) servers and high-level agentic workflows, offering structured data access and a robust background server management system.

Built on top of [lsp-client](https://github.com/lsp-client/lsp-client) and [LSAP](https://github.com/lsp-client/LSAP), this tool is designed for developers and AI agents who need reliable, fast, and structured access to language intelligence.

## Key Features

- **🤖 Built for Agents**: The CLI output is optimized for Coding Agents. By avoiding fancy TUI/UI elements and rich terminal formatting, it significantly reduces token consumption while maintaining high readability for LLMs.
- **🚀 Instant Analysis**: Quickly get definitions, references, hover info, and completions from the terminal.
- **🏢 Managed Server Lifecycle**: A background manager automatically handles language server processes, reusing them across requests for maximum performance.
- **🧩 LSAP Integration**: Leverages the Language Server Agent Protocol for structured, agent-friendly responses with built-in pagination and text-based location finding.
- **⚡ Async-First**: Built with `anyio` and `asyncer` for high-performance concurrent operations.

## Supported Languages

`lsp-cli` currently supports the following languages:

| Language                    | Language Server              |
| :-------------------------- | :--------------------------- |
| **Python**                  | `basedpyright`               |
| **Go**                      | `gopls`                      |
| **Rust**                    | `rust-analyzer`              |
| **TypeScript / JavaScript** | `typescript-language-server` |
| **Deno**                    | `deno`                       |

More supported languages coming very soon!

```bash
uv tool install --python 3.13 lsp-cli
```

## Quick Start

The main entry point is the `lsp` command. It automatically detects the appropriate language server for your project.

### Find Definition

Find where a symbol is defined:

```bash
# Using line scope
lsp definition --locate main.py:10

# Using text search to locate the symbol
lsp definition --locate "main.py@my_function<HERE>"

# Find declaration instead of definition
lsp definition --locate models.py:25 --decl
```

### Get Symbol Information

Get detailed information about a symbol at a specific location:

```bash
# Get symbol info at line 15
lsp symbol --locate main.py:15

# Find and get symbol info
lsp symbol --locate "utils.py@UserClass<HERE>"
```

### Find References

Find all references to a symbol:

```bash
# Find references to a symbol at line 20
lsp reference --locate models.py:20

# Find references with text search
lsp reference --locate "models.py@UserClass<HERE>"

# Show more context lines around each reference
lsp reference --locate app.py:10 --context-lines 5

# Find implementations instead of references
lsp reference --locate interface.py:15 --impl
```

### Search Workspace Symbols

Search for symbols across the entire workspace by name:

```bash
# Search for symbols containing "MyClass"
lsp search MyClass

# Search in a specific workspace
lsp search "UserModel" --workspace /path/to/project

# Filter by symbol kind
lsp search "test" --kind function --kind method

# Limit results
lsp search "Config" --max-items 10
```

### Get File Outline

Get a hierarchical outline of symbols in a file:

```bash
# Get outline of main symbols (classes, functions, methods)
lsp outline main.py

# Include all symbols (variables, parameters, etc.)
lsp outline utils.py --all
```

### Get Hover Information

Get documentation and type information for a symbol:

```bash
# Get hover info at a specific line
lsp hover --locate main.py:42

# Find symbol and get hover info
lsp hover --locate "models.py@process_data<HERE>"
```

## Commands

| Command      | Description                                             |
| ------------ | ------------------------------------------------------- |
| `definition` | Find symbol definition, declaration, or type definition |
| `hover`      | Get hover information (type info, documentation)        |
| `reference`  | Find symbol references or implementations               |
| `outline`    | Get a structured symbol outline for a file              |
| `symbol`     | Get detailed symbol information at a specific location  |
| `search`     | Search for symbols across the entire workspace by name  |
| `rename`     | Rename a symbol across the workspace                    |
| `server`     | Manage background LSP server processes                  |
| `locate`     | Parse and verify a location string                      |

## Server Management

`lsp-cli` uses a **background manager process to keep language servers alive between command invocations**. This significantly reduces latency for repeated queries.

```bash
# List all running LSP servers
lsp server list

# Manually start a server for a path
lsp server start .

# Stop a server
lsp server stop .
```

The manager starts automatically when you run any analysis command.

## Usage Tips

### Locating Symbols

LSP CLI uses a unified `locate` string syntax (`-L` or `--locate`) to specify positions in your code. The format is `<file_path>[:<scope>][@<find>]`.

1. **Line-based**: Specify a line number (1-based)

   ```bash
   lsp definition --locate main.py:42
   ```

2. **Range-based**: Specify a line range

   ```bash
   lsp symbol --locate utils.py:10,20
   ```

3. **Text-based**: Search for text with a cursor marker `<HERE>` or `<|>`

   ```bash
   lsp hover --locate "app.py@my_function<HERE>()"
   ```

4. **Symbol path**: Navigate using symbol hierarchy
   ```bash
   lsp definition --locate models.py:UserClass.get_name
   ```

### Working with Results

Pagination for large result sets:

```bash
# Get first 50 results
lsp search "config" --max-items 50

# Get next page
lsp search "config" --max-items 50 --start-index 50
```

### Debugging

Enable debug mode to see detailed logs:

```bash
lsp --debug definition --locate main.py:10
```

## Configuration

`lsp-cli` can be configured via environment variables or a `config.toml` file.

- **Config File**: `~/.config/lsp-cli/config.toml` (on Linux) or `~/Library/Application Support/lsp-cli/config.toml` (on macOS).
- **Environment Variables**: Prefix with `LSP_` (e.g., `LSP_LOG_LEVEL=DEBUG`).

### Available Settings

Create a `config.toml` file at the location above with the following options:

```toml
# config.toml

# Enable debug mode (verbose logging)
debug = false

# Idle timeout for managed servers (in seconds)
idle_timeout = 600

# Log level: TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL
log_level = "INFO"

# Default maximum items for paginated results (search, reference, etc.)
# Set to null for no limit, or a number like 20
default_max_items = 20

# Default number of context lines for reference results
default_context_lines = 2

# Paths to ignore in search results (e.g., virtual environments, build directories)
ignore_paths = [".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build"]
```

### Environment Variables

All settings can be overridden via environment variables:

```bash
export LSP_DEBUG=true
export LSP_LOG_LEVEL=DEBUG
export LSP_DEFAULT_MAX_ITEMS=50
```

## Contributing

Contributions are welcome! Please see our [Contributing Guide](CONTRIBUTING.md) for details on:

- Development setup
- Adding new CLI commands
- Improving the server manager
- Development workflow

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [lsp-client](https://github.com/lsp-client/python-sdk): The underlying LSP client library.
- [LSAP](https://github.com/lsp-client/LSAP): The Language Server Agent Protocol.
- [lsprotocol](https://github.com/microsoft/lsprotocol): LSP type definitions.
