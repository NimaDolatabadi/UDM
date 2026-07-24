# Code Commenting Standard

Comments and docstrings explain contracts, intent, constraints, and decisions
that the code cannot express clearly by itself. They are maintained as part of
the implementation and must remain accurate.

## Module Docstrings

Every maintained source module must begin with a concise docstring describing its
single responsibility.

```python
"""Configuration persistence and download category routing."""
```

Do not use a module docstring to repeat the filename or list implementation
details that are evident from the module contents.

## Public API Docstrings

Document public classes, functions, and methods when a caller needs information
that is not obvious from the name and signature. Explain relevant:

- inputs and accepted formats;
- returned values;
- state changes and other side effects;
- emitted signals or raised exceptions;
- lifecycle requirements and important invariants.

Keep short contracts to a single sentence:

```python
def get_category_path(self, filename):
    """Return and create the configured download directory for a filename."""
```

Use a longer docstring only when the contract genuinely requires more detail.
Private helpers do not require docstrings when their names and implementation are
clear.

## Inline Comments

Use an inline comment immediately before non-obvious code to explain why the
approach is necessary:

```python
# Delete from the bottom upward so earlier row indexes remain valid.
for row in reversed(selected_rows):
    table.removeRow(row)
```

Appropriate subjects include:

- compatibility workarounds;
- platform-specific behavior;
- concurrency and Qt thread constraints;
- byte-range or scheduling invariants;
- preservation of data not edited by a component;
- decisions that appear simpler but would introduce a defect.

Do not add comments that narrate syntax:

```python
# Bad: Increment the counter.
counter += 1
```

Prefer clearer names and smaller functions when code requires many explanatory
comments.

## Maintenance Markers

Use markers sparingly and include enough context to make them actionable:

- `TODO:` identifies scoped future work that is not required for correctness.
- `FIXME:` identifies known incorrect behavior that requires repair.
- `NOTE:` records a significant constraint that is easy to violate.

Include an issue reference when one exists:

```python
# TODO: Add torrent metadata loading after native backend selection. Issue #42.
```

Markers must not replace proper issue tracking or excuse broken behavior in a
completed change.

## Prohibited Commenting Practices

- Do not commit commented-out code. Git preserves previous implementations.
- Do not copy implementation details into comments that will quickly become
  stale.
- Do not add decorative comment banners or emojis.
- Do not place credentials, tokens, private URLs, or other secrets in comments.
- Do not use comments to suppress a warning without explaining why suppression
  is safe.

## Review Checklist

When changing code:

1. Add or update docstrings for changed public contracts.
2. Add rationale comments only where the decision is non-obvious.
3. Update or remove comments invalidated by the change.
4. Search for stale `TODO:`, `FIXME:`, and `NOTE:` markers in the affected area.
5. Confirm comments describe current behavior and do not merely repeat code.
