#!/usr/bin/env python3
"""
ALPHA OMEGA - ADVANCED CODE INTELLIGENCE
Codebase understanding and navigation
Version: 2.0.0
"""

import asyncio
import json
import logging
import os
import ast
import re
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class Language(Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPP = "cpp"
    C = "c"
    GO = "go"
    RUST = "rust"
    UNKNOWN = "unknown"


@dataclass
class CodeSymbol:
    name: str
    symbol_type: str
    file_path: str
    line_number: int
    end_line: int = 0
    docstring: str = ""
    signature: str = ""
    parameters: List[str] = field(default_factory=list)
    return_type: str = ""
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.symbol_type,
            "file": self.file_path,
            "line": self.line_number,
            "end_line": self.end_line,
            "docstring": self.docstring[:100] if self.docstring else "",
            "signature": self.signature,
        }


@dataclass
class CodeFile:
    path: str
    language: Language
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    variables: List[str] = field(default_factory=list)
    loc: int = 0
    complexity: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "language": self.language.value,
            "imports": len(self.imports),
            "classes": len(self.classes),
            "functions": len(self.functions),
            "loc": self.loc,
        }


@dataclass
class CodeIssue:
    file_path: str
    line_number: int
    severity: str
    message: str
    rule_id: str
    suggestion: str = ""


class PythonParser:
    """Parse Python source code"""

    def parse_file(self, file_path: Path) -> Tuple[CodeFile, List[CodeSymbol]]:
        """Parse a Python file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()

            tree = ast.parse(source)

            code_file = CodeFile(
                path=str(file_path),
                language=Language.PYTHON,
                loc=len(source.splitlines()),
            )

            symbols = []

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        code_file.imports.append(alias.name)

                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        code_file.imports.append(f"{module}.{alias.name}")

                elif isinstance(node, ast.ClassDef):
                    symbol = self._parse_class(node, file_path)
                    symbols.append(symbol)
                    code_file.classes.append(node.name)

                elif isinstance(node, ast.FunctionDef) or isinstance(
                    node, ast.AsyncFunctionDef
                ):
                    symbol = self._parse_function(node, file_path)
                    symbols.append(symbol)
                    code_file.functions.append(node.name)

                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            code_file.variables.append(target.id)

            return code_file, symbols

        except Exception as e:
            return CodeFile(path=str(file_path), language=Language.PYTHON), []

    def _parse_class(self, node: ast.ClassDef, file_path: Path) -> CodeSymbol:
        """Parse class definition"""
        docstring = ast.get_docstring(node) or ""

        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)

        return CodeSymbol(
            name=node.name,
            symbol_type="class",
            file_path=str(file_path),
            line_number=node.lineno,
            end_line=node.end_lineno or node.lineno,
            docstring=docstring,
            dependencies=bases,
        )

    def _parse_function(self, node, file_path: Path) -> CodeSymbol:
        """Parse function definition"""
        docstring = ast.get_docstring(node) or ""

        params = []
        for arg in node.args.args:
            params.append(arg.arg)

        signature = f"{node.name}({', '.join(params)})"

        return_code_symbol = CodeSymbol(
            name=node.name,
            symbol_type="function",
            file_path=str(file_path),
            line_number=node.lineno,
            end_line=node.end_lineno or node.lineno,
            docstring=docstring,
            signature=signature,
            parameters=params,
        )

        return return_code_symbol


class CodeAnalyzer:
    """Analyze code for issues and metrics"""

    ISSUES = {
        "long_function": {"threshold": 50, "message": "Function is too long"},
        "too_many_params": {"threshold": 7, "message": "Too many parameters"},
        "missing_docstring": {"threshold": 0, "message": "Missing docstring"},
        "complex_condition": {"threshold": 3, "message": "Complex condition"},
    }

    def __init__(self):
        self.logger = logging.getLogger("CodeAnalyzer")

    def analyze_file(
        self, file_path: Path, symbols: List[CodeSymbol]
    ) -> List[CodeIssue]:
        """Analyze file for issues"""
        issues = []

        for symbol in symbols:
            if symbol.symbol_type == "function":
                lines = symbol.end_line - symbol.line_number
                if lines > self.ISSUES["long_function"]["threshold"]:
                    issues.append(
                        CodeIssue(
                            file_path=str(file_path),
                            line_number=symbol.line_number,
                            severity="warning",
                            message=f"Function '{symbol.name}' is too long ({lines} lines)",
                            rule_id="long_function",
                            suggestion="Consider breaking into smaller functions",
                        )
                    )

                if len(symbol.parameters) > self.ISSUES["too_many_params"]["threshold"]:
                    issues.append(
                        CodeIssue(
                            file_path=str(file_path),
                            line_number=symbol.line_number,
                            severity="warning",
                            message=f"Function '{symbol.name}' has too many parameters",
                            rule_id="too_many_params",
                            suggestion="Consider using a configuration object",
                        )
                    )

                if not symbol.docstring:
                    issues.append(
                        CodeIssue(
                            file_path=str(file_path),
                            line_number=symbol.line_number,
                            severity="info",
                            message=f"Function '{symbol.name}' missing docstring",
                            rule_id="missing_docstring",
                            suggestion="Add a docstring to document the function",
                        )
                    )

        return issues


class CodeIntelligence:
    """Main code intelligence system"""

    LANGUAGE_EXTENSIONS = {
        ".py": Language.PYTHON,
        ".js": Language.JAVASCRIPT,
        ".ts": Language.TYPESCRIPT,
        ".java": Language.JAVA,
        ".cpp": Language.CPP,
        ".c": Language.C,
        ".go": Language.GO,
        ".rs": Language.RUST,
    }

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger("CodeIntelligence")

        self._parsers = {
            Language.PYTHON: PythonParser(),
        }
        self._analyzer = CodeAnalyzer()

        self._files: Dict[str, CodeFile] = {}
        self._symbols: Dict[str, CodeSymbol] = {}
        self._symbol_index: Dict[str, List[str]] = {}

    async def initialize(self) -> bool:
        """Initialize code intelligence"""
        self.logger.info("Code Intelligence initialized")
        return True

    def detect_language(self, file_path: Path) -> Language:
        """Detect language from file extension"""
        ext = file_path.suffix.lower()
        return self.LANGUAGE_EXTENSIONS.get(ext, Language.UNKNOWN)

    async def index_directory(self, directory: Path) -> Dict[str, Any]:
        """Index all code files in a directory"""
        results = {
            "files_indexed": 0,
            "symbols_found": 0,
            "errors": [],
        }

        for file_path in directory.rglob("*"):
            if file_path.is_file():
                language = self.detect_language(file_path)

                if language == Language.UNKNOWN:
                    continue

                if file_path.name.startswith("__"):
                    continue

                try:
                    await self.index_file(file_path)
                    results["files_indexed"] += 1
                except Exception as e:
                    results["errors"].append(f"{file_path}: {e}")

        results["symbols_found"] = len(self._symbols)

        self.logger.info(
            f"Indexed {results['files_indexed']} files, {results['symbols_found']} symbols"
        )
        return results

    async def index_file(self, file_path: Path) -> CodeFile:
        """Index a single file"""
        language = self.detect_language(file_path)

        parser = self._parsers.get(language)
        if not parser:
            return CodeFile(path=str(file_path), language=language)

        code_file, symbols = parser.parse_file(file_path)

        self._files[str(file_path)] = code_file

        for symbol in symbols:
            key = f"{symbol.symbol_type}:{symbol.name}"
            self._symbols[f"{str(file_path)}:{key}"] = symbol

            if symbol.name not in self._symbol_index:
                self._symbol_index[symbol.name] = []
            self._symbol_index[symbol.name].append(str(file_path))

        return code_file

    def find_symbol(self, name: str) -> List[CodeSymbol]:
        """Find symbols by name"""
        results = []

        for key, symbol in self._symbols.items():
            if symbol.name == name:
                results.append(symbol)

        return results

    def find_references(self, symbol_name: str) -> List[Tuple[str, int]]:
        """Find all references to a symbol"""
        references = []

        for file_path, code_file in self._files.items():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                for i, line in enumerate(lines):
                    if re.search(rf"\b{re.escape(symbol_name)}\b", line):
                        references.append((file_path, i + 1))
            except:
                pass

        return references

    def get_definition(self, symbol_name: str) -> Optional[CodeSymbol]:
        """Get symbol definition"""
        symbols = self.find_symbol(symbol_name)
        return symbols[0] if symbols else None

    def get_file_overview(self, file_path: str) -> Dict[str, Any]:
        """Get overview of a file"""
        code_file = self._files.get(file_path)
        if not code_file:
            return {}

        file_symbols = [s for k, s in self._symbols.items() if k.startswith(file_path)]

        return {
            "file": code_file.to_dict(),
            "symbols": [s.to_dict() for s in file_symbols],
        }

    async def analyze_codebase(self) -> Dict[str, Any]:
        """Analyze entire codebase"""
        all_issues = []

        for file_path, code_file in self._files.items():
            file_symbols = [
                s for k, s in self._symbols.items() if k.startswith(file_path)
            ]

            issues = self._analyzer.analyze_file(Path(file_path), file_symbols)
            all_issues.extend(issues)

        return {
            "files": len(self._files),
            "symbols": len(self._symbols),
            "issues": len(all_issues),
            "issues_by_severity": {
                "error": sum(1 for i in all_issues if i.severity == "error"),
                "warning": sum(1 for i in all_issues if i.severity == "warning"),
                "info": sum(1 for i in all_issues if i.severity == "info"),
            },
        }

    def search_code(self, query: str) -> List[Dict[str, Any]]:
        """Search code by pattern"""
        results = []

        query_lower = query.lower()

        for file_path, code_file in self._files.items():
            if query_lower in file_path.lower():
                results.append(
                    {
                        "type": "file",
                        "path": file_path,
                        "match": file_path,
                    }
                )

        for key, symbol in self._symbols.items():
            if query_lower in symbol.name.lower():
                results.append(
                    {
                        "type": "symbol",
                        "path": symbol.file_path,
                        "name": symbol.name,
                        "symbol_type": symbol.symbol_type,
                        "line": symbol.line_number,
                    }
                )

        return results

    def get_call_graph(self, symbol_name: str) -> Dict[str, Any]:
        """Get call graph for a symbol"""
        symbol = self.get_definition(symbol_name)
        if not symbol:
            return {}

        return {
            "symbol": symbol.to_dict(),
            "called_by": [],
            "calls": [],
        }

    def suggest_refactoring(self, file_path: str) -> List[Dict[str, Any]]:
        """Suggest refactorings for a file"""
        suggestions = []

        code_file = self._files.get(file_path)
        if not code_file:
            return suggestions

        file_symbols = [s for k, s in self._symbols.items() if k.startswith(file_path)]

        issues = self._analyzer.analyze_file(Path(file_path), file_symbols)

        for issue in issues:
            suggestions.append(
                {
                    "type": "refactor",
                    "line": issue.line_number,
                    "message": issue.message,
                    "suggestion": issue.suggestion,
                }
            )

        return suggestions
