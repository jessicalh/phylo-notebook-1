#!/usr/bin/env python3
"""
Utility script to read specific cells from Jupyter notebooks for efficient debugging.
Prevents token waste and handles large notebooks gracefully.
"""

import json
import argparse
import sys
import io
from typing import List, Dict, Optional, Union
import re

class NotebookReader:
    """Read and extract specific cells from Jupyter notebooks."""

    def __init__(self, notebook_path: str):
        """Initialize with notebook path."""
        self.notebook_path = notebook_path
        self.notebook = None
        self.cells = []
        self.load_notebook()

    def load_notebook(self):
        """Load the notebook file."""
        try:
            with open(self.notebook_path, 'r', encoding='utf-8') as f:
                self.notebook = json.load(f)
                self.cells = self.notebook.get('cells', [])
        except FileNotFoundError:
            print(f"ERROR: Notebook not found: {self.notebook_path}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid notebook format: {e}")
            sys.exit(1)

    def get_cell_summary(self) -> List[Dict]:
        """Get a summary of all cells with their types and first lines."""
        summary = []
        for i, cell in enumerate(self.cells):
            cell_info = {
                'index': i,
                'type': cell.get('cell_type', 'unknown'),
                'lines': len(cell.get('source', [])),
            }

            # Get first meaningful line
            source = cell.get('source', [])
            if source:
                if isinstance(source, list):
                    first_line = source[0] if source else ''
                    # Try to find a more meaningful line if first is empty
                    for line in source[:5]:
                        if line.strip() and not line.strip().startswith('#='):
                            first_line = line
                            break
                else:
                    first_line = str(source).split('\n')[0]

                cell_info['first_line'] = first_line[:100].strip()
            else:
                cell_info['first_line'] = '[empty cell]'

            # Check for specific content
            full_source = ''.join(source) if isinstance(source, list) else source

            # Identify key cells
            if 'COMPREHENSIVE INSTALLATION' in full_source:
                cell_info['tag'] = 'INSTALLATION'
            elif 'COMPREHENSIVE IMPORTS' in full_source:
                cell_info['tag'] = 'IMPORTS'
            elif 'HELPER FUNCTIONS' in full_source:
                cell_info['tag'] = 'HELPERS'
            elif '@safe_cell_execution' in full_source:
                # Extract function name
                match = re.search(r'@safe_cell_execution\("([^"]+)"\)', full_source)
                if match:
                    cell_info['tag'] = f'FUNCTION: {match.group(1)}'

            # Check for errors in output
            if 'outputs' in cell:
                for output in cell.get('outputs', []):
                    if output.get('output_type') == 'error':
                        cell_info['has_error'] = True
                        cell_info['error_type'] = output.get('ename', 'Unknown')
                    elif 'text' in output:
                        text = output.get('text', '')
                        if isinstance(text, list):
                            text = ''.join(text)
                        if 'error' in text.lower() or 'exception' in text.lower():
                            cell_info['has_output_error'] = True

            summary.append(cell_info)

        return summary

    def get_cell(self, index: int) -> Optional[Dict]:
        """Get a specific cell by index."""
        if 0 <= index < len(self.cells):
            return self.cells[index]
        return None

    def get_cells_by_type(self, cell_type: str) -> List[Dict]:
        """Get all cells of a specific type (code/markdown)."""
        return [cell for cell in self.cells if cell.get('cell_type') == cell_type]

    def get_initialization_cells(self) -> List[Dict]:
        """Get cells related to initialization (installation, imports, setup)."""
        init_cells = []
        for i, cell in enumerate(self.cells):
            if cell.get('cell_type') != 'code':
                continue

            source = cell.get('source', [])
            full_source = ''.join(source) if isinstance(source, list) else source

            # Check for initialization patterns
            if any(pattern in full_source for pattern in [
                'COMPREHENSIVE INSTALLATION',
                'COMPREHENSIVE IMPORTS',
                'HELPER FUNCTIONS',
                'safe_install',
                'safe_import',
                'import subprocess',
                'from datetime import datetime',
                'FileManager',
                'ProgressTracker',
                'CheckpointManager'
            ]):
                init_cells.append({
                    'index': i,
                    'cell': cell,
                    'type': self._identify_init_type(full_source)
                })

        return init_cells

    def _identify_init_type(self, source: str) -> str:
        """Identify the type of initialization cell."""
        if 'COMPREHENSIVE INSTALLATION' in source:
            return 'INSTALLATION'
        elif 'COMPREHENSIVE IMPORTS' in source:
            return 'IMPORTS'
        elif 'HELPER FUNCTIONS' in source:
            return 'HELPERS'
        elif 'safe_install' in source:
            return 'INSTALL_FUNCTION'
        elif 'safe_import' in source:
            return 'IMPORT_FUNCTION'
        else:
            return 'SETUP'

    def get_error_cells(self) -> List[Dict]:
        """Get cells that have errors in their output."""
        error_cells = []
        for i, cell in enumerate(self.cells):
            if cell.get('cell_type') != 'code':
                continue

            # Check outputs for errors
            for output in cell.get('outputs', []):
                if output.get('output_type') == 'error':
                    error_cells.append({
                        'index': i,
                        'cell': cell,
                        'error': {
                            'type': output.get('ename', 'Unknown'),
                            'value': output.get('evalue', 'No error message'),
                            'traceback': output.get('traceback', [])
                        }
                    })
                    break

                # Also check for error text in regular output
                if 'text' in output:
                    text = output.get('text', '')
                    if isinstance(text, list):
                        text = ''.join(text)

                    if any(err in text.lower() for err in [
                        'error:', 'exception:', 'failed:', 'traceback'
                    ]):
                        error_cells.append({
                            'index': i,
                            'cell': cell,
                            'error': {
                                'type': 'OutputError',
                                'value': 'Error text in output',
                                'text': text[:500]  # First 500 chars
                            }
                        })
                        break

        return error_cells

    def get_cell_source(self, index: int, max_lines: int = None) -> Optional[str]:
        """Get the source code of a specific cell."""
        cell = self.get_cell(index)
        if not cell:
            return None

        source = cell.get('source', [])
        if isinstance(source, list):
            if max_lines:
                source = source[:max_lines]
            return ''.join(source)
        return str(source)

    def get_cell_output(self, index: int, max_lines: int = None) -> Optional[str]:
        """Get the output of a specific cell."""
        cell = self.get_cell(index)
        if not cell:
            return None

        outputs = []
        for output in cell.get('outputs', []):
            if output.get('output_type') == 'error':
                outputs.append(f"ERROR: {output.get('ename')}: {output.get('evalue')}")
                if output.get('traceback'):
                    outputs.append('\nTraceback:')
                    traceback = output.get('traceback', [])
                    if max_lines:
                        traceback = traceback[:max_lines]
                    outputs.extend(traceback)

            elif 'text' in output:
                text = output.get('text', '')
                if isinstance(text, list):
                    if max_lines:
                        text = text[:max_lines]
                    outputs.extend(text)
                else:
                    outputs.append(str(text))

            elif 'data' in output:
                data = output.get('data', {})
                if 'text/plain' in data:
                    outputs.append(data['text/plain'])

        return '\n'.join(outputs) if outputs else 'No output'

    def search_cells(self, pattern: str, case_sensitive: bool = False) -> List[Dict]:
        """Search for cells containing a specific pattern."""
        results = []
        flags = 0 if case_sensitive else re.IGNORECASE
        regex = re.compile(pattern, flags)

        for i, cell in enumerate(self.cells):
            source = cell.get('source', [])
            full_source = ''.join(source) if isinstance(source, list) else source

            if regex.search(full_source):
                results.append({
                    'index': i,
                    'type': cell.get('cell_type'),
                    'matches': regex.findall(full_source)[:3]  # First 3 matches
                })

        return results

    def format_cell_display(self, index: int, include_output: bool = True) -> str:
        """Format a cell for display."""
        cell = self.get_cell(index)
        if not cell:
            return f"Cell {index} not found"

        output = []
        output.append(f"\n{'='*60}")
        output.append(f"CELL {index} ({cell.get('cell_type', 'unknown')})")
        output.append(f"{'='*60}")

        # Add source
        source = self.get_cell_source(index)
        if source:
            output.append("SOURCE:")
            output.append(source)

        # Add output if requested
        if include_output and cell.get('cell_type') == 'code':
            cell_output = self.get_cell_output(index)
            if cell_output:
                output.append("\nOUTPUT:")
                output.append(cell_output)

        return '\n'.join(output)


def main():
    """Command line interface for notebook reader."""
    # Set UTF-8 encoding for output
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    parser = argparse.ArgumentParser(description='Read specific cells from Jupyter notebooks')
    parser.add_argument('notebook', help='Path to the notebook file')
    parser.add_argument('--summary', action='store_true', help='Show summary of all cells')
    parser.add_argument('--cell', type=int, help='Show specific cell by index')
    parser.add_argument('--init', action='store_true', help='Show initialization cells')
    parser.add_argument('--errors', action='store_true', help='Show cells with errors')
    parser.add_argument('--search', help='Search for pattern in cells')
    parser.add_argument('--no-output', action='store_true', help='Don\'t show cell outputs')

    args = parser.parse_args()

    reader = NotebookReader(args.notebook)

    if args.summary:
        summary = reader.get_cell_summary()
        print(f"\nNotebook has {len(summary)} cells:\n")
        for cell_info in summary:
            tag = f" [{cell_info.get('tag')}]" if 'tag' in cell_info else ""
            error = " [ERROR]" if cell_info.get('has_error') else ""
            print(f"Cell {cell_info['index']:3}: {cell_info['type']:8} ({cell_info['lines']:4} lines){tag}{error}")
            print(f"         {cell_info['first_line']}")

    elif args.cell is not None:
        print(reader.format_cell_display(args.cell, not args.no_output))

    elif args.init:
        init_cells = reader.get_initialization_cells()
        print(f"\nFound {len(init_cells)} initialization cells:\n")
        for cell_info in init_cells:
            print(f"Cell {cell_info['index']}: {cell_info['type']}")
            if not args.no_output:
                print(reader.format_cell_display(cell_info['index'], False))

    elif args.errors:
        error_cells = reader.get_error_cells()
        if error_cells:
            print(f"\nFound {len(error_cells)} cells with errors:\n")
            for cell_info in error_cells:
                print(f"\nCell {cell_info['index']}:")
                print(f"  Error Type: {cell_info['error']['type']}")
                print(f"  Error Value: {cell_info['error']['value']}")
                if not args.no_output:
                    print(reader.format_cell_display(cell_info['index']))
        else:
            print("No error cells found")

    elif args.search:
        results = reader.search_cells(args.search)
        print(f"\nFound pattern in {len(results)} cells:")
        for result in results:
            print(f"Cell {result['index']} ({result['type']}): {result['matches']}")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()