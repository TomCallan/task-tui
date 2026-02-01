import os
import re
import sys
from pathlib import Path
from typing import Iterable, List
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.widgets import DirectoryTree, Footer, Header, Markdown, Checkbox, Static, Label, ProgressBar
from textual.binding import Binding

class FilteredDirectoryTree(DirectoryTree):
    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return [path for path in paths if path.is_dir() or path.suffix.lower() == ".md"]

class MarkdownViewerApp(App):
    CSS = """
    Screen {
        layout: horizontal;
    }

    #sidebar {
        width: 30;
        height: 100%;
        dock: left;
        border-right: solid $primary;
        background: $surface;
    }

    #content {
        height: 100%;
        width: 1fr;
        padding: 0 0;
    }
    
    #content-scroll {
        height: 1fr;
        padding: 1 2;
    }

    ProgressBar {
        dock: top;
        margin: 1 2;
        width: 1fr;
        display: none;
    }
    
    Checkbox {
        padding: 0;
        margin: 0 0 0 1;
        height: auto;
    }
    
    Markdown {
        margin: 0;
        padding: 0 0 1 0;
    }
    
    .hide-completed .completed {
        display: none;
    }
    """

    BINDINGS = [
        Binding("q", "quit_save", "Quit (Save)"),
        Binding("Q", "force_quit", "Force Quit"),
        Binding("ctrl+q", "force_quit", show=False),
        Binding("r", "reload", "Reload"),
        Binding("d", "toggle_dark", "Theme"),
        Binding("h", "toggle_hide_completed", "Hide Done"),
        Binding("j", "next_item", "Next"),
        Binding("k", "prev_item", "Prev"),
        Binding("space", "toggle_check", "Toggle"),
    ]

    def __init__(self):
        super().__init__()
        self.current_file = None
        self.last_mtime = 0
        self.checkbox_map = {} 
        self.hide_completed = False
        self.load_count = 0
        
        # Buffer for edits
        self.file_content: List[str] = []
        self.original_content: List[str] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            FilteredDirectoryTree("./", id="tree-view"),
            id="sidebar",
        )
        yield Container(
            ProgressBar(id="progress-bar", show_eta=False, show_percentage=True),
            VerticalScroll(id="content-scroll"),
            id="content"
        )
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(1.0, self.check_for_changes)

    def action_quit_save(self) -> None:
        """Quit the app, saving changes if any."""
        if self.is_dirty:
            self.save_file()
            self.notify("Changes saved.", title="Saved")
        self.exit()

    def action_force_quit(self) -> None:
        """Quit without saving."""
        self.exit()

    def action_toggle_dark(self) -> None:
        self.theme = "textual-light" if self.theme == "textual-dark" else "textual-dark"

    def action_toggle_hide_completed(self) -> None:
        self.hide_completed = not self.hide_completed
        scroll_container = self.query_one("#content-scroll")
        if self.hide_completed:
            scroll_container.add_class("hide-completed")
            self.notify("Hiding completed items")
            # If focus is on a completed item, move it to a visible one
            focused = self.screen.focused
            if isinstance(focused, Checkbox) and focused.has_class("completed"):
                self.action_next_item()
        else:
            scroll_container.remove_class("hide-completed")
            self.notify("Showing all items")

    def action_next_item(self) -> None:
        # Filter visible checkboxes
        if self.hide_completed:
            checkboxes = list(self.query(Checkbox).exclude(".completed"))
        else:
            checkboxes = list(self.query(Checkbox))
            
        if not checkboxes:
            return
            
        focused = self.screen.focused
        if focused in checkboxes:
            idx = checkboxes.index(focused)
            if idx < len(checkboxes) - 1:
                checkboxes[idx + 1].focus()
        else:
            # If focus is elsewhere, jump to first item
            checkboxes[0].focus()

    def action_prev_item(self) -> None:
        if self.hide_completed:
            checkboxes = list(self.query(Checkbox).exclude(".completed"))
        else:
            checkboxes = list(self.query(Checkbox))

        if not checkboxes:
            return
            
        focused = self.screen.focused
        if focused in checkboxes:
            idx = checkboxes.index(focused)
            if idx > 0:
                checkboxes[idx - 1].focus()
        else:
            checkboxes[0].focus()
        
    def action_toggle_check(self) -> None:
        focused = self.screen.focused
        if isinstance(focused, Checkbox):
            focused.toggle()

    @property
    def is_dirty(self) -> bool:
        return self.file_content != self.original_content

    def check_for_changes(self) -> None:
        if not self.current_file:
            return
        try:
            current_mtime = os.path.getmtime(self.current_file)
            if current_mtime != self.last_mtime:
                if self.is_dirty:
                    self.notify("External changes detected but ignored (unsaved local changes).", severity="warning", title="Conflict")
                else:
                    self.notify("File changed externally. Reloading...", title="Sync")
                    self.load_file(self.current_file)
        except OSError:
            pass

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        if event.path.suffix.lower() == ".md":
            if self.is_dirty:
                self.save_file() 
                self.notify("Previous file saved.", title="Saved")
            self.load_file(str(event.path))

    def update_progress(self) -> None:
        total = 0
        completed = 0
        for cb in self.query(Checkbox):
            total += 1
            if cb.value:
                completed += 1
                cb.add_class("completed")
            else:
                cb.remove_class("completed")
        
        try:
            bar = self.query_one("#progress-bar", ProgressBar)
            if total > 0:
                bar.display = True
                bar.update(total=total, progress=completed)
            else:
                bar.display = False
        except Exception:
            pass

    def load_file(self, file_path: str):
        self.current_file = file_path
        self.load_count += 1
        
        try:
            self.last_mtime = os.path.getmtime(file_path)
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            self.file_content = list(lines)
            self.original_content = list(lines)
        except Exception as e:
            self.query_one("#content-scroll", VerticalScroll).mount(Static(f"Error reading file: {e}", style="red"))
            return

        self.refresh_ui_content()

    def refresh_ui_content(self):
        content_container = self.query_one("#content-scroll", VerticalScroll)
        content_container.remove_children()
        
        self.checkbox_map = {}
        
        checkbox_pattern = re.compile(r"^(\s*)-\s\[([ xX])\]\s+(.*)$")
        current_text_block = []

        for i, line in enumerate(self.file_content):
            match = checkbox_pattern.match(line)
            
            if match:
                if current_text_block:
                    content_container.mount(Markdown("".join(current_text_block)))
                    current_text_block = []

                indentation, status, text = match.groups()
                is_checked = status.lower() == 'x'
                
                cb_id = f"cb_{self.load_count}_{i}"
                cb = Checkbox(text.strip(), value=is_checked, id=cb_id)
                if is_checked:
                    cb.add_class("completed")

                indent_level = len(indentation.replace("\t", "    "))
                cb.styles.margin = (0, 0, 0, indent_level + 1)
                
                content_container.mount(cb)
                
                self.checkbox_map[cb_id] = {
                    "line_index": i,
                    "indentation": indentation,
                    "text": text
                }
            else:
                current_text_block.append(line)

        if current_text_block:
            content_container.mount(Markdown("".join(current_text_block)))
            
        self.sub_title = str(self.current_file)
        self.update_progress()
        
        if self.hide_completed:
            content_container.add_class("hide-completed")

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if not self.current_file:
            return

        # Update UI Progress
        self.update_progress()

        # Update Memory Buffer
        checkbox_id = event.checkbox.id
        if checkbox_id in self.checkbox_map:
            data = self.checkbox_map[checkbox_id]
            line_idx = data["line_index"]
            indent = data["indentation"]
            text = data["text"] 
            
            new_mark = "x" if event.value else " "
            new_line = f"{indent}- [{new_mark}] {text}\n"
            
            # Ensure line_idx is valid
            if 0 <= line_idx < len(self.file_content):
                old_line = self.file_content[line_idx]
                if old_line.endswith("\n") and not new_line.endswith("\n"):
                    new_line += "\n"
                
                self.file_content[line_idx] = new_line
                self.sub_title = f"{self.current_file}{' *' if self.is_dirty else ''}"

    def save_file(self):
        if not self.current_file:
            return
        try:
            with open(self.current_file, "w", encoding="utf-8") as f:
                f.writelines(self.file_content)
            
            # Update sync state
            self.last_mtime = os.path.getmtime(self.current_file)
            self.original_content = list(self.file_content)
            self.sub_title = str(self.current_file)
        except Exception as e:
            self.notify(f"Failed to save: {e}", severity="error")

def main():
    app = MarkdownViewerApp()
    app.run()

if __name__ == "__main__":
    main()
