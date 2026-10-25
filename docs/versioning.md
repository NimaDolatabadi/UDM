# Versioning Policy

This project uses Semantic Versioning in the form `MAJOR.MINOR.PATCH`.
`VERSION` at the repository root is the canonical current version.

## Version Bumps

### Major

Increment `MAJOR` and reset `MINOR` and `PATCH` to zero when a change is not
backward compatible. Examples include removing supported behavior, changing a
public interface incompatibly, or requiring users to migrate existing data or
configuration.

Example: `1.4.2` becomes `2.0.0`.

### Minor

Increment `MINOR` and reset `PATCH` to zero for backward-compatible functionality.
Examples include a new user-facing feature, a new optional public interface, or a
substantial new capability.

Example: `1.4.2` becomes `1.5.0`.

### Patch

Increment `PATCH` for backward-compatible corrections and maintenance. Examples
include bug fixes, refactoring without behavior changes, tests, documentation,
dependency maintenance, and build or tooling adjustments.

Example: `1.4.2` becomes `1.4.3`.

## Pre-1.0 Development

Versions below `1.0.0` indicate that the public interface may still evolve.
During this phase:

- Use a minor bump for a breaking change or a new feature.
- Use a patch bump for a fix, documentation, tests, refactoring, or maintenance.
- Release `1.0.0` when the public behavior and interfaces are considered stable.

## Change Workflow

1. Read the current value in `VERSION`.
2. Review the whole change set and identify its highest-impact change.
3. Calculate one new version using the rules above.
4. Update `VERSION`.
5. Add a matching entry near the top of `PROJECT_LOG.md`.
6. Use the new version in the pull request title or description when practical.
7. After merge, a release tag may be created as `vMAJOR.MINOR.PATCH`.

Multiple commits that form one coherent change set use one version bump. If a
change set contains different categories, use the highest applicable category:
major before minor, and minor before patch.
