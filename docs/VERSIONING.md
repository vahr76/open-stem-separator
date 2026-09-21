# Versioning policy

OSS uses a practical pre-1.0 versioning policy while the project is still evolving.

The format is:

```text
0.MINOR.PATCH
```

During the `0.x.y` stage, version bumps mean:

## PATCH: `0.1.1` → `0.1.2`

Use a PATCH bump for quality-of-life improvements, fixes, documentation, packaging polish, tests, and compatibility changes that do not redefine the product's main capability.

Examples:

- `ytd open`, `ytd last`, `ytd config`.
- Better messages and clearer errors.
- README, release notes, legal notices, packaging docs.
- Bug fixes in cookie fallback, path handling, console encoding, thumbnails, filenames, metadata heuristics.
- Small packaging improvements for an existing package target.
- Manifest/checksum improvements.
- Test coverage improvements.
- History display improvements when history already exists.

## MINOR: `0.1.2` → `0.2.0`

Use a MINOR bump for new user-facing product functionality, a new flow, a new module, or a newly supported platform/package class.

Examples:

- Search inside `ytd`.
- Interactive result selector.
- Independent conversion command.
- `ytd update`.
- Duplicate detection with confirmation.
- Batch downloads or queue support.
- Formal playlist support.
- First manually validated Windows package.
- First macOS package.
- First stem-separation integration.
- Local web UI.
- Real project management beyond simple folders and metadata.

## MAJOR: `1.0.0`

Do not use `1.0.0` until the project has a stable user-facing product.

A future `1.0.0` should require, at minimum:

- documented and tested install flow;
- at least Linux and Windows validated on real machines;
- reliable core download workflow;
- clear copyright/usage guidance;
- stable config/history/project behavior;
- acceptable packaging and release process;
- a product scope that is no longer just exploratory.

## Current interpretation

`v0.1.1` is the first useful public pre-release with Linux and Windows assets.

QoL commands such as `ytd config`, `ytd last`, and `ytd open` should be released as `v0.1.2`, not folded back into `v0.1.1`, because the existing release is already published and coherent.
