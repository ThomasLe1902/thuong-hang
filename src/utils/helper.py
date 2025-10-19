from langchain_core.documents import Document
from typing import Union, TypedDict, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, trim_messages
from langchain_core.runnables import RunnableLambda
from langgraph.prebuilt import ToolNode
from langchain_core.messages import ToolMessage
import base64
from fastapi import UploadFile
from typing import TypeVar
import os
from typing import List, Iterable
from git import Repo
import tiktoken
from src.utils.logger import logger
from src.config.constants import MAX_REPOSITORY_SIZE_MB

State = TypeVar("State", bound=Dict[str, Any])


def fake_token_counter(messages: Union[list[BaseMessage], BaseMessage]) -> int:
    if isinstance(messages, list):
        return sum(len(str(message.content).split()) for message in messages)
    return len(str(messages.content).split())


def convert_list_context_source_to_str(contexts: list[Document]):
    formatted_str = ""
    for i, context in enumerate(contexts):
        formatted_str += f"Document index {i}:\nContent: {context.page_content}\n"
        formatted_str += "----------------------------------------------\n\n"
    return formatted_str


def trim_messages_function(messages: list[BaseMessage], max_tokens: int = 100000):
    if len(messages) <= 1:
        return messages
    messages = trim_messages(
        messages,
        strategy="last",
        token_counter=fake_token_counter,
        max_tokens=max_tokens,
        start_on="human",
        # end_on="ai",
        include_system=False,
        allow_partial=False,
    )
    return messages


def create_tool_node_with_fallback(tools: list) -> dict:
    return ToolNode(tools).with_fallbacks(
        [RunnableLambda(handle_tool_error)], exception_key="error"
    )


def handle_tool_error(state: State) -> dict:
    error = state.get("error")
    tool_messages = state["messages"][-1]
    return {
        "messages": [
            ToolMessage(
                content=f"Error: {repr(error)}\n please fix your mistakes.",
                tool_call_id=tc["id"],
            )
            for tc in tool_messages.tool_calls
        ]
    }


async def preprocess_messages(query: str, attachs: list[UploadFile]):
    messages: dict[str, list[dict]] = {
        "role": "user",
        "content": [],
    }
    if query:
        messages["content"].append(
            {
                "type": "text",
                "text": query,
            }
        )
    if attachs:
        for attach in attachs:
            if (
                attach.content_type == "image/jpeg"
                or attach.content_type == "image/png"
            ):
                content = await attach.read()
                encoded_string = base64.b64encode(content).decode("utf-8")
                messages["content"].append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encoded_string}",
                        },
                    }
                )
            if attach.content_type == "application/pdf":
                content = await attach.read()
                encoded_string = base64.b64encode(content).decode("utf-8")
                messages["content"].append(
                    {
                        "type": "file",
                        "source_type": "base64",
                        "mime_type": "application/pdf",
                        "data": f"{encoded_string}",
                        "citations": {"enabled": True},
                    }
                )
    return messages


REPO_FOLDER = os.path.join(os.path.dirname(__file__), "../../repo")


def calculate_directory_size(directory_path: str) -> int:
    """Calculate the total size of a directory in bytes.

    Args:
        directory_path (str): Path to the directory

    Returns:
        int: Total size in bytes
    """
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(directory_path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(file_path)
                except (OSError, IOError):
                    # Skip files that can't be accessed
                    continue
    except (OSError, IOError):
        # If directory can't be accessed, return 0
        pass
    return total_size


def list_code_files_in_repository(
    repo_url: str, extensions: List[str], max_size_mb: int = MAX_REPOSITORY_SIZE_MB
) -> Iterable[str]:
    """Clone the GitHub repository and return a list of code files with the specified extensions.

    Args:
        repo_url (str): URL of the GitHub repository
        extensions (List[str]): List of file extensions to include
        max_size_mb (int): Maximum repository size in MB (default: 2MB)

    Returns:
        Iterable[str]: List of code files

    Raises:
        ValueError: If repository size exceeds the limit
    """
    local_path = clone_github_repository(repo_url)

    # Check repository size
    repo_size_bytes = calculate_directory_size(local_path)
    repo_size_mb = repo_size_bytes / (1024 * 1024)  # Convert to MB

    logger.info(f"Repository size: {repo_size_mb:.2f} MB")

    if repo_size_mb > max_size_mb:
        # Clean up the cloned repository
        import shutil

        shutil.rmtree(local_path)
        raise ValueError(
            f"Repository size ({repo_size_mb:.2f} MB) exceeds the maximum allowed size of {max_size_mb} MB"
        )

    return get_all_files_in_directory(local_path, extensions)


def clone_github_repository(repo_url: str) -> str:
    """Clone a GitHub repository into the 'repo' folder and return the local path.

    Args:
        repo_url (str): URL of the GitHub repository

    Returns:
        str: Local path to the cloned repository

    Raises:
        git.GitCommandError: If cloning fails
    """
    if not os.path.exists(REPO_FOLDER):
        os.makedirs(REPO_FOLDER)

    repo_name = repo_url.split("/")[-1]
    local_path = os.path.join(REPO_FOLDER, repo_name)

    # Remove existing repository if it exists
    if os.path.exists(local_path):
        import shutil

        shutil.rmtree(local_path)
        logger.info(f"Removed existing repository at {local_path}")

    # Clone fresh copy
    logger.info(f"Cloning repository from {repo_url}")
    Repo.clone_from(repo_url, local_path)
    logger.info(f"Repository cloned successfully to {local_path}")

    return local_path


def read_file(file_path: str, from_repo: bool = True) -> str:
    """Read the contents of a file.

    Args:
        file_path (str): Path to the file
        from_repo (bool): Whether to read from repository folder

    Returns:
        str: Contents of the file

    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If there's an error reading the file
    """
    try:
        if from_repo:
            full_path = os.path.join(REPO_FOLDER, file_path)
        else:
            full_path = file_path
        with open(full_path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {full_path}")
    except IOError as e:
        raise IOError(f"Error reading file {full_path}: {str(e)}")


def get_all_files_in_directory(path: str, extensions: List[str]) -> List[str]:
    """Return a list of all files in a directory with the specified extensions."""
    files = []
    for root, _, filenames in os.walk(path):
        for filename in filenames:
            if any(filename.endswith(ext) for ext in extensions):
                files.append(os.path.join(root, filename))
    return files


def count_token(string: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding("cl100k_base")
    num_tokens = len(encoding.encode(string))
    return num_tokens


def input_preparation(selected_files, project_description, criterias, token_limit=4000):
    filtered_data = []
    filtered_files = []
    file_tree = build_tree(selected_files)
    for file_path in selected_files:
        content = read_file(file_path)
        token_count = count_token(content)
        if token_count <= token_limit:
            filtered_files.append(file_path)
            filtered_data.append(
                {
                    "criterias": criterias,
                    "file_name": file_path,
                    "file_tree": file_tree,
                    "code": content,
                    "project_description": project_description,
                }
            )
        else:
            logger.warning(
                f"Skipping {file_path}: Token count {token_count} exceeds limit of 4000"
            )
    return filtered_data, filtered_files


def create_file_tree(code_files: Iterable[str]) -> List[dict]:
    """Create a tree structure from the list of code files, removing the 'repo' prefix."""
    file_tree = []
    code_files = sorted(code_files)

    for file in code_files:
        # Remove the 'repo/' prefix from file paths
        file = file.replace(REPO_FOLDER + os.sep, "")

        parts = file.split(os.sep)
        current_level = file_tree
        for i, part in enumerate(parts):
            existing = [node for node in current_level if node["label"] == part]
            if existing:
                current_level = existing[0].setdefault("children", [])
            else:
                new_node = {
                    "label": part,
                    "value": os.sep.join(parts[: i + 1]),
                }
                current_level.append(new_node)
                if i != len(parts) - 1:
                    current_level = new_node.setdefault("children", [])
    return file_tree


def format_comment_across_file(
    files_name: list[str], analyze_results: list[str]
) -> str:
    """Format the comments across all files."""
    return "\n".join(
        [
            f'File Name: {file_name}\nComment: {analyze_result.get("comment","")}'
            for file_name, analyze_result in zip(files_name, analyze_results)
        ]
    )


def is_file_path(path: str) -> bool:
    """Check if a path is a file path (has an extension) rather than a directory path."""
    filename = path.split("/")[-1]
    return "." in filename and not filename.startswith(".")


def filter_file_paths(paths: List[str]) -> List[str]:
    """Filter a list of paths to include only file paths, excluding directory paths."""
    return [path for path in paths if is_file_path(path)]


def build_tree(paths: list[str]) -> str:
    """Build a visual tree structure from a list of paths."""
    tree = {}
    for path in paths:
        parts = path.split(os.sep)
        node = tree
        for part in parts:
            node = node.setdefault(part, {})

    return tree_to_string(tree)


def tree_to_string(tree: dict, prefix: str = "", is_last: bool = True) -> str:
    """Convert a tree structure to a string representation with visual connectors.

    Args:
        tree: Dictionary representing the tree structure
        prefix: Current line prefix for drawing branches
        is_last: Whether current node is the last sibling

    Returns:
        String representation of the tree with visual connectors
    """
    lines = []
    items = list(tree.items())

    for i, (name, subtree) in enumerate(items):
        is_last_item = i == len(items) - 1
        connector = "└── " if is_last_item else "├── "
        lines.append(prefix + connector + name)

        if isinstance(subtree, dict):
            extension = "    " if is_last_item else "│   "
            subtree_lines = tree_to_string(subtree, prefix + extension, is_last_item)
            lines.append(subtree_lines)

    return "\n".join(filter(None, lines))
