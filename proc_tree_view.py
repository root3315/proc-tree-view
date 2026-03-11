#!/usr/bin/env python3
"""
proc-tree-view: Real-time process tree visualization CLI tool.
Displays running processes in a tree structure with live updates.
"""

import argparse
import os
import sys
import time
from collections import defaultdict
from datetime import datetime

try:
    import psutil
except ImportError:
    print("Error: psutil library required. Install with: pip install psutil")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.tree import Tree
    from rich.live import Live
    from rich.panel import Panel
    from rich.style import Style
    from rich.text import Text
except ImportError:
    print("Error: rich library required. Install with: pip install rich")
    sys.exit(1)


def get_process_info(proc):
    """Extract relevant information from a process."""
    try:
        return {
            "pid": proc.pid,
            "name": proc.name(),
            "ppid": proc.ppid(),
            "status": proc.status(),
            "username": proc.username(),
            "cpu_percent": proc.cpu_percent(interval=0),
            "memory_percent": proc.memory_percent(),
            "create_time": proc.create_time(),
        }
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return None


def build_process_tree(all_processes):
    """Build a tree structure from process list."""
    children_map = defaultdict(list)
    process_dict = {}

    for proc_info in all_processes:
        if proc_info is None:
            continue
        pid = proc_info["pid"]
        ppid = proc_info["ppid"]
        process_dict[pid] = proc_info
        children_map[ppid].append(pid)

    return process_dict, children_map


def create_process_label(proc_info, show_details=False):
    """Create a formatted label for a process node."""
    name = proc_info["name"]
    pid = proc_info["pid"]
    cpu = proc_info["cpu_percent"]
    mem = proc_info["memory_percent"]
    status = proc_info["status"]

    status_colors = {
        "running": "green",
        "sleeping": "blue",
        "idle": "white",
        "stopped": "yellow",
        "zombie": "red",
        "dead": "red",
    }

    color = status_colors.get(status.lower(), "white")
    label = Text()
    label.append(f"{name}", style=f"bold {color}")
    label.append(f" (PID: {pid})", style="dim")

    if show_details:
        label.append(f" [CPU: {cpu:.1f}% MEM: {mem:.1f}%]", style="dim italic")

    return label


def build_rich_tree(pid, process_dict, children_map, depth=0, show_details=False):
    """Recursively build a Rich Tree from process data."""
    if pid not in process_dict:
        return None

    proc_info = process_dict[pid]
    label = create_process_label(proc_info, show_details)
    tree = Tree(label)

    child_pids = sorted(children_map.get(pid, []))
    for child_pid in child_pids:
        child_tree = build_rich_tree(
            child_pid, process_dict, children_map, depth + 1, show_details
        )
        if child_tree:
            tree.add(child_tree)

    return tree


def get_root_processes(process_dict, children_map):
    """Find root processes (those with no parent or parent not in list)."""
    roots = []
    for pid in process_dict:
        ppid = process_dict[pid]["ppid"]
        if ppid not in process_dict or ppid == pid:
            roots.append(pid)
    return sorted(roots)


def generate_tree_display(process_dict, children_map, show_details=False):
    """Generate the full process tree display."""
    console = Console()
    main_tree = Tree("🖥️  Process Tree", style="bold magenta")

    root_pids = get_root_processes(process_dict, children_map)

    for root_pid in root_pids:
        subtree = build_rich_tree(
            root_pid, process_dict, children_map, 0, show_details
        )
        if subtree:
            main_tree.add(subtree)

    return main_tree


def get_summary_stats(process_dict):
    """Calculate summary statistics."""
    total = len(process_dict)
    running = sum(1 for p in process_dict.values() if p["status"] == "running")
    sleeping = sum(1 for p in process_dict.values() if p["status"] == "sleeping")
    zombie = sum(1 for p in process_dict.values() if p["status"] == "zombie")

    total_cpu = sum(p["cpu_percent"] for p in process_dict.values())
    total_mem = sum(p["memory_percent"] for p in process_dict.values())

    return {
        "total": total,
        "running": running,
        "sleeping": sleeping,
        "zombie": zombie,
        "cpu": total_cpu,
        "memory": total_mem,
    }


def create_summary_panel(stats):
    """Create a summary panel with statistics."""
    summary_text = Text()
    summary_text.append(f"Total: {stats['total']}  ", style="bold cyan")
    summary_text.append(f"Running: {stats['running']}  ", style="green")
    summary_text.append(f"Sleeping: {stats['sleeping']}  ", style="blue")
    summary_text.append(f"Zombie: {stats['zombie']}  ", style="red")
    summary_text.append(f"CPU: {stats['cpu']:.1f}%  ", style="yellow")
    summary_text.append(f"Memory: {stats['memory']:.1f}%", style="magenta")

    return Panel(
        summary_text,
        title="📊 Process Summary",
        border_style="bright_black",
    )


def refresh_processes():
    """Refresh and return current process information."""
    processes = []
    for proc in psutil.process_iter():
        info = get_process_info(proc)
        if info:
            processes.append(info)
    return processes


def run_live_view(interval, show_details, filter_name=None):
    """Run the live updating process tree view."""
    console = Console()

    with Live(console=console, refresh_per_second=1, screen=True) as live:
        while True:
            try:
                all_procs = refresh_processes()

                if filter_name:
                    all_procs = [
                        p for p in all_procs if filter_name.lower() in p["name"].lower()
                    ]

                if not all_procs:
                    empty_tree = Tree("⚠️  No processes found", style="yellow")
                    live.update(empty_tree)
                    time.sleep(interval)
                    continue

                process_dict, children_map = build_process_tree(all_procs)
                stats = get_summary_stats(process_dict)

                main_tree = generate_tree_display(
                    process_dict, children_map, show_details
                )

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                summary_panel = create_summary_panel(stats)

                from rich.layout import Layout
                layout = Layout()
                layout.split_column(
                    Layout(summary_panel, size=3),
                    Layout(main_tree, name="tree"),
                )

                live.update(layout)
                time.sleep(interval)

            except KeyboardInterrupt:
                break
            except Exception as e:
                error_tree = Tree(f"⚠️  Error: {e}", style="red")
                live.update(error_tree)
                time.sleep(interval)


def run_static_view(show_details, filter_name=None):
    """Run a static (non-updating) process tree view."""
    console = Console()

    all_procs = refresh_processes()

    if filter_name:
        all_procs = [
            p for p in all_procs if filter_name.lower() in p["name"].lower()
        ]

    if not all_procs:
        console.print("[yellow]⚠️  No processes found[/yellow]")
        return

    process_dict, children_map = build_process_tree(all_procs)
    stats = get_summary_stats(process_dict)

    console.print(create_summary_panel(stats))
    console.print()

    main_tree = generate_tree_display(process_dict, children_map, show_details)
    console.print(main_tree)


def run_list_view(filter_name=None):
    """Run a simple list view of processes."""
    console = Console()

    all_procs = refresh_processes()

    if filter_name:
        all_procs = [
            p for p in all_procs if filter_name.lower() in p["name"].lower()
        ]

    if not all_procs:
        console.print("[yellow]⚠️  No processes found[/yellow]")
        return

    process_dict, children_map = build_process_tree(all_procs)

    console.print("[bold cyan]PID    PPID   NAME{'':<25} STATUS{'':<10} CPU{'':<8} MEM[/bold cyan]")
    console.print("─" * 80)

    for pid in sorted(process_dict.keys()):
        proc = process_dict[pid]
        name = proc["name"][:30]
        status = proc["status"][:10]
        console.print(
            f"{proc['pid']:<7}{proc['ppid']:<7}{name:<33}{status:<13}"
            f"{proc['cpu_percent']:<10.1f}{proc['memory_percent']:.1f}"
        )


def generate_plain_tree(pid, process_dict, children_map, prefix="", is_last=True, show_details=False):
    """Generate plain text tree representation."""
    lines = []

    if pid not in process_dict:
        return lines

    proc_info = process_dict[pid]
    name = proc_info["name"]
    pid_val = proc_info["pid"]
    status = proc_info["status"]

    connector = "└── " if is_last else "├── "
    label = f"{name} (PID: {pid_val}, Status: {status})"

    if show_details:
        cpu = proc_info["cpu_percent"]
        mem = proc_info["memory_percent"]
        label = f"{name} (PID: {pid_val}, Status: {status}, CPU: {cpu:.1f}%, MEM: {mem:.1f}%)"

    lines.append(f"{prefix}{connector}{label}")

    child_pids = sorted(children_map.get(pid, []))
    child_prefix = prefix + ("    " if is_last else "│   ")

    for i, child_pid in enumerate(child_pids):
        is_last_child = (i == len(child_pids) - 1)
        child_lines = generate_plain_tree(
            child_pid, process_dict, children_map, child_prefix, is_last_child, show_details
        )
        lines.extend(child_lines)

    return lines


def export_tree_to_file(filepath, process_dict, children_map, show_details=False, filter_name=None):
    """Export the process tree to a text file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = []
    lines.append("=" * 60)
    lines.append("Process Tree Export")
    lines.append(f"Generated: {timestamp}")
    if filter_name:
        lines.append(f"Filter: {filter_name}")
    lines.append("=" * 60)
    lines.append("")

    stats = get_summary_stats(process_dict)
    lines.append(f"Total Processes: {stats['total']}")
    lines.append(f"Running: {stats['running']}")
    lines.append(f"Sleeping: {stats['sleeping']}")
    lines.append(f"Zombie: {stats['zombie']}")
    lines.append(f"Total CPU: {stats['cpu']:.1f}%")
    lines.append(f"Total Memory: {stats['memory']:.1f}%")
    lines.append("")
    lines.append("-" * 60)
    lines.append("Process Tree:")
    lines.append("-" * 60)

    root_pids = get_root_processes(process_dict, children_map)

    for i, root_pid in enumerate(root_pids):
        is_last = (i == len(root_pids) - 1)
        tree_lines = generate_plain_tree(
            root_pid, process_dict, children_map, "", is_last, show_details
        )
        lines.extend(tree_lines)

    lines.append("")
    lines.append("=" * 60)

    content = "\n".join(lines)

    with open(filepath, "w") as f:
        f.write(content)

    return filepath


def main():
    parser = argparse.ArgumentParser(
        description="Visualize process trees in real time",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                     # Live tree view
  %(prog)s --static            # Static snapshot
  %(prog)s --list              # Simple list format
  %(prog)s -i 2                # Update every 2 seconds
  %(prog)s --details           # Show CPU/Memory details
  %(prog)s --filter python     # Filter by process name
  %(prog)s --export tree.txt   # Export tree to file
        """,
    )

    parser.add_argument(
        "-i", "--interval",
        type=float,
        default=1.0,
        help="Update interval in seconds (default: 1.0)",
    )

    parser.add_argument(
        "--static",
        action="store_true",
        help="Show static snapshot instead of live view",
    )

    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_mode",
        help="Show simple list instead of tree",
    )

    parser.add_argument(
        "--details",
        action="store_true",
        help="Show CPU and memory details for each process",
    )

    parser.add_argument(
        "--filter",
        type=str,
        dest="filter_name",
        help="Filter processes by name substring",
    )

    parser.add_argument(
        "--export",
        type=str,
        dest="export_file",
        metavar="FILE",
        help="Export tree to a text file instead of displaying",
    )

    args = parser.parse_args()

    if args.export_file:
        all_procs = refresh_processes()

        if args.filter_name:
            all_procs = [
                p for p in all_procs if args.filter_name.lower() in p["name"].lower()
            ]

        if not all_procs:
            console = Console()
            console.print("[yellow]⚠️  No processes found to export[/yellow]")
            sys.exit(1)

        process_dict, children_map = build_process_tree(all_procs)
        export_tree_to_file(
            args.export_file, process_dict, children_map, args.details, args.filter_name
        )
        console = Console()
        console.print(f"[green]✓ Tree exported to {args.export_file}[/green]")
    elif args.list_mode:
        run_list_view(args.filter_name)
    elif args.static:
        run_static_view(args.details, args.filter_name)
    else:
        run_live_view(args.interval, args.details, args.filter_name)


if __name__ == "__main__":
    main()
