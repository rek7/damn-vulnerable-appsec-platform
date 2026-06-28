# DVAP evil-repo: Secret Scanning / symlink_traversal

This repo contains **no executable payload**. It abuses how a naive secret
scanner walks a repository: it `open()`s every file it finds **without resolving
symlinks first**. We plant a symlink named `leak` that points at
`/proc/self/environ` (outside the repo). When the scanner reads `leak`, it
actually reads the worker process's environment -- which holds the synthetic
secrets -- and flags them as "found in the repo".

Files:
- `config.txt`  -- benign cover content.
- `notes.md`    -- benign cover content.
- `leak`        -- symlink materialized by the worker as
  `/proc/self/environ` inside each sample scan workdir.

The checked-in `leak` symlink is inert so repository containment tests can walk
`evil-repos/` without reading the test process's own environment. The worker
retargets it when copying this sample into an ephemeral scan workdir.

Real behavior abused: file-based secret scanners (truffleHog-style walkers,
naive `grep -r`) follow symlinks by default and read whatever they target,
including paths that escape the repository root.

Mitigation (`resolve_symlinks`): the worker resolves `os.path.realpath` of each
candidate and skips any whose real path escapes the repo workdir root, so `leak`
is never read.

When secrets are found on the vulnerable path, the **worker** (not a payload in
this repo) emits the `symlink_traversal` beacon on the repo's behalf.
