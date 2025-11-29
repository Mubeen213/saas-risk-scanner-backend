import re
from typing import Any


def bind_named(query: str, params: dict[str, Any]) -> tuple[str, list[Any]]:
    """
    Convert named parameters (:param_name) to positional parameters ($1, $2, etc.)
    for asyncpg compatibility.
    """
    pattern = re.compile(r":(\w+)")
    matches = pattern.findall(query)
    values: list[Any] = []
    param_index = 1
    result_query = query

    seen: set[str] = set()
    # Sort by length descending to avoid substring replacement issues
    # e.g., :email_verified should be replaced before :email
    unique_matches = sorted(set(matches), key=len, reverse=True)

    for match in unique_matches:
        if match in seen:
            continue
        seen.add(match)
        if match not in params:
            raise ValueError(f"Missing parameter: {match}")
        # Use word boundary regex to avoid partial replacements
        result_query = re.sub(rf":{match}\b", f"${param_index}", result_query)
        values.append(params[match])
        param_index += 1

    return result_query, values
