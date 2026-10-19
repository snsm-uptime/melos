"""TOON (Text Object Oriented Notation) encoder/decoder for LLM prompts"""
from typing import Any, Dict, List, Optional


class TOONEncoder:
    """Encodes data to TOON format for LLM consumption"""

    @staticmethod
    def encode_dict(data: Dict[str, Any], indent: int = 0) -> str:
        """Encode dictionary to TOON keyed format"""
        lines = []
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{'  ' * indent}{key}:")
                lines.append(TOONEncoder.encode_dict(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{'  ' * indent}{key}:")
                for item in value:
                    if isinstance(item, dict):
                        lines.append(TOONEncoder.encode_dict(item, indent + 1))
                    else:
                        lines.append(f"{'  ' * (indent + 1)}- {TOONEncoder._escape(str(item))}")
            else:
                lines.append(f"{'  ' * indent}{key}: {TOONEncoder._escape(str(value))}")
        return "\n".join(lines)

    @staticmethod
    def encode_list(items: List[Any]) -> str:
        """Encode list to TOON tabular format"""
        if not items:
            return ""

        if isinstance(items[0], dict):
            # Determine columns
            columns = set()
            for item in items:
                columns.update(item.keys())
            columns = sorted(list(columns))

            # Header
            lines = ["|" + "|".join(f" {col} " for col in columns) + "|"]
            lines.append("|" + "|".join("-" * (len(col) + 2) for col in columns) + "|")

            # Rows
            for item in items:
                row = [str(item.get(col, "")) for col in columns]
                lines.append("|" + "|".join(f" {val} " for val in row) + "|")

            return "\n".join(lines)
        else:
            return "\n".join(f"- {TOONEncoder._escape(str(item))}" for item in items)

    @staticmethod
    def _escape(text: str) -> str:
        """Escape special characters in TOON"""
        return text.replace("|", "\\|").replace("\n", "\\n")


class TOONDecoder:
    """Decodes TOON format responses from LLM"""

    @staticmethod
    def decode_dict(text: str) -> Dict[str, Any]:
        """Parse TOON keyed format to dictionary"""
        result = {}
        lines = text.strip().split("\n")
        current_key = None
        current_list = []
        indent_stack = [(-1, {})]

        for line in lines:
            if not line.strip():
                continue

            indent = len(line) - len(line.lstrip())
            stripped = line.strip()

            if ":" in stripped:
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip()

                result[key] = value if value else {}
                current_key = key
            elif stripped.startswith("-"):
                item = stripped[1:].strip()
                if current_key:
                    if current_key not in result or not isinstance(result[current_key], list):
                        result[current_key] = []
                    result[current_key].append(item)

        return result

    @staticmethod
    def decode_list(text: str) -> List[Dict[str, str]]:
        """Parse TOON tabular format to list of dicts"""
        lines = text.strip().split("\n")
        if not lines or "|" not in lines[0]:
            # Try simple list format
            return [{"value": line.strip()} for line in lines if line.strip() and not line.startswith("-")]

        # Parse table format
        rows = [line for line in lines if line.startswith("|")]
        if len(rows) < 2:
            return []

        # Extract header
        header_row = rows[0]
        columns = [col.strip() for col in header_row.split("|")[1:-1]]

        # Parse data rows (skip separator)
        result = []
        for row in rows[2:]:
            values = [val.strip() for val in row.split("|")[1:-1]]
            result.append(dict(zip(columns, values)))

        return result
