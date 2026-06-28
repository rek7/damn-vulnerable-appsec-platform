# Assessment fixture: Secret Scanning / symlink_traversal

This repo contains **no executable script**. It exercises how a naive secret
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
`sample-repos/` without reading the test process's own environment. The worker
retargets it when copying this sample into an ephemeral scan workdir.

Real behavior abused: file-based secret scanners (truffleHog-style walkers,
naive `grep -r`) follow symlinks by default and read whatever they target,
including paths that escape the repository root.

When secrets are found, the **worker** (not a script in this repo) emits the
`symlink_traversal` signal on the repo's behalf.
