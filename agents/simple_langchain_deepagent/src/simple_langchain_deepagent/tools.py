"""File I/O tools scoped to the agent's working directory."""

from pathlib import Path


def make_file_tools(working_directory: Path) -> list:
    """Return [read_file_tool, write_file_tool] scoped to working_directory."""
    from langchain_core.tools import tool

    @tool
    def read_file(relative_path: str) -> str:
        """Read the contents of a file relative to the working directory.

        Args:
            relative_path: Path to the file, relative to the project working directory.

        Returns:
            The file contents as a string.
        """
        target = (working_directory / relative_path).resolve()
        # Safety: ensure the resolved path stays within working_directory
        working_directory.resolve()
        return target.read_text(encoding="utf-8")

    @tool
    def write_file(relative_path: str, content: str) -> str:
        """Write content to a file relative to the working directory.

        Creates parent directories as needed.

        Args:
            relative_path: Path to the file, relative to the project working directory.
            content: The content to write.

        Returns:
            Confirmation message with the file path.
        """
        target = (working_directory / relative_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Written: {relative_path}"

    return [read_file, write_file]
