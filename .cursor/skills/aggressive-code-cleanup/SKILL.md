---
name: aggressive-code-cleanup
description: Detects dead code, removes unused and legacy paths, finds likely bugs, and simplifies implementations without preserving backward compatibility. Use when cleaning up, refactoring, modernizing, reviewing, or editing code where deletion and simplification are preferred over compatibility layers, deprecation shims, or legacy support.
---

# Aggressive Code Cleanup

## Goal

Make the codebase smaller, clearer, and safer.

Default stance:
- Delete dead code instead of commenting it out.
- Remove legacy paths instead of preserving them.
- Prefer one canonical implementation over parallel old/new flows.
- Do not add backward-compatibility shims, aliases, adapters, or deprecation wrappers unless the user explicitly asks for them.

## When This Skill Applies

Apply this skill when the user asks to:
- clean up code
- remove dead code
- refactor or modernize
- review for bugs or improvements
- simplify logic
- remove legacy or deprecated paths

Also apply it during ordinary code edits when unused code, compatibility glue, duplicated flows, or stale abstractions are discovered nearby.

## What To Look For

Prioritize finding and removing:
- unused functions, classes, methods, modules, constants, imports, exports, fixtures, and helpers
- unreachable branches, impossible conditions, duplicate guards, and stale feature flags
- compatibility adapters, deprecated aliases, fallback code paths, shadow DTOs, and migration leftovers
- duplicate implementations where one path can replace the others
- dead configuration, unused environment variables, and no-op settings
- defensive code that hides bad states instead of fixing them

Also look for likely bugs and cleanup opportunities:
- swallowed exceptions
- incorrect null or truthiness handling
- inconsistent return types
- duplicated validation or parsing logic
- copy-paste branching that can drift
- stale comments, TODOs, and misleading names

## Operating Rules

1. Assume dead code is a defect.
2. Prefer removal over deprecation.
3. Prefer breaking cleanup over preserving obsolete behavior.
4. Do not keep legacy code "just in case."
5. Do not add transitional compatibility code unless the user explicitly requests it.
6. If a public boundary may affect callers outside the repository and external usage cannot be verified, call out the breaking change clearly. Do not silently preserve legacy behavior.

## Cleanup Workflow

Use this sequence:

1. Map usage.
   - Search for references before deleting code.
   - Distinguish repo-local usage from speculative external usage.

2. Delete aggressively.
   - Remove dead symbols, old branches, unused files, duplicate flows, and compatibility layers.
   - Remove callers and tests that only exist for deleted legacy behavior.

3. Simplify after deletion.
   - Collapse conditionals.
   - Inline single-use wrappers when it improves clarity.
   - Merge duplicate logic into one implementation.
   - Rename misleading symbols if cleanup makes names inaccurate.

4. Fix bugs exposed by simplification.
   - Tighten types and return values.
   - Replace fallback behavior with explicit handling.
   - Remove hidden failure modes and ambiguous defaults.

5. Validate.
   - Run focused tests or checks when practical.
   - Check lints on edited files.
   - Ensure imports, exports, routes, schemas, and references still line up.

## Decision Heuristics

Use these defaults:

- If code has no references in the repo and is not an obvious entrypoint, delete it.
- If two paths do the same job, keep the simpler one and remove the other.
- If a fallback exists only for an old data shape or old API, remove the fallback and update the canonical path.
- If a parameter, field, or config no longer changes behavior, remove it.
- If a wrapper only forwards arguments without adding clarity or policy, inline it.
- If a compatibility alias exists, delete the alias and update call sites.

## Do Not Do

Avoid these patterns unless explicitly requested:
- deprecated wrappers
- temporary aliases
- dual read or dual write flows
- versioned code paths for old behavior
- "safe" no-op fallbacks that hide breakage
- commented-out code kept for reference

## Output Expectations

When using this skill, report results in this shape:

- Removed: dead code, legacy paths, duplicate logic, unused config, or obsolete tests
- Fixed: likely bugs or risky behavior uncovered during cleanup
- Breaking changes: any intentionally removed behavior, API shape, config, or compatibility path
- Validation: tests, lints, or targeted checks that were run

If you choose not to delete something because the impact is genuinely unclear, say exactly what evidence is missing.

## Review Standard

Judge success by these questions:
- Is the codebase smaller?
- Is there less branching and fewer special cases?
- Did we remove obsolete behavior instead of preserving it?
- Did we reduce bug surface area?
- Did we avoid introducing new compatibility debt?
