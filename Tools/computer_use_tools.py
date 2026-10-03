"""Local desktop implementation for OpenAI's Computer Use tool.

The OpenAI API decides which UI action to perform; this module executes that
single action with PyAutoGUI and returns a fresh PNG screenshot to the API.
Keep a human in the loop for logins, purchases, destructive actions, and every
API safety check.

Dependencies: ``pip install pyautogui pillow pyperclip``
"""

from __future__ import annotations

import base64
import io
import math
import time
from collections.abc import Callable, Iterable, Mapping
from typing import Any

try:
    import pyautogui
except ImportError as exc:  # Give a useful error without hiding the dependency.
    raise ImportError(
        "Computer Use requires PyAutoGUI and Pillow. Install them with "
        "`python -m pip install pyautogui pillow`."
    ) from exc


pyautogui.FAILSAFE = True  # Moving the pointer to the upper-left aborts actions.
pyautogui.PAUSE = 0.05

DEFAULT_MODEL = "gpt-5.6-luna"
_KEY_ALIASES = {
    "ALT": "alt",
    "ARROWDOWN": "down",
    "ARROWLEFT": "left",
    "ARROWRIGHT": "right",
    "ARROWUP": "up",
    "BACKSPACE": "backspace",
    "CMD": "command",
    "COMMAND": "command",
    "CTRL": "ctrl",
    "CONTROL": "ctrl",
    "DEL": "delete",
    "DELETE": "delete",
    "END": "end",
    "ENTER": "enter",
    "ESC": "esc",
    "ESCAPE": "esc",
    "HOME": "home",
    "META": "win",
    "OPTION": "alt",
    "PAGEDOWN": "pagedown",
    "PAGEUP": "pageup",
    "RETURN": "enter",
    "SHIFT": "shift",
    "SPACE": "space",
    "SUPER": "win",
    "TAB": "tab",
    "WIN": "win",
}


class SafetyCheckRequired(RuntimeError):
    """Raised when the API asks for confirmation and none was supplied."""

    def __init__(self, checks: list[dict[str, Any]]) -> None:
        self.checks = checks
        descriptions = "; ".join(
            str(check.get("message") or check.get("code") or check) for check in checks
        )
        super().__init__(f"Computer Use safety confirmation required: {descriptions}")


def _value(value: Any, name: str, default: Any = None) -> Any:
    """Read a field from either an SDK model or a plain mapping."""
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "model_dump"):
        return value.model_dump(exclude_none=True)
    if hasattr(value, "dict"):
        return value.dict(exclude_none=True)
    return {
        name: field
        for name in dir(value)
        if not name.startswith("_")
        and not callable(field := getattr(value, name, None))
    }


def display_size() -> tuple[int, int]:
    """Return the primary display size in physical screenshot coordinates."""
    size = pyautogui.size()
    return int(size.width), int(size.height)


def computer_tool(
    *,
    tool_type: str = "computer",
    environment: str = "windows",
    width: int | None = None,
    height: int | None = None,
) -> dict[str, Any]:
    """Build the native Computer Use declaration for ``responses.create``.

    ``computer_use_preview`` is the preview API declaration. Newer API/model
    combinations may use ``tool_type='computer'``, which needs no dimensions.
    The declared dimensions must match screenshots and action coordinates.
    """
    if tool_type == "computer":
        return {"type": "computer"}
    if tool_type != "computer_use_preview":
        raise ValueError("tool_type must be 'computer_use_preview' or 'computer'")
    screen_width, screen_height = display_size()
    return {
        "type": tool_type,
        "display_width": int(width or screen_width),
        "display_height": int(height or screen_height),
        "environment": environment,
    }


def take_screenshot() -> bytes:
    """Capture the primary display and return PNG bytes."""
    image = pyautogui.screenshot()
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def screenshot_base64() -> str:
    """Capture the display and return an unprefixed base64 PNG string."""
    return base64.b64encode(take_screenshot()).decode("ascii")


def screenshot_data_url() -> str:
    """Capture the display in the image URL format expected by OpenAI."""
    return "data:image/png;base64," + screenshot_base64()


def _coordinate(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite number")
    if not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    return int(round(value))


def _point(action: Any) -> tuple[int, int]:
    x = _coordinate(_value(action, "x"), "x")
    y = _coordinate(_value(action, "y"), "y")
    width, height = display_size()
    if not (0 <= x < width and 0 <= y < height):
        raise ValueError(
            f"coordinate ({x}, {y}) is outside the {width}x{height} display"
        )
    return x, y


def _button(action: Any) -> str:
    button = str(_value(action, "button", "left")).lower()
    if button not in {"left", "middle", "right"}:
        raise ValueError(f"unsupported mouse button: {button!r}")
    return button


def _keys(keys: str | Iterable[str]) -> list[str]:
    if isinstance(keys, str):
        keys = [keys]
    normalized = []
    for key in keys:
        text = str(key)
        normalized.append(_KEY_ALIASES.get(text.upper(), text.lower()))
    if not normalized:
        raise ValueError("keypress requires at least one key")
    return normalized


def _type_text(text: str) -> None:
    """Type Unicode text, using the clipboard only when PyAutoGUI cannot."""
    try:
        text.encode("ascii")
    except UnicodeEncodeError:
        try:
            import pyperclip
        except ImportError as exc:
            raise RuntimeError("Unicode typing requires pyperclip") from exc
        previous = pyperclip.paste()
        try:
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
        finally:
            # Give the target app time to consume the clipboard before restoring it.
            time.sleep(0.05)
            pyperclip.copy(previous)
    else:
        pyautogui.write(text, interval=0.001)


def execute_action(action: Any) -> None:
    """Execute one action from an OpenAI ``computer_call``.

    Supported actions are click, double_click, move, scroll, keypress, type,
    drag, wait, and screenshot. A screenshot action itself is a no-op because
    callers capture a fresh screenshot after every action.
    """
    action_type = str(_value(action, "type", "")).lower()

    if action_type == "click":
        pyautogui.click(*_point(action), button=_button(action))
    elif action_type == "double_click":
        pyautogui.doubleClick(*_point(action), button=_button(action), interval=0.1)
    elif action_type in {"move", "move_to"}:
        pyautogui.moveTo(*_point(action), duration=0.1)
    elif action_type == "scroll":
        pyautogui.moveTo(*_point(action), duration=0.05)
        scroll_x = _coordinate(_value(action, "scroll_x", 0), "scroll_x")
        scroll_y = _coordinate(_value(action, "scroll_y", 0), "scroll_y")
        # The API uses pixels, positive toward right/down. PyAutoGUI uses
        # wheel clicks and positive vertical values toward up.
        if scroll_x:
            pyautogui.hscroll(int(round(scroll_x / 100)) or (1 if scroll_x > 0 else -1))
        if scroll_y:
            pyautogui.scroll(int(round(-scroll_y / 100)) or (-1 if scroll_y > 0 else 1))
    elif action_type in {"keypress", "key_press"}:
        keys = _keys(_value(action, "keys", []))
        if len(keys) == 1:
            pyautogui.press(keys[0])
        else:
            pyautogui.hotkey(*keys)
    elif action_type in {"type", "type_text"}:
        _type_text(str(_value(action, "text", "")))
    elif action_type == "drag":
        path = _value(action, "path", [])
        points = [_point(point) for point in path]
        if not points:
            raise ValueError("drag requires a non-empty path")
        pyautogui.moveTo(*points[0], duration=0.05)
        pyautogui.mouseDown(button=_button(action))
        try:
            for point in points[1:]:
                pyautogui.moveTo(*point, duration=0.1)
        finally:
            pyautogui.mouseUp(button=_button(action))
    elif action_type == "wait":
        seconds = _value(action, "seconds", 2.0)
        seconds = float(seconds)
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError("wait seconds must be a non-negative finite number")
        time.sleep(min(seconds, 30.0))
    elif action_type == "screenshot":
        return
    else:
        raise ValueError(f"unsupported computer action: {action_type!r}")


def computer_call_output(
    call_id: str,
    *,
    acknowledged_safety_checks: Iterable[Any] = (),
) -> dict[str, Any]:
    """Create a Computer Use output containing a fresh desktop screenshot."""
    result: dict[str, Any] = {
        "type": "computer_call_output",
        "call_id": call_id,
        "output": {
            "type": "computer_screenshot",
            "image_url": screenshot_data_url(),
            "detail": "original",
        },
    }
    checks = [_as_dict(check) for check in acknowledged_safety_checks]
    if checks:
        result["acknowledged_safety_checks"] = checks
    return result


def handle_computer_call(
    call: Any,
    *,
    confirm_safety: Callable[[list[dict[str, Any]]], bool] | None = None,
) -> dict[str, Any]:
    """Confirm checks, execute a call, and return its screenshot output.

    Safety checks are never accepted automatically. Supply a callback that
    displays the checks to a human and returns True only after confirmation.
    """
    pending = [
        _as_dict(check) for check in (_value(call, "pending_safety_checks", []) or [])
    ]
    if pending and (confirm_safety is None or not confirm_safety(pending)):
        raise SafetyCheckRequired(pending)

    call_id = _value(call, "call_id")
    if not isinstance(call_id, str) or not call_id:
        raise ValueError("computer call has no call_id")
    actions = _value(call, "actions")
    if actions is None:
        action = _value(call, "action")
        if action is None:
            raise ValueError("computer call has no actions")
        actions = [action]
    for action in actions:
        print("Computer action:", _as_dict(action))
        execute_action(action)
    return computer_call_output(
        call_id, acknowledged_safety_checks=pending
    )


def _computer_calls(response: Any) -> list[Any]:
    return [
        item
        for item in (_value(response, "output", []) or [])
        if _value(item, "type") == "computer_call"
    ]


def run_computer_agent(
    client: Any,
    task: str,
    *,
    model: str = DEFAULT_MODEL,
    max_steps: int = 30,
    confirm_safety: Callable[[list[dict[str, Any]]], bool] | None = None,
    tool: Mapping[str, Any] | None = None,
    instructions: str | None = None,
    previous_response_id: str | None = None,
    reasoning_effort: str = "medium",
    on_response: Callable[[Any, float], None] | None = None,
) -> Any:
    """Run the Responses API Computer Use loop and return the final response.

    ``client`` is an ``openai.OpenAI`` instance. The caller remains responsible
    for sandboxing the desktop and for deciding whether safety checks may be
    acknowledged.
    """
    if not task.strip():
        raise ValueError("task must not be empty")
    if max_steps < 1:
        raise ValueError("max_steps must be at least 1")

    kwargs: dict[str, Any] = {
        "model": model,
        "tools": [dict(tool) if tool is not None else computer_tool()],
        "truncation": "auto",
        "reasoning": {"effort": reasoning_effort},
    }
    if instructions:
        kwargs["instructions"] = instructions
    def request(input_items, response_id):
        start = time.perf_counter()
        response = client.responses.create(
            **kwargs, input=input_items, previous_response_id=response_id,
        )
        if on_response is not None:
            on_response(response, time.perf_counter() - start)
        if _value(response, "status") != "completed":
            raise RuntimeError(f"Response stopped: {_value(response, 'status')}")
        return response

    response = request([{
        "role": "user",
        "content": [
            {"type": "input_text", "text": task},
            {"type": "input_image", "image_url": screenshot_data_url(),
             "detail": "original"},
        ],
    }], previous_response_id)

    for _ in range(max_steps):
        calls = _computer_calls(response)
        if not calls:
            return response
        outputs = [
            handle_computer_call(call, confirm_safety=confirm_safety) for call in calls
        ]
        response = request(outputs, _value(response, "id"))
    if not _computer_calls(response):
        return response
    raise RuntimeError(f"Computer Use exceeded the {max_steps}-step limit")


# Current tool declaration requires no display discovery at import time.
tools = [computer_tool()]

# Convenient compatibility aliases.
screenshot = take_screenshot
handle_computer_action = execute_action

__all__ = [
    "DEFAULT_MODEL",
    "SafetyCheckRequired",
    "computer_call_output",
    "computer_tool",
    "display_size",
    "execute_action",
    "handle_computer_action",
    "handle_computer_call",
    "run_computer_agent",
    "screenshot",
    "screenshot_base64",
    "screenshot_data_url",
    "take_screenshot",
    "tools",
]
