import subprocess
from pathlib import Path
from pydantic import BaseModel, ConfigDict

def shell(command: str) -> str:
    """
    Run a shell command.
    Returns the exit code and stdout/stderr text in a combined string.
    """
    print('TOOL shell:', command)
    try:
        completed = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        output = completed.stdout or ""
        return f"Exit code: {completed.returncode}\n{output}"
    except Exception as exc:
        return f"Failed to execute command: {type(exc).__name__}: {exc}"


def read(path: str) -> str:
    """
    Read the specified file.
    `path` is relative to current directory or absolute.
    Returns line-enumerated contents of the file or an error message.
    """
    print('TOOL read:', path)
    try:
        with Path(path).expanduser().open("r", encoding="utf-8") as file:
            return "".join(
                f"{line_number:04}| {line}"
                for line_number, line in enumerate(file, 1)
            )
    except Exception as exc:
        return f"Failed to read file: {type(exc).__name__}: {exc}"


def write(path: str, content: str) -> str:
    """
    Write the `content` to the specified file.
    `path` is relative to current directory or absolute.
    Returns a status message (success or failure with error details).
    """
    print('TOOL write:', path)
    try:
        file_path = Path(path).expanduser()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"Successfully wrote {file_path}"
    except Exception as exc:
        return f"Failed to write file: {type(exc).__name__}: {exc}"


def edit(path: str, replace_this: str, with_this: str) -> str:
    """
    Edit the specified file.
    `path` is relative to current directory or absolute.
    `replace_this` is the content you want to replace; must be unique within the file.
    `with_this` is the new content to insert where `replace_this` is found.
    Returns a status message (success or failure with error details).
    """
    print('TOOL edit:', path)
    try:
        file_path = Path(path).expanduser()
        original = file_path.read_text(encoding="utf-8")
        if not replace_this:
            return "Failed to edit file: text to replace must not be empty"

        occurrences = original.count(replace_this)
        if occurrences != 1:
            if occurrences == 0:
                return "Failed to edit file: text to replace was not found"
            return (
                f"Failed to edit file: text to replace was found {occurrences} times; "
                "it must be unique"
            )

        file_path.write_text(original.replace(replace_this, with_this, 1), encoding="utf-8")
        return f"Successfully edited {file_path}"
    except Exception as exc:
        return f"Failed to edit file: {type(exc).__name__}: {exc}"



class ShellParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command: str

class ReadParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str

class WriteParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    content: str

class EditParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    replace_this: str
    with_this: str


tools = [
    {
        "type": "function",
        "name": "shell",
        "description": (
            "Run a shell command on the local computer. "
            "Return the exit code and combined stdout/stderr."
        ),
        "parameters": ShellParams.model_json_schema(),
        "strict": True,
    },
    {
        "type": "function",
        "name": "read",
        "description": (
            "Read a UTF-8 file and return its contents with line numbers. "
            "The path can be absolute or relative to the current directory."
        ),
        "parameters": ReadParams.model_json_schema(),
        "strict": True,
    },
    {
        "type": "function",
        "name": "write",
        "description": (
            "Write UTF-8 text to a file, creating parent directories "
            "if needed. Overwrites the file if it already exists."
        ),
        "parameters": WriteParams.model_json_schema(),
        "strict": True,
    },
    {
        "type": "function",
        "name": "edit",
        "description": (
            "Replace exactly one occurrence of text in a UTF-8 file. "
            "replace_this must be nonempty and occur exactly once. "
            "Do not include the line-number prefixes from the read tool."
        ),
        "parameters": EditParams.model_json_schema(),
        "strict": True,
    },
]
