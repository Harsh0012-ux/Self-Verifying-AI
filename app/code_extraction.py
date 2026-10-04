"""Normalize LLM completions before they are handed to the Python sandbox."""
import re


_FENCED_CODE = re.compile(r"```(?:python|py)?\s*\n?(.*?)```", re.IGNORECASE | re.DOTALL)
_PYTHON_START = re.compile(
    r"^\s*(?:async\s+def\s+|def\s+|class\s+|from\s+\S+\s+import\s+|import\s+\S+|@|#)"
)


def extract_python_code(completion: str) -> str:
    """Return a Python code block when a completion uses Markdown fences.

    The model is prompted to emit code only, so unfenced text is deliberately
    preserved: silently guessing at prose boundaries would be less reliable
    than letting the sandbox report the syntax error.
    """
    matches = _FENCED_CODE.findall(completion)
    if matches:
        return max(matches, key=len).strip()
    lines = completion.strip().splitlines()
    start = next((index for index, line in enumerate(lines) if _PYTHON_START.match(line)), 0)
    candidate = "\n".join(lines[start:]).strip()
    # If a natural-language epilogue makes the source invalid, retain the
    # longest syntactically valid prefix.  Valid code is otherwise untouched.
    for end in range(len(candidate.splitlines()), 0, -1):
        prefix = "\n".join(candidate.splitlines()[:end])
        try:
            compile(prefix, "<llm-completion>", "exec")
        except SyntaxError:
            continue
        return prefix.strip()
    return candidate
