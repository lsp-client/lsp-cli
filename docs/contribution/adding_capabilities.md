# Adding New Capabilities

This guide explains how to add new LSP capabilities to the `lsp-cli` system.

## Architecture Overview

The `lsp-cli` follows a layered architecture for providing capabilities:

1.  **LSAP Layer (`lsap`)**: Defines the capability protocol, request/response schemas, and the implementation of the capability using an LSP client.
2.  **Manager Layer (`lsp_cli.manager`)**:
    *   `Capabilities` class (`src/lsp_cli/manager/capability.py`): Orchestrates all available capabilities for a managed client.
    *   `CapabilityController` (`src/lsp_cli/manager/capability.py`): Exposes capabilities as HTTP endpoints via Litestar.
3.  **CLI Front-end (`lsp_cli.cli`)**: Provides the Typer commands that users interact with.

## Step-by-Step Guide

### 1. Define Capability in LSAP

Before adding a capability to the CLI, it must be defined in the `lsap` package (usually in a separate repository or as a dependency). A capability typically consists of:
*   `Request` schema.
*   `Response` schema.
*   A `Capability` class that takes an `lsp_client.Client` and implements the logic.

### 2. Register Capability in the Manager

Update `src/lsp_cli/manager/capability.py`:

1.  **Import** the new capability, request, and response classes from `lsap`.
2.  Add the new capability as a field in the `@frozen class Capabilities`.
3.  Update `Capabilities.build()` to instantiate the new capability.
4.  Add a new `@post` endpoint to `class CapabilityController`.

Example:
```python
@post("/my-new-capability")
async def my_new_capability(
    self, data: MyNewRequest, state: State
) -> MyNewResponse | None:
    return await state.capabilities.my_new_capability(data)
```

### 3. Create CLI Command

Create a new file in `src/lsp_cli/cli/` (e.g., `my_new_capability.py`) or add to an existing one.

1.  Define a Typer command.
2.  Use `managed_client(path)` to get an `AsyncHttpClient`.
3.  Call the endpoint you created in the manager.
4.  Format and print the output using `print_resp`.

Example:
```python
@app.command("my-new-capability")
@cli_syncify
async def get_my_new_capability(locate: op.LocateOpt):
    locate_obj = create_locate(locate)
    async with managed_client(locate_obj.file_path) as client:
        resp_obj = await client.post(
            "/capability/my-new-capability",
            MyNewResponse,
            json=MyNewRequest(locate=locate_obj),
        )
    if resp_obj:
        print_resp(resp_obj)
```

### 4. Register Command in Main CLI

Update `src/lsp_cli/cli/main.py` to include your new command module using `app.add_typer()`.

## Best Practices

*   **Type Safety**: Always use the defined Request/Response schemas for communication between CLI and Manager.
*   **Error Handling**: Use `lsp_cli.cli.shared.get_msg` to handle and display errors consistently.
*   **Locate Option**: Use the standard `LocateOpt` and `create_locate` utility for file/line/column positioning.
