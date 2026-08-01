"""Profile fields owned by the `diagram` skill.

Picked up automatically by `{{cmd:scaffold:profile}}` (see `_sibling_fields` in
`scaffold/profile.py`) when both skills are installed, and read straight from the saved
profile by `render.py` when they are not. Same 6-tuple shape as the scaffold fields:

    (key, group, label, example, used_in, source)

Every field is optional. Nothing here is required to build a diagram — each value only
removes a question the skill would otherwise have to ask, and every one can be overridden
per run by a CLI flag or an environment variable.
"""

FIELDS = [
    (
        "diagrams_dir",
        "Diagrams",
        "Where diagrams are written (design workspace, never a deployed code repo)",
        "$HOME/design/system-diagrams",
        "{{cmd:diagram:build}} output folder",
        "you choose (a design/docs workspace path; ~ and $VARS expand)",
    ),
    (
        "brand_guidelines",
        "Diagrams",
        "Path to the brand/style guide diagrams must follow (palette, typography)",
        "$HOME/design/brand-guidelines.md",
        "{{cmd:diagram:build}} — loaded before drawing so output matches the brand",
        "your brand/design system owner (blank = use the active project's style guide)",
    ),
    (
        "drawio_bin",
        "Diagrams",
        "draw.io desktop binary used to export PNGs for self-review",
        "/Applications/draw.io.app/Contents/MacOS/draw.io",
        "{{cmd:diagram:build}} + {{cmd:diagram:review}} rendering step",
        "your local draw.io install (blank = auto-detected from PATH/usual locations)",
    ),
]
