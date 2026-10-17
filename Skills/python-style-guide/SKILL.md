---
name: python-style-guide
description: Review and correct Python style in a specified file, code snippet, or codebase using PEP 8 and concise PEP 257 documentation. Fix spacing, naming conventions, and long lines while preserving behavior and identifier meanings.
---

# Python Style Guide

Review the requested Python code and apply style corrections. For an explicitly
review-only request, report findings without editing. Work only within the user's
specified scope; do not perform unrelated refactoring or bug fixes.

## Review and corrections

Read the target code and applicable project instructions or style configuration.
Follow [PEP 8](https://peps.python.org/pep-0008/) and
[PEP 257](https://peps.python.org/pep-0257/), respecting explicit user requirements
and established project conventions where they differ.

- Use four spaces for indentation. Correct operator, comma, delimiter, and
  comment spacing; remove trailing whitespace and unnecessary blank lines.
- Use two blank lines around top-level definitions and one between methods.
  Keep blank lines within functions purposeful.
- Separate imports and group standard-library, third-party, and local imports.
  Preserve import ordering or placement when it affects initialization or avoids
  circular imports. Do not remove imports solely because they appear unused.
- Check every target file for long lines. Default to 79 characters for code and
  72 for comments and docstrings unless the project specifies another limit.
  Prefer wrapping inside parentheses, brackets, or braces. Preserve literal
  string values, expression grouping, and evaluation order when wrapping.
- Normalize functions, methods, parameters, and variables to snake_case, classes
  to CapWords, and actual constants to UPPER_SNAKE_CASE. Preserve meaningful
  words and abbreviations; change the naming convention rather than inventing
  a new meaning. Do not classify every module-level variable as a constant.

## Preserve meaning and compatibility

Trace references before renaming and update them consistently within scope.
Respect lexical scope and avoid collisions, shadowing changes, or blind text
replacement. Preserve leading underscores, special methods, and identifiers
required by frameworks or external interfaces.

Treat public names, keyword argument names, imported symbols, serialized keys,
and names accessed through strings or reflection as compatibility-sensitive.
If a rename requires changes outside the requested scope or its compatibility
cannot be established, leave it unchanged and explain the remaining style issue.
Do not silently add aliases or alter data keys to compensate.

Preserve function signatures apart from safe naming changes, control flow,
return values, side effects, and execution order. Flag behavior defects separately
without repairing them as part of this style pass.

## Brief documentation

Add or improve docstrings for modules, classes, and functions that need them.
Limit each added or rewritten docstring or comment to one or two concise
sentences. State purpose and, when useful, a non-obvious return value or side
effect. Use triple double quotes for docstrings and an imperative opening for
function summaries. Avoid restating signatures, obvious operations, long usage
examples, or boilerplate parameter sections. Preserve essential contracts and
existing detailed documentation unless shortening it is requested.

## Verification and handoff

Inspect the diff for unintended changes. Check syntax without executing target
modules, and use existing focused checks when renames or import changes warrant
behavioral verification. Use configured formatters or linters when available;
review their changes and do not let them expand the scope or override the
requested line limits. Do not install tools or introduce new configuration
solely for this pass.

Report the corrections, checks performed, and any unresolved compatibility or
line-length issues briefly. Do not claim behavior preservation was proven by
style or syntax checks alone.
