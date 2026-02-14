"""
Progress display for OJHunt Lite CLI.

Supports TUI mode with rich Live display and plain mode for non-TTY environments.
"""

import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


@dataclass
class TaskInfo:
    key: str
    crawler: str
    title: str
    username: str
    status: TaskStatus = TaskStatus.PENDING
    solved: Optional[int] = None
    submissions: Optional[int] = None
    duration: Optional[float] = None
    error: Optional[str] = None


@dataclass
class ProgressManager:
    tasks: Dict[str, TaskInfo] = field(default_factory=dict)
    task_order: List[str] = field(default_factory=list)
    console: Console = field(default_factory=Console)
    live: Optional[Live] = None
    is_tty: bool = field(default_factory=lambda: sys.stdout.isatty())

    @staticmethod
    def _make_key(crawler: str, username: str) -> str:
        return f"{username}@{crawler}"

    def add_task(self, crawler: str, title: str, username: str) -> str:
        key = self._make_key(crawler, username)
        self.tasks[key] = TaskInfo(
            key=key,
            crawler=crawler,
            title=title,
            username=username,
        )
        self.task_order.append(key)
        return key

    def start_task(self, key: str) -> None:
        if key in self.tasks:
            self.tasks[key].status = TaskStatus.RUNNING
            if self.is_tty and self.live:
                self.live.update(self._build_table())
            else:
                print(f"Querying {self.tasks[key].title}...")

    def complete_task(
        self,
        key: str,
        success: bool,
        solved: Optional[int] = None,
        submissions: Optional[int] = None,
        duration: Optional[float] = None,
        error: Optional[str] = None,
    ) -> None:
        if key in self.tasks:
            task = self.tasks[key]
            task.status = TaskStatus.SUCCESS if success else TaskStatus.ERROR
            task.solved = solved
            task.submissions = submissions
            task.duration = duration
            task.error = error
            if self.is_tty and self.live:
                self.live.update(self._build_table())
            else:
                self._print_task_done(task)

    def _print_task_done(self, task: TaskInfo) -> None:
        if task.status == TaskStatus.SUCCESS:
            print(f"{task.title} done ({task.solved} solved, {task.duration:.2f}s)")
        else:
            print(f"{task.title} ERROR: {task.error}")

    def _build_table(self) -> Table:
        table = Table(show_header=True, header_style="bold", expand=False)
        table.add_column("Crawler", width=20)
        table.add_column("Username", width=20)
        table.add_column("Status", width=40)

        for crawler in self.task_order:
            task = self.tasks[crawler]
            status_text = self._format_status(task)
            table.add_row(task.title, task.username, status_text)

        return table

    def _format_status(self, task: TaskInfo):
        if task.status == TaskStatus.PENDING:
            return Text("Waiting...", style="dim")
        elif task.status == TaskStatus.RUNNING:
            spinner = Spinner("dots", text="Running...")
            return spinner
        elif task.status == TaskStatus.SUCCESS:
            duration_str = f"{task.duration:.2f}s" if task.duration else "N/A"
            return Text(f"OK ({duration_str})", style="green")
        else:
            return Text(f"ERROR: {task.error}", style="red")

    def __enter__(self):
        if self.is_tty:
            self.live = Live(
                self._build_table(),
                console=self.console,
                refresh_per_second=10,
            )
            self.live.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.live:
            self.live.__exit__(exc_type, exc_val, exc_tb)
        return False

    def get_results(self) -> List[Dict[str, Any]]:
        results = []
        for crawler in self.task_order:
            task = self.tasks[crawler]
            result: Dict[str, Any] = {
                "crawler": task.crawler,
                "title": task.title,
                "username": task.username,
                "success": task.status == TaskStatus.SUCCESS,
            }
            if task.status == TaskStatus.SUCCESS:
                result["solved"] = task.solved
                result["submissions"] = task.submissions
                result["duration"] = task.duration
                result["solved_list"] = []
            else:
                result["error"] = task.error or "Unknown error"
            results.append(result)
        return results
