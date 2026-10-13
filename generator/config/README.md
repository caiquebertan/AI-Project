# Generator config

`generator.json` is the **single place** for the harness's tunable values; every script reads it through `generator/scripts/awarelib.py`, and `generator/WORKFLOW.md` (§2, §5.2, §6) cites it. Change a value here, never in a script.

| Key | Used by | Notes |
|---|---|---|
| `generate_model`, `generate_model_fallback` | `/generate`, `regen_check.py`, `render_prompt.py --generate` | Exact model ids, pinned at **P3** (now `TBD-at-P3`; real regen runs refuse to start) |
| `self_repair_max` | generator prompt | Bounded self-repair per `/generate` run (§5.2 `gen_self_repair`) |
| `apps.<app>` | all app-aware scripts | `dir`, `platform_spec`, `conventions`, `build`, `test` (build/test commands pinned at P3) |
| `limits.rev_opus_changed_lines` | `state.py model` | Reviewer runs on Opus above this many changed lines (§2) |
| `limits.snapshot_split_lines` | `snapshot_diff.py` | Above this, the snapshot is a file list + per-file patches (§6.4) |
| `limits.caps.*` | `state.py` | Counter caps from §5.2; exceeding one routes to G2 |
| `count_lines` | `count_lines.py`, `snapshot_diff.py` | Files excluded from `changed_lines` (§6.2) |
| `headers` | `check_headers.py`, generator prompt | Manifest name, GENERATED header text, which extensions need it |
| `trace` | `check_trace.py` | Traceability file, spec-id pattern, scope pattern; `coverage_apps`, `default_apps`, `file_apps` say which apps must cover a rule (by spec file name; an `[apps: a, b]` marker on a rule overrides) |
| `generate` | `render_prompt.py --generate` | Paths filled into `generator/prompts/generate.md`. `platform_shared` lists the platform inputs every app reads (hooks, snapshot schema). `spec_version_regex` captures the full version including a prerelease suffix (`0.1.0-draft`), which is what gets stamped in headers and the manifest; `draft_suffix_regex` decides `spec_is_draft`, which is passed to the prompt and makes `/generate` print a `WARNING ... is a draft` line on stderr. Drafts never block generation. |
| `regen` | `regen_check.py` | Generate command template (`{app}`, `{model}`), worktree and report dirs |
| `commits` | `lint_commits.py` | Author pattern and trailer rules from §8 |
| `prompt_lint` | `lint_prompts.py` | Feature-noun denylist for E-EVOL-1 (review at P0) |
| `preflight` | `preflight.py` | Probe timeout |
