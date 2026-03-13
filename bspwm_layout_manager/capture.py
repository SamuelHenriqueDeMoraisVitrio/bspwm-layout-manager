import subprocess
import json
import os
from pathlib import Path


SHELLS = {"bash", "sh", "zsh", "fish", "dash", "ksh", "tcsh", "csh"}


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip()


def get_window_pid(window_id: str) -> int | None:
    out = run(["xprop", "-id", window_id, "_NET_WM_PID"])
    # Output: _NET_WM_PID(CARDINAL) = 12345
    try:
        return int(out.split("=")[-1].strip())
    except (ValueError, IndexError):
        return None


def get_child_processes(pid: int) -> list[int]:
    """Returns direct child PIDs of the given pid."""
    children = []
    try:
        for entry in os.scandir("/proc"):
            if not entry.name.isdigit():
                continue
            try:
                status = Path(f"/proc/{entry.name}/status").read_text()
                ppid_line = next(l for l in status.splitlines() if l.startswith("PPid:"))
                ppid = int(ppid_line.split()[1])
                if ppid == pid:
                    children.append(int(entry.name))
            except (OSError, PermissionError, StopIteration, ValueError):
                continue
    except OSError:
        pass
    return children


def _get_process_name(pid: int) -> str:
    """Returns the base name of the process executable."""
    try:
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes()
        parts = cmdline.split(b"\x00")
        parts = [p for p in parts if p]
        if parts:
            return os.path.basename(parts[0].decode("utf-8", errors="replace"))
    except (OSError, PermissionError):
        pass
    return ""


def _find_shell(pid: int) -> str:
    """Finds the shell that is a direct child of the terminal (pid).
    Returns its full executable path, or empty string if not found."""
    for child_pid in get_child_processes(pid):
        name = _get_process_name(child_pid)
        if name in SHELLS:
            try:
                return os.readlink(f"/proc/{child_pid}/exe")
            except (OSError, PermissionError):
                return name
    return ""


def _find_real_process(pid: int) -> int:
    """Traverses child processes to find the first non-shell foreground process.
    Returns the original pid if no real process is found."""
    for child_pid in get_child_processes(pid):
        name = _get_process_name(child_pid)
        if not name:
            continue
        if name in SHELLS:
            found = _find_real_process(child_pid)
            if found != child_pid:
                return found
        else:
            return child_pid
    return pid


def get_process_info(pid: int) -> dict:
    """Returns working directory and command for a PID.

    If the PID belongs to a terminal, traverses child processes to find
    the first real (non-shell) foreground process and uses its cwd/command.
    """
    real_pid = _find_real_process(pid)
    shell = _find_shell(pid)

    try:
        cwd = os.readlink(f"/proc/{real_pid}/cwd")
    except (OSError, PermissionError):
        cwd = str(Path.home())

    try:
        cmdline = Path(f"/proc/{real_pid}/cmdline").read_bytes()
        # cmdline is null-byte separated
        parts = cmdline.split(b"\x00")
        parts = [p.decode("utf-8", errors="replace") for p in parts if p]
        command = " ".join(parts)
    except (OSError, PermissionError):
        command = ""

    return {"cwd": cwd, "command": command, "shell": shell}


def get_window_class(window_id: str) -> str:
    out = run(["xprop", "-id", window_id, "WM_CLASS"])
    # Output: WM_CLASS(STRING) = "alacritty", "Alacritty"
    try:
        parts = out.split("=")[-1].strip().replace('"', "").split(", ")
        return parts[-1] if parts else ""
    except IndexError:
        return ""


def parse_tree(node: dict, windows: list, floating_windows: list):
    """Recursively walks the bspwm tree and collects window nodes.
    Tiled windows go into `windows`, floating windows go into `floating_windows`.
    """
    if node is None:
        return

    client = node.get("client")
    if client:
        window_id = hex(node["id"])
        pid = get_window_pid(window_id)
        info = get_process_info(pid) if pid else {"cwd": str(Path.home()), "command": ""}

        if client.get("state") == "floating":
            floating_windows.append({
                "node_id": node["id"],
                "window_id": window_id,
                "class": client.get("className", ""),
                "instance": client.get("instanceName", ""),
                "cwd": info["cwd"],
                "command": info["command"],
                "shell": info.get("shell", ""),
                "pid": pid,
                "floatingRectangle": client.get("floatingRectangle", {}),
            })
            return

        windows.append({
            "node_id": node["id"],
            "window_id": window_id,
            "class": client.get("className", ""),
            "instance": client.get("instanceName", ""),
            "cwd": info["cwd"],
            "command": info["command"],
            "shell": info.get("shell", ""),
            "pid": pid,
            "rectangle": client.get("tiledRectangle", {}),
        })
        return

    parse_tree(node.get("firstChild"), windows, floating_windows)
    parse_tree(node.get("secondChild"), windows, floating_windows)


def capture_splits(node: dict) -> dict | None:
    """Recursively captures the split tree structure with ratios."""
    if node is None:
        return None

    client = node.get("client")
    if client:
        if client.get("state") == "floating":
            return None
        return {
            "type": "window",
            "class": client.get("className", ""),
            "instance": client.get("instanceName", ""),
            "node_id": node["id"],
        }

    first = capture_splits(node.get("firstChild"))
    second = capture_splits(node.get("secondChild"))

    # Skip branches where both children are empty
    if first is None and second is None:
        return None

    return {
        "type": "split",
        "split_type": node.get("splitType", "vertical"),
        "ratio": node.get("splitRatio", 0.5),
        "first": first,
        "second": second,
    }


def capture_current_desktop() -> dict:
    """Captures the full state of the current bspwm desktop."""
    raw = run(["bspc", "query", "-T", "-d"])
    tree = json.loads(raw)

    desktop_name = tree.get("name", "")
    desktop_id = tree.get("id")

    # Get current desktop index
    all_desktops = run(["bspc", "query", "-D", "--names"]).splitlines()
    desktop_index = all_desktops.index(desktop_name) + 1 if desktop_name in all_desktops else 1

    # Collect windows in order
    windows = []
    floating_windows = []
    parse_tree(tree.get("root"), windows, floating_windows)

    # Capture split structure
    splits = capture_splits(tree.get("root"))

    # Map node_id -> window info
    window_map = {w["node_id"]: w for w in windows}

    return {
        "desktop": desktop_index,
        "desktop_name": desktop_name,
        "gap": tree.get("windowGap", 10),
        "windows": windows,
        "floating_windows": floating_windows,
        "splits": splits,
        "window_map": window_map,
    }
