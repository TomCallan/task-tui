# Task TUI

A terminal-based interface for viewing and managing Markdown task lists.

## Installation

### Install from source (for development or global installation)

1. Clone or download this repository
2. Navigate to the project directory
3. Install in editable mode:

```bash
pip install -e .
```

This will install `task-tui` globally on your system, making it accessible from anywhere.

**Windows:** The executable will be installed to `%APPDATA%\Python\Python3XX\Scripts\task-tui.exe`. Ensure this directory is in your PATH.

**Linux/Mac:** The executable will be installed to `~/.local/bin/task-tui`. Ensure this directory is in your PATH:

```bash
# Add to ~/.bashrc or ~/.zshrc if needed
export PATH=$PATH:~/.local/bin
```

## Usage

Run the tool from your terminal:

```bash
task-tui
```

Navigate through your directory, select a Markdown file, and manage your tasks.

## Features

- Browse directories and select Markdown files.
- View Markdown content.
- Interactive checkboxes: toggle tasks directly in the TUI.
- Hide completed tasks.
- Dark/Light mode.
- Progress bar.
