import os
import tempfile
import shutil
import subprocess
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
import uuid
import re
import time
import hashlib
from fastapi import (
    UploadFile,
    File,
    Form,
    HTTPException,
    BackgroundTasks,
    APIRouter,
    FastAPI,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import json
import resource
import platform
from loguru import logger

app = FastAPI(title="Code Grader API", version="1.0.0", docs_url="/")

# Configuration
MAX_EXECUTION_TIME = 5  # seconds
MAX_MEMORY = 256 * 1024 * 1024  # 256MB
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_TOTAL_SIZE = 2 * 1024 * 1024  # 2MB total size limit for uploads and repos


class ExecutionResult(BaseModel):
    success: bool
    stdout: str
    stderr: str
    execution_time: float
    exit_code: int
    error: Optional[str] = None


class InputPattern(BaseModel):
    type: str  # "input", "scanf", "cin", etc.
    line_number: int
    variable_name: Optional[str] = None
    prompt_message: Optional[str] = None
    data_type: Optional[str] = None  # "int", "str", "float", etc.
    raw_code: str


class InputAnalysisResult(BaseModel):
    language: str
    total_inputs: int
    input_patterns: List[InputPattern]
    suggestions: List[str]  # UI suggestions for user


class CodeExecutor:
    def __init__(self):
        self.compilers = {
            "c": "clang" if platform.system() == "Darwin" else "gcc",
            "cpp": "clang++" if platform.system() == "Darwin" else "g++",
            "java": "javac",
            "python": "python3",
        }

    def set_resource_limits(self):
        """Set resource limits for subprocess (Unix only)"""
        if platform.system() == "Linux":
            resource.setrlimit(
                resource.RLIMIT_CPU, (MAX_EXECUTION_TIME, MAX_EXECUTION_TIME)
            )
            resource.setrlimit(resource.RLIMIT_AS, (MAX_MEMORY, MAX_MEMORY))

    def analyze_input_patterns(
        self, language: str, file_contents: Dict[str, str]
    ) -> InputAnalysisResult:
        """Analyze code files to detect input patterns"""
        patterns = []

        if language == "python":
            patterns = self._analyze_python_inputs(file_contents)
        elif language == "java":
            patterns = self._analyze_java_inputs(file_contents)
        elif language in ["c", "cpp"]:
            patterns = self._analyze_c_cpp_inputs(file_contents)

        suggestions = self._generate_input_suggestions(patterns, language)

        return InputAnalysisResult(
            language=language,
            total_inputs=len(patterns),
            input_patterns=patterns,
            suggestions=suggestions,
        )

    def _analyze_python_inputs(
        self, file_contents: Dict[str, str]
    ) -> List[InputPattern]:
        """Analyze Python files for input() patterns"""
        patterns = []

        for filename, content in file_contents.items():
            lines = content.split("\n")

            for i, line in enumerate(lines, 1):
                # Pattern 1: variable = input("prompt")
                match = re.search(
                    r'(\w+)\s*=\s*input\s*\(\s*["\']([^"\']*)["\']?\s*\)', line
                )
                if match:
                    var_name, prompt = match.groups()
                    patterns.append(
                        InputPattern(
                            type="input",
                            line_number=i,
                            variable_name=var_name,
                            prompt_message=prompt or f"Enter value for {var_name}",
                            data_type="str",
                            raw_code=line.strip(),
                        )
                    )
                    continue

                # Pattern 2: variable = int(input("prompt"))
                match = re.search(
                    r'(\w+)\s*=\s*(int|float|str)\s*\(\s*input\s*\(\s*["\']([^"\']*)["\']?\s*\)\s*\)',
                    line,
                )
                if match:
                    var_name, data_type, prompt = match.groups()
                    patterns.append(
                        InputPattern(
                            type="input",
                            line_number=i,
                            variable_name=var_name,
                            prompt_message=prompt
                            or f"Enter {data_type} value for {var_name}",
                            data_type=data_type,
                            raw_code=line.strip(),
                        )
                    )
                    continue

                # Pattern 3: Simple input() without assignment
                if "input(" in line and "=" not in line:
                    patterns.append(
                        InputPattern(
                            type="input",
                            line_number=i,
                            variable_name=None,
                            prompt_message="Enter input",
                            data_type="str",
                            raw_code=line.strip(),
                        )
                    )

        return patterns

    def _analyze_java_inputs(self, file_contents: Dict[str, str]) -> List[InputPattern]:
        """Analyze Java files for Scanner input patterns"""
        patterns = []

        for filename, content in file_contents.items():
            lines = content.split("\n")

            for i, line in enumerate(lines, 1):
                # Pattern 1: scanner.nextInt(), scanner.nextLine(), etc.
                match = re.search(r"(\w+)\s*=\s*(\w+)\.next(\w+)\s*\(\s*\)", line)
                if match:
                    var_name, scanner_name, method = match.groups()
                    data_type = self._java_method_to_type(method)
                    patterns.append(
                        InputPattern(
                            type="scanner",
                            line_number=i,
                            variable_name=var_name,
                            prompt_message=f"Enter {data_type} value for {var_name}",
                            data_type=data_type,
                            raw_code=line.strip(),
                        )
                    )
                    continue

                # Pattern 2: Direct scanner calls without assignment
                match = re.search(r"(\w+)\.next(\w+)\s*\(\s*\)", line)
                if match and "=" not in line:
                    scanner_name, method = match.groups()
                    data_type = self._java_method_to_type(method)
                    patterns.append(
                        InputPattern(
                            type="scanner",
                            line_number=i,
                            variable_name=None,
                            prompt_message=f"Enter {data_type} input",
                            data_type=data_type,
                            raw_code=line.strip(),
                        )
                    )

        return patterns

    def _analyze_c_cpp_inputs(
        self, file_contents: Dict[str, str]
    ) -> List[InputPattern]:
        """Analyze C/C++ files for input patterns"""
        patterns = []

        for filename, content in file_contents.items():
            lines = content.split("\n")

            for i, line in enumerate(lines, 1):
                # Pattern 1: scanf("%d", &variable)
                match = re.search(
                    r'scanf\s*\(\s*["\']([^"\']*)["\'],\s*&(\w+)\s*\)', line
                )
                if match:
                    format_spec, var_name = match.groups()
                    data_type = self._c_format_to_type(format_spec)
                    patterns.append(
                        InputPattern(
                            type="scanf",
                            line_number=i,
                            variable_name=var_name,
                            prompt_message=f"Enter {data_type} value for {var_name}",
                            data_type=data_type,
                            raw_code=line.strip(),
                        )
                    )
                    continue

                # Pattern 2: cin >> variable (C++)
                match = re.search(r"cin\s*>>\s*(\w+)", line)
                if match:
                    var_name = match.group(1)
                    patterns.append(
                        InputPattern(
                            type="cin",
                            line_number=i,
                            variable_name=var_name,
                            prompt_message=f"Enter value for {var_name}",
                            data_type="unknown",
                            raw_code=line.strip(),
                        )
                    )
                    continue

                # Pattern 3: getline(cin, variable) for strings
                match = re.search(r"getline\s*\(\s*cin\s*,\s*(\w+)\s*\)", line)
                if match:
                    var_name = match.group(1)
                    patterns.append(
                        InputPattern(
                            type="getline",
                            line_number=i,
                            variable_name=var_name,
                            prompt_message=f"Enter string for {var_name}",
                            data_type="string",
                            raw_code=line.strip(),
                        )
                    )

        return patterns

    def _java_method_to_type(self, method: str) -> str:
        """Convert Java Scanner method to data type"""
        type_mapping = {
            "Int": "int",
            "Double": "double",
            "Float": "float",
            "Long": "long",
            "Line": "string",
            "": "string",
        }
        return type_mapping.get(method, "string")

    def _c_format_to_type(self, format_spec: str) -> str:
        """Convert C format specifier to data type"""
        if "%d" in format_spec or "%i" in format_spec:
            return "int"
        elif "%f" in format_spec:
            return "float"
        elif "%lf" in format_spec:
            return "double"
        elif "%c" in format_spec:
            return "char"
        elif "%s" in format_spec:
            return "string"
        return "unknown"

    def _generate_input_suggestions(
        self, patterns: List[InputPattern], language: str
    ) -> List[str]:
        """Generate UI suggestions based on detected patterns"""
        suggestions = []

        if not patterns:
            suggestions.append(
                "No input patterns detected. Code will run without user input."
            )
            return suggestions

        suggestions.append(
            f"Detected {len(patterns)} input requirement(s) in {language} code:"
        )

        for i, pattern in enumerate(patterns, 1):
            if pattern.variable_name:
                suggestions.append(
                    f"{i}. Line {pattern.line_number}: {pattern.prompt_message} "
                    f"(Variable: {pattern.variable_name}, Type: {pattern.data_type})"
                )
            else:
                suggestions.append(
                    f"{i}. Line {pattern.line_number}: {pattern.prompt_message} "
                    f"(Type: {pattern.data_type})"
                )

        suggestions.append(
            "Please provide input values in the order they appear in the code."
        )

        return suggestions

    async def execute_code(
        self,
        language: str,
        main_files: List[str],
        workspace: str,
        input_data: Optional[List[str]] = None,
    ) -> ExecutionResult:
        """Execute code based on language with optional input data"""
        try:
            if language == "python":
                return await self._execute_python(main_files, workspace, input_data)
            elif language == "java":
                return await self._execute_java(main_files, workspace, input_data)
            elif language in ["c", "cpp"]:
                return await self._execute_c_cpp(
                    main_files, workspace, language, input_data
                )
            else:
                raise ValueError(f"Unsupported language: {language}")
        except Exception as e:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                execution_time=0,
                exit_code=-1,
                error=str(e),
            )

    async def _execute_with_input(
        self, command: List[str], workspace: str, input_data: Optional[List[str]] = None
    ) -> tuple:
        """Execute process with input data"""
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=workspace,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE,
            preexec_fn=(
                self.set_resource_limits if platform.system() == "Linux" else None
            ),
        )

        # Prepare input string
        stdin_input = None
        if input_data:
            stdin_input = "\n".join(input_data) + "\n"
            stdin_input = stdin_input.encode("utf-8")

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=stdin_input), timeout=MAX_EXECUTION_TIME
            )
            return stdout, stderr, process.returncode
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise asyncio.TimeoutError()

    async def _execute_python(
        self,
        main_files: List[str],
        workspace: str,
        input_data: Optional[List[str]] = None,
    ) -> ExecutionResult:
        """Execute Python code with input support"""
        results = []

        for main_file in main_files:
            file_path = os.path.join(workspace, main_file)
            if not os.path.exists(file_path):
                results.append(
                    ExecutionResult(
                        success=False,
                        stdout="",
                        stderr=f"File not found: {main_file}",
                        execution_time=0,
                        exit_code=-1,
                    )
                )
                continue

            try:
                start_time = asyncio.get_event_loop().time()

                stdout, stderr, returncode = await self._execute_with_input(
                    ["python3", main_file], workspace, input_data
                )

                execution_time = asyncio.get_event_loop().time() - start_time

                results.append(
                    ExecutionResult(
                        success=returncode == 0,
                        stdout=stdout.decode("utf-8", errors="replace"),
                        stderr=stderr.decode("utf-8", errors="replace"),
                        execution_time=execution_time,
                        exit_code=returncode,
                    )
                )

            except asyncio.TimeoutError:
                results.append(
                    ExecutionResult(
                        success=False,
                        stdout="",
                        stderr="Execution timeout exceeded",
                        execution_time=MAX_EXECUTION_TIME,
                        exit_code=-1,
                    )
                )
            except Exception as e:
                results.append(
                    ExecutionResult(
                        success=False,
                        stdout="",
                        stderr=str(e),
                        execution_time=0,
                        exit_code=-1,
                        error=str(e),
                    )
                )

        return self._combine_results(results, main_files)

    async def _execute_java(
        self,
        main_files: List[str],
        workspace: str,
        input_data: Optional[List[str]] = None,
    ) -> ExecutionResult:
        """Compile and execute Java code with input support"""

        # Check if we have .java files to compile
        java_files = list(Path(workspace).glob("*.java"))
        needs_compilation = len(java_files) > 0

        # If we have .java files, compile them
        if needs_compilation:
            logger.info(f"Found {len(java_files)} Java source files, compiling...")

            compile_process = await asyncio.create_subprocess_exec(
                "javac",
                *[str(f) for f in java_files],
                cwd=workspace,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await compile_process.communicate()

            if compile_process.returncode != 0:
                return ExecutionResult(
                    success=False,
                    stdout="",
                    stderr=f"Compilation failed:\n{stderr.decode('utf-8', errors='replace')}",
                    execution_time=0,
                    exit_code=compile_process.returncode,
                )

            logger.info("Java compilation successful")
        else:
            # Check if we have .class files for the main files
            class_files_missing = []
            for main_file in main_files:
                if main_file.endswith(".class"):
                    class_file_path = os.path.join(workspace, main_file)
                else:
                    class_file_path = os.path.join(workspace, f"{main_file}.class")

                if not os.path.exists(class_file_path):
                    class_files_missing.append(main_file)

            if class_files_missing:
                return ExecutionResult(
                    success=False,
                    stdout="",
                    stderr=f"No Java source files found and missing .class files for: {', '.join(class_files_missing)}",
                    execution_time=0,
                    exit_code=-1,
                )

            logger.info("Using existing .class files, skipping compilation")

        # Execute main files
        results = []
        for main_file in main_files:
            # Determine class name
            if main_file.endswith(".class"):
                class_name = main_file.replace(".class", "")
            elif main_file.endswith(".java"):
                class_name = main_file.replace(".java", "")
            else:
                class_name = main_file

            # Verify the .class file exists
            class_file_path = os.path.join(workspace, f"{class_name}.class")
            if not os.path.exists(class_file_path):
                results.append(
                    ExecutionResult(
                        success=False,
                        stdout="",
                        stderr=f"Class file not found: {class_name}.class",
                        execution_time=0,
                        exit_code=-1,
                    )
                )
                continue

            try:
                start_time = asyncio.get_event_loop().time()

                stdout, stderr, returncode = await self._execute_with_input(
                    ["java", class_name], workspace, input_data
                )

                execution_time = asyncio.get_event_loop().time() - start_time

                results.append(
                    ExecutionResult(
                        success=returncode == 0,
                        stdout=stdout.decode("utf-8", errors="replace"),
                        stderr=stderr.decode("utf-8", errors="replace"),
                        execution_time=execution_time,
                        exit_code=returncode,
                    )
                )

            except asyncio.TimeoutError:
                results.append(
                    ExecutionResult(
                        success=False,
                        stdout="",
                        stderr="Execution timeout exceeded",
                        execution_time=MAX_EXECUTION_TIME,
                        exit_code=-1,
                    )
                )
            except Exception as e:
                results.append(
                    ExecutionResult(
                        success=False,
                        stdout="",
                        stderr=str(e),
                        execution_time=0,
                        exit_code=-1,
                        error=str(e),
                    )
                )

        return self._combine_results(results, main_files)

    async def _execute_c_cpp(
        self,
        main_files: List[str],
        workspace: str,
        language: str,
        input_data: Optional[List[str]] = None,
    ) -> ExecutionResult:
        """Compile and execute C/C++ code with input support"""
        compiler = self.compilers[language]
        results = []

        for main_file in main_files:
            file_path = os.path.join(workspace, main_file)
            if not os.path.exists(file_path):
                results.append(
                    ExecutionResult(
                        success=False,
                        stdout="",
                        stderr=f"File not found: {main_file}",
                        execution_time=0,
                        exit_code=-1,
                    )
                )
                continue

            # Output binary name
            output_name = main_file.replace(".c", "").replace(".cpp", "")

            # Compile
            compile_process = await asyncio.create_subprocess_exec(
                compiler,
                main_file,
                "-o",
                output_name,
                cwd=workspace,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await compile_process.communicate()

            if compile_process.returncode != 0:
                results.append(
                    ExecutionResult(
                        success=False,
                        stdout="",
                        stderr=f"Compilation failed:\n{stderr.decode('utf-8', errors='replace')}",
                        execution_time=0,
                        exit_code=compile_process.returncode,
                    )
                )
                continue

            # Execute
            try:
                start_time = asyncio.get_event_loop().time()

                stdout, stderr, returncode = await self._execute_with_input(
                    [f"./{output_name}"], workspace, input_data
                )

                execution_time = asyncio.get_event_loop().time() - start_time

                results.append(
                    ExecutionResult(
                        success=returncode == 0,
                        stdout=stdout.decode("utf-8", errors="replace"),
                        stderr=stderr.decode("utf-8", errors="replace"),
                        execution_time=execution_time,
                        exit_code=returncode,
                    )
                )

            except asyncio.TimeoutError:
                results.append(
                    ExecutionResult(
                        success=False,
                        stdout="",
                        stderr="Execution timeout exceeded",
                        execution_time=MAX_EXECUTION_TIME,
                        exit_code=-1,
                    )
                )
            except Exception as e:
                results.append(
                    ExecutionResult(
                        success=False,
                        stdout="",
                        stderr=str(e),
                        execution_time=0,
                        exit_code=-1,
                        error=str(e),
                    )
                )

        return self._combine_results(results, main_files)

    def _combine_results(
        self, results: List[ExecutionResult], main_files: List[str]
    ) -> ExecutionResult:
        """Combine multiple execution results"""
        if len(results) == 1:
            return results[0]
        else:
            combined_stdout = "\n".join(
                [f"=== {main_files[i]} ===\n{r.stdout}" for i, r in enumerate(results)]
            )
            combined_stderr = "\n".join(
                [
                    f"=== {main_files[i]} ===\n{r.stderr}"
                    for i, r in enumerate(results)
                    if r.stderr
                ]
            )
            total_time = sum(r.execution_time for r in results)
            all_success = all(r.success for r in results)

            return ExecutionResult(
                success=all_success,
                stdout=combined_stdout,
                stderr=combined_stderr,
                execution_time=total_time,
                exit_code=0 if all_success else -1,
            )


def get_directory_size(directory_path: str) -> int:
    """Calculate total size of directory in bytes"""
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(directory_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
    except Exception as e:
        print(f"Error calculating directory size: {e}")
        return float("inf")
    return total_size


def validate_upload_size(files: List[UploadFile]) -> tuple[bool, int]:
    """Validate total size of uploaded files"""
    total_size = 0
    for file in files:
        if hasattr(file, "size") and file.size:
            total_size += file.size
        else:
            return True, 0
    return total_size <= MAX_TOTAL_SIZE, total_size


# Create executor instance
executor = CodeExecutor()


async def clone_repo(repo_url: str, workspace: str):
    """Clone a git repository into the workspace."""
    try:
        process = await asyncio.create_subprocess_exec(
            "git",
            "clone",
            repo_url,
            ".",
            cwd=workspace,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise HTTPException(
                status_code=400, detail=f"Failed to clone repository: {stderr.decode()}"
            )

        repo_size = get_directory_size(workspace)
        if repo_size > MAX_TOTAL_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Repository size ({repo_size / 1024 / 1024:.2f}MB) exceeds limit ({MAX_TOTAL_SIZE / 1024 / 1024:.2f}MB)",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error cloning repository: {str(e)}"
        )


def detect_language_from_files(main_files: List[str]) -> str:
    """Detect programming language from file extensions"""
    if not main_files:
        raise HTTPException(status_code=400, detail="No main files provided")

    first_file = main_files[0]
    if "." not in first_file:
        java_extensions = [".java", ".class"]
        for file in main_files:
            if any(file.endswith(ext) for ext in java_extensions):
                return "java"

        raise HTTPException(
            status_code=400,
            detail=f"Cannot detect language: file '{first_file}' has no extension",
        )

    extension = first_file.split(".")[-1].lower()

    extension_to_language = {
        "py": "python",
        "java": "java",
        "class": "java",
        "c": "c",
        "cpp": "cpp",
        "cc": "cpp",
        "cxx": "cpp",
        "c++": "cpp",
    }

    if extension not in extension_to_language:
        supported_extensions = ", ".join(extension_to_language.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '.{extension}'. Supported extensions: {supported_extensions}",
        )

    detected_language = extension_to_language[extension]

    for file in main_files:
        if "." in file:
            file_ext = file.split(".")[-1].lower()
            file_language = extension_to_language.get(file_ext)
            if file_language != detected_language:
                raise HTTPException(
                    status_code=400,
                    detail=f"Mixed languages detected: '{first_file}' ({detected_language}) and '{file}' ({file_language})",
                )

    return detected_language


@app.post("/analyze-inputs")
async def analyze_inputs(code_content: str = Form(...), language: str = Form(...)):
    """
    Analyze code content to detect input patterns with caching

    Simple API that takes code content and language, returns input patterns

    Args:
        code_content: The source code content to analyze
        language: Programming language (python, java, c, cpp)

    Returns:
        InputAnalysisResult with detected input patterns
    """
    try:
        # Validate language
        supported_languages = ["python", "java", "c", "cpp"]
        if language.lower() not in supported_languages:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported language: {language}. Supported: {supported_languages}",
            )

        # Create a simple file contents dict for analysis
        file_contents_dict = {"main": code_content}

        analysis_result = executor.analyze_input_patterns(
            language.lower(), file_contents_dict
        )
        result_dict = analysis_result.model_dump()

        # Cache the result

        logger.info(f"Input analysis completed for {language} code")
        return JSONResponse(content=result_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing inputs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/judge")
async def judge_code(
    main_files: str = Form(...),
    files: List[UploadFile] = File(None),
    repo_url: Optional[str] = Form(None),
    input_data: Optional[str] = Form(None),  # JSON array of input strings
):
    """
    Judge code submission with optional input data

    - main_files: JSON array of main files to execute
    - files: Multiple files maintaining folder structure
    - repo_url: Git repository URL (alternative to files)
    - input_data: JSON array of input strings for programs that require user input
    """
    # Parse main_files
    try:
        main_files_list = json.loads(main_files)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid main_files format")

    # Parse input_data if provided
    input_list = None
    logger.info(f"Received input_data: {input_data}")
    if input_data:
        try:
            input_list = json.loads(input_data)
            if not isinstance(input_list, list):
                raise ValueError("Input data must be an array")
        except (json.JSONDecodeError, ValueError):
            raise HTTPException(
                status_code=400, detail="Invalid input_data format - must be JSON array"
            )

    # Auto-detect language from file extensions
    language = detect_language_from_files(main_files_list)

    # Validate input: either files or repo_url must be provided
    if not files and not repo_url:
        raise HTTPException(
            status_code=400, detail="Either files or repo_url must be provided"
        )
    if files and repo_url:
        raise HTTPException(
            status_code=400, detail="Provide either files or repo_url, not both"
        )

    # Create temporary workspace
    workspace = None
    try:
        # Create unique temporary directory
        workspace = tempfile.mkdtemp(prefix=f"judge_{uuid.uuid4().hex}_")

        if repo_url:
            # Clone repository
            await clone_repo(repo_url, workspace)
        else:
            # Validate total upload size
            total_upload_size = 0
            file_contents = []

            # Pre-read all files to check total size
            for file in files:
                content = await file.read()
                if len(content) > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File {file.filename} exceeds individual size limit",
                    )

                total_upload_size += len(content)
                file_contents.append((file.filename, content))

            # Check total size limit
            if total_upload_size > MAX_TOTAL_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"Total upload size ({total_upload_size / 1024 / 1024:.2f}MB) exceeds limit ({MAX_TOTAL_SIZE / 1024 / 1024:.2f}MB)",
                )

            # Save uploaded files maintaining structure
            for filename, content in file_contents:
                # Create file path
                file_path = os.path.join(workspace, filename)

                # Create directories if needed
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                # Write file
                with open(file_path, "wb") as f:
                    f.write(content)

        # Execute code with input data
        result = await executor.execute_code(
            language, main_files_list, workspace, input_list
        )
        logger.info(f"Execution result: {result}")
        return JSONResponse(content=result.model_dump())

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up temporary files
        if workspace and os.path.exists(workspace):
            try:
                shutil.rmtree(workspace)
            except Exception as e:
                print(f"Error cleaning up workspace: {e}")


@app.get("/languages")
async def get_supported_languages():
    """Get supported programming languages with auto-detection info"""
    return {
        "languages": [
            {"id": "python", "name": "Python 3", "extensions": [".py"]},
            {"id": "java", "name": "Java", "extensions": [".java", ".class"]},
            {"id": "c", "name": "C", "extensions": [".c"]},
            {"id": "cpp", "name": "C++", "extensions": [".cpp", ".cc", ".cxx", ".c++"]},
        ],
        "note": "Language is automatically detected from file extensions. For Java, both source (.java) and compiled (.class) files are supported.",
        "input_support": "All languages support automatic input detection and handling for interactive programs.",
    }


# Example usage endpoints for testing
@app.get("/examples/input-patterns")
async def get_input_pattern_examples():
    """Get examples of supported input patterns for each language"""
    return {
        "python": [
            'name = input("Enter your name: ")',
            'age = int(input("Enter your age: "))',
            'score = float(input("Enter score: "))',
            "input()  # Simple input without assignment",
        ],
        "java": [
            "String name = scanner.nextLine();",
            "int age = scanner.nextInt();",
            "double score = scanner.nextDouble();",
            "scanner.next();  # Direct call",
        ],
        "c": ['scanf("%s", name);', 'scanf("%d", &age);', 'scanf("%f", &score);'],
        "cpp": ["cin >> name;", "cin >> age;", "getline(cin, fullName);"],
    }


@app.post("/test-input-analysis")
async def test_input_analysis():
    """Test endpoint with sample code for input analysis"""

    # Sample Python code with inputs
    sample_code = {
        "main.py": """
name = input("Enter your name: ")
age = int(input("Enter your age: "))
score = float(input("Enter your score: "))

print(f"Hello {name}")
print(f"You are {age} years old")
print(f"Your score is {score}")

# Simple input without assignment
input("Press enter to continue...")
"""
    }

    # Test the analysis
    analysis_result = executor.analyze_input_patterns("python", sample_code)

    return {
        "sample_code": sample_code,
        "analysis": analysis_result.model_dump(),
        "suggested_inputs": [
            "John Doe",  # for name
            "25",  # for age
            "95.5",  # for score
            "",  # for press enter
        ],
    }
