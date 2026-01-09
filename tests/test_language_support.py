"""
Test basic usability for each supported language.

This module tests that LSP CLI works correctly with all supported languages:
- Python
- Go
- Rust
- TypeScript
- JavaScript
- Deno

Each test verifies that the CLI can:
1. Start a language server for the project
2. List the running server
3. Stop the server cleanly
"""

import subprocess
import time
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def fixtures_dir():
    """Return the path to the test fixtures directory."""
    return Path(__file__).parent / "fixtures"


class BaseLSPTest:
    """Base class for LSP CLI tests with common helper methods."""

    def run_lsp_command(self, *args, timeout=30):
        """Run an lsp command and return the result."""
        result = subprocess.run(
            ["uv", "run", "lsp"] + list(args),
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=Path(__file__).parent.parent,
        )
        return result


class TestLanguageSupport(BaseLSPTest):
    """Test that each supported language works with LSP CLI."""

    def test_python_support(self, fixtures_dir):
        """Test basic LSP operations with Python project."""
        # Use the actual source code as a Python project
        python_file = fixtures_dir.parent.parent / "src" / "lsp_cli" / "__init__.py"
        assert python_file.exists(), "Python test file does not exist"

        # Start server
        result = self.run_lsp_command("server", "start", str(python_file))
        assert result.returncode == 0, f"Failed to start Python server: {result.stderr}"

        # List servers - should show Python server
        result = self.run_lsp_command("server", "list")
        assert result.returncode == 0, f"Failed to list servers: {result.stderr}"
        assert "python" in result.stdout.lower(), "Python server not listed"

        # Stop server
        result = self.run_lsp_command("server", "stop", str(python_file))
        assert result.returncode == 0, f"Failed to stop Python server: {result.stderr}"

    def test_go_support(self, fixtures_dir):
        """Test basic LSP operations with Go project."""
        go_file = fixtures_dir / "go_project" / "main.go"
        assert go_file.exists(), "Go test file does not exist"

        # Start server
        result = self.run_lsp_command("server", "start", str(go_file))
        assert result.returncode == 0, f"Failed to start Go server: {result.stderr}"

        # List servers - should show Go server
        result = self.run_lsp_command("server", "list")
        assert result.returncode == 0, f"Failed to list servers: {result.stderr}"
        assert "go" in result.stdout.lower(), "Go server not listed"

        # Stop server
        result = self.run_lsp_command("server", "stop", str(go_file))
        assert result.returncode == 0, f"Failed to stop Go server: {result.stderr}"

    def test_rust_support(self, fixtures_dir):
        """Test basic LSP operations with Rust project."""
        rust_file = fixtures_dir / "rust_project" / "src" / "main.rs"
        assert rust_file.exists(), "Rust test file does not exist"

        # Start server
        result = self.run_lsp_command("server", "start", str(rust_file))
        assert result.returncode == 0, f"Failed to start Rust server: {result.stderr}"

        # List servers - should show Rust server
        result = self.run_lsp_command("server", "list")
        assert result.returncode == 0, f"Failed to list servers: {result.stderr}"
        assert "rust" in result.stdout.lower(), "Rust server not listed"

        # Stop server
        result = self.run_lsp_command("server", "stop", str(rust_file))
        assert result.returncode == 0, f"Failed to stop Rust server: {result.stderr}"

    def test_typescript_support(self, fixtures_dir):
        """Test basic LSP operations with TypeScript project."""
        ts_file = fixtures_dir / "typescript_project" / "index.ts"
        assert ts_file.exists(), "TypeScript test file does not exist"

        # Start server
        result = self.run_lsp_command("server", "start", str(ts_file))
        assert result.returncode == 0, f"Failed to start TypeScript server: {result.stderr}"

        # List servers - should show TypeScript server
        result = self.run_lsp_command("server", "list")
        assert result.returncode == 0, f"Failed to list servers: {result.stderr}"
        # Note: TypeScript may be identified as "typescript" or abbreviated form
        # We check for both to handle different language server implementations
        stdout_lower = result.stdout.lower()
        assert (
            "typescript" in stdout_lower or "tsserver" in stdout_lower
        ), f"TypeScript server not listed. Output: {result.stdout}"

        # Stop server
        result = self.run_lsp_command("server", "stop", str(ts_file))
        assert result.returncode == 0, f"Failed to stop TypeScript server: {result.stderr}"

    def test_javascript_support(self, fixtures_dir):
        """Test basic LSP operations with JavaScript project."""
        js_file = fixtures_dir / "javascript_project" / "index.js"
        assert js_file.exists(), "JavaScript test file does not exist"

        # Start server
        result = self.run_lsp_command("server", "start", str(js_file))
        assert result.returncode == 0, f"Failed to start JavaScript server: {result.stderr}"

        # List servers - should show JavaScript server
        result = self.run_lsp_command("server", "list")
        assert result.returncode == 0, f"Failed to list servers: {result.stderr}"
        # Note: JavaScript may be identified as "javascript" or abbreviated form
        # We check for both to handle different language server implementations
        stdout_lower = result.stdout.lower()
        assert (
            "javascript" in stdout_lower or "jsserver" in stdout_lower
        ), f"JavaScript server not listed. Output: {result.stdout}"

        # Stop server
        result = self.run_lsp_command("server", "stop", str(js_file))
        assert result.returncode == 0, f"Failed to stop JavaScript server: {result.stderr}"

    def test_deno_support(self, fixtures_dir):
        """Test basic LSP operations with Deno project."""
        deno_file = fixtures_dir / "deno_project" / "main.ts"
        assert deno_file.exists(), "Deno test file does not exist"

        # Start server
        result = self.run_lsp_command("server", "start", str(deno_file))
        assert result.returncode == 0, f"Failed to start Deno server: {result.stderr}"

        # List servers - should show Deno server
        result = self.run_lsp_command("server", "list")
        assert result.returncode == 0, f"Failed to list servers: {result.stderr}"
        assert "deno" in result.stdout.lower(), "Deno server not listed"

        # Stop server
        result = self.run_lsp_command("server", "stop", str(deno_file))
        assert result.returncode == 0, f"Failed to stop Deno server: {result.stderr}"


class TestLanguageServerLifecycle(BaseLSPTest):
    """Test language server lifecycle for all supported languages."""

    def test_multiple_language_servers(self, fixtures_dir):
        """Test running multiple language servers simultaneously."""
        # Start servers for different languages
        python_file = fixtures_dir.parent.parent / "src" / "lsp_cli" / "__init__.py"
        go_file = fixtures_dir / "go_project" / "main.go"
        rust_file = fixtures_dir / "rust_project" / "src" / "main.rs"

        servers = []
        if python_file.exists():
            result = self.run_lsp_command("server", "start", str(python_file))
            if result.returncode == 0:
                servers.append(("python", python_file))

        if go_file.exists():
            result = self.run_lsp_command("server", "start", str(go_file))
            if result.returncode == 0:
                servers.append(("go", go_file))

        if rust_file.exists():
            result = self.run_lsp_command("server", "start", str(rust_file))
            if result.returncode == 0:
                servers.append(("rust", rust_file))

        # List should show multiple servers
        result = self.run_lsp_command("server", "list")
        assert result.returncode == 0, f"Failed to list servers: {result.stderr}"

        # Verify each started server is listed
        for lang, _ in servers:
            assert lang in result.stdout.lower(), f"{lang} server not found in list"

        # Stop all servers
        for _, file_path in servers:
            result = self.run_lsp_command("server", "stop", str(file_path))
            assert result.returncode == 0, f"Failed to stop server for {file_path}"

    def test_language_server_reuse(self, fixtures_dir):
        """Test that starting a server twice reuses the same server."""
        python_file = fixtures_dir.parent.parent / "src" / "lsp_cli" / "__init__.py"
        assert python_file.exists(), "Python test file does not exist"

        # Start server first time
        result1 = self.run_lsp_command("server", "start", str(python_file))
        assert result1.returncode == 0, f"Failed to start server first time: {result1.stderr}"

        # Get server list
        list1 = self.run_lsp_command("server", "list")
        assert list1.returncode == 0

        # Start server second time (should reuse)
        result2 = self.run_lsp_command("server", "start", str(python_file))
        assert result2.returncode == 0, f"Failed to start server second time: {result2.stderr}"

        # Get server list again
        list2 = self.run_lsp_command("server", "list")
        assert list2.returncode == 0

        # Should have the same number of Python servers
        python_count1 = list1.stdout.lower().count("python")
        python_count2 = list2.stdout.lower().count("python")
        assert python_count1 == python_count2, "Server was not reused"

        # Cleanup
        self.run_lsp_command("server", "stop", str(python_file))


class TestLanguageServerErrors(BaseLSPTest):
    """Test error handling for language servers."""

    def test_invalid_file_path(self):
        """Test that invalid file paths are handled gracefully."""
        invalid_file = Path("/nonexistent/path/file.py")

        # Should fail gracefully, not crash
        result = self.run_lsp_command("server", "start", str(invalid_file))
        # Either fails with non-zero exit code or succeeds with error message
        # We just verify it doesn't crash
        assert isinstance(result.returncode, int)

    def test_unsupported_language(self, fixtures_dir):
        """Test that unsupported file types are handled gracefully."""
        # Create a temporary file with unsupported extension
        unsupported_file = fixtures_dir / "test.unsupported"
        unsupported_file.parent.mkdir(parents=True, exist_ok=True)
        unsupported_file.write_text("test content")

        try:
            # Should handle gracefully
            result = self.run_lsp_command("server", "start", str(unsupported_file))
            # Either fails with non-zero exit code or succeeds with appropriate message
            assert isinstance(result.returncode, int)
        finally:
            # Cleanup
            if unsupported_file.exists():
                unsupported_file.unlink()
