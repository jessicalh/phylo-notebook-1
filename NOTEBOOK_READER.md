# Notebook Reader Utility

A specialized tool for efficiently reading and debugging large Jupyter notebooks without token waste or context overload.

## Motivation

During debugging sessions with large notebooks (especially those with extensive logging and error handling), reading the entire notebook file becomes inefficient and can consume significant tokens in LLM contexts. This utility allows targeted extraction of specific cells, particularly initialization code and error locations.

## Features

- **Summary View**: Quick overview of all cells with types, line counts, and tags
- **Cell Extraction**: Get specific cells by index
- **Initialization Detection**: Automatically find setup/installation/import cells
- **Error Detection**: Find cells with errors in their outputs
- **Pattern Search**: Search for specific patterns across all cells
- **Output Control**: Option to include/exclude cell outputs
- **UTF-8 Support**: Handles emoji and special characters in notebooks

## Installation

No installation required - it's a standalone Python script that only uses standard library modules.

```bash
python notebook_reader.py --help
```

## Usage Examples

### 1. Get Notebook Summary

```bash
python notebook_reader.py notebook.ipynb --summary
```

Output shows all cells with:
- Cell index
- Cell type (code/markdown)
- Line count
- Tags for special cells (INSTALLATION, IMPORTS, HELPERS, etc.)
- Error indicators
- First meaningful line

Example output:
```
Cell   0: markdown (  10 lines)
         # Protein Phylogenetic Analysis Pipeline
Cell   2: code     ( 314 lines) [INSTALLATION]
         # COMPREHENSIVE INSTALLATION CELL WITH LOGGING
Cell   4: code     ( 234 lines) [IMPORTS]
         # COMPREHENSIVE IMPORTS WITH VALIDATION
```

### 2. Extract Specific Cell

```bash
# Get cell 2 with output
python notebook_reader.py notebook.ipynb --cell 2

# Get cell 2 without output (source only)
python notebook_reader.py notebook.ipynb --cell 2 --no-output
```

### 3. Find Initialization Cells

```bash
python notebook_reader.py notebook.ipynb --init
```

Automatically finds and displays:
- Installation cells
- Import cells
- Helper function definitions
- Setup/configuration cells

### 4. Find Error Cells

```bash
python notebook_reader.py notebook.ipynb --errors
```

Detects cells with:
- Python exceptions in output
- Error output types
- Text containing error keywords

### 5. Search for Pattern

```bash
python notebook_reader.py notebook.ipynb --search "MMseqs2"
```

Case-insensitive search across all cells, showing:
- Cell index
- Cell type
- First 3 matches

## Python API Usage

The tool can also be used as a Python module:

```python
from notebook_reader import NotebookReader

# Load notebook
reader = NotebookReader('notebook.ipynb')

# Get summary
summary = reader.get_cell_summary()
for cell in summary:
    print(f"Cell {cell['index']}: {cell['type']}")

# Get specific cell
cell = reader.get_cell(2)
source = reader.get_cell_source(2)
output = reader.get_cell_output(2)

# Find initialization cells
init_cells = reader.get_initialization_cells()
for cell_info in init_cells:
    print(f"Found {cell_info['type']} at cell {cell_info['index']}")

# Find error cells
error_cells = reader.get_error_cells()
for cell_info in error_cells:
    print(f"Error in cell {cell_info['index']}: {cell_info['error']['type']}")

# Search for pattern
results = reader.search_cells('import pandas')
```

## Key Classes and Methods

### NotebookReader Class

**Methods:**
- `get_cell_summary()`: Returns list of cell metadata
- `get_cell(index)`: Get specific cell by index
- `get_initialization_cells()`: Find setup-related cells
- `get_error_cells()`: Find cells with errors
- `search_cells(pattern)`: Search for pattern in cells
- `get_cell_source(index, max_lines)`: Get cell source code
- `get_cell_output(index, max_lines)`: Get cell output

**Cell Identification Logic:**

The reader identifies special cells by looking for key patterns:
- **INSTALLATION**: Contains "COMPREHENSIVE INSTALLATION" or "safe_install"
- **IMPORTS**: Contains "COMPREHENSIVE IMPORTS" or "safe_import"
- **HELPERS**: Contains "HELPER FUNCTIONS"
- **FUNCTIONS**: Decorated with @safe_cell_execution

## Design Decisions

### 1. Minimal Dependencies
Only uses Python standard library to ensure it works anywhere the notebook might be debugged.

### 2. Smart Cell Detection
Uses pattern matching to identify important cells without needing cell metadata or tags.

### 3. Flexible Output
Can return raw data structures for programmatic use or formatted text for CLI.

### 4. Error Resilience
Handles malformed notebooks gracefully and continues processing what it can.

### 5. Memory Efficient
Allows limiting output lines to prevent memory issues with very large outputs.

## Use Cases

### Debugging Workflow

1. **Initial Error Detection**
   ```bash
   python notebook_reader.py failed_notebook.ipynb --errors
   ```

2. **Check Initialization**
   ```bash
   python notebook_reader.py failed_notebook.ipynb --init
   ```

3. **Examine Specific Problem Cell**
   ```bash
   python notebook_reader.py failed_notebook.ipynb --cell 42
   ```

4. **Search for Problematic Function**
   ```bash
   python notebook_reader.py failed_notebook.ipynb --search "run_mmseqs2"
   ```

### Token-Efficient LLM Debugging

Instead of passing entire notebook to LLM:
```python
# Old way - sends entire 80KB notebook
with open('notebook.ipynb', 'r') as f:
    content = f.read()
    send_to_llm(content)  # Wastes tokens

# New way - sends only relevant cells
reader = NotebookReader('notebook.ipynb')
error_cells = reader.get_error_cells()
for cell in error_cells:
    send_to_llm(reader.format_cell_display(cell['index']))  # Efficient
```

## Limitations

1. **No Execution**: Only reads notebooks, doesn't execute cells
2. **No Kernel State**: Can't access variable values or kernel state
3. **Static Analysis**: Can't detect runtime errors that haven't occurred yet
4. **Output Truncation**: Very large outputs may be truncated for display

## Future Enhancements

Potential improvements for v2:
- Export specific cells to new notebook
- Dependency graph between cells
- Execution time analysis from timestamps
- Integration with notebook diff tools
- Support for notebook v3 format
- Real-time monitoring of running notebooks

## Testing

The utility has been tested with:
- Large notebooks (>80KB, >10000 lines)
- Notebooks with Unicode/emoji characters
- Notebooks with errors and exceptions
- Various cell types and output formats

## Conclusion

This utility significantly improves the debugging experience for large Jupyter notebooks by allowing targeted inspection of specific cells. It reduces token usage in LLM contexts and helps quickly identify problem areas without scrolling through thousands of lines of code.

For notebooks with extensive logging and error handling (like our phylogenetic analysis notebook), this tool is essential for efficient debugging and maintenance.