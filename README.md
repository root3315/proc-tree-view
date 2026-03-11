# proc-tree-view

CLI tool to visualize process trees in real time. Because sometimes you just need to see what the hell is running on your system.

## Why I Made This

`pstree` is great, but I wanted something prettier with live updates and actual resource usage. Plus I like trees. Process trees. You get it.

## Quick Start

```bash
pip install -r requirements.txt
python proc_tree_view.py
```

That's it. You'll see a live-updating tree of all processes with colors and stats.

## Usage

```
# Live view (default) - updates every second
python proc_tree_view.py

# Static snapshot
python proc_tree_view.py --static

# Simple list format
python proc_tree_view.py --list

# Slower updates (every 2 seconds)
python proc_tree_view.py -i 2

# Show CPU and memory per process
python proc_tree_view.py --details

# Filter by process name
python proc_tree_view.py --filter python
python proc_tree_view.py --filter node
```

## What You See

- **Green** = running processes
- **Blue** = sleeping processes  
- **Yellow** = stopped processes
- **Red** = zombie/dead processes (uh oh)

The summary bar shows total process count, breakdown by status, and aggregate CPU/memory usage.

## Dependencies

- `psutil` - for process info
- `rich` - for the pretty terminal output

Both are in `requirements.txt`.

## Notes

- Needs to run with enough permissions to see all processes (sudo for full visibility)
- Zombie processes will show up in red so you know something's wrong
- The tree structure follows parent-child relationships from `/proc`

## License

Do whatever you want with it.
