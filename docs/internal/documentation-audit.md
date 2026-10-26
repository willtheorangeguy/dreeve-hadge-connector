# Documentation audit

The October 2026 documentation pass follows the local `docs-sweep` runbook and
the `willtheorangeguy/mkdocs` rollout and writing standard. The MkDocs rollout
supplies the final site shape where the two phases differ.

## Scope decisions

- Retain the existing root README's installation and operating guidance, as the
  MkDocs rollout explicitly requires. Add a documentation badge and repository
  guide link. The sweep's 120-line rewrite rule is superseded for this pass.
- Use `docs/index.md` as the landing page and `getting-started.md` as the single
  quickstart. Do not create a second index or duplicate quickstart page.
- Keep the canonical root `LICENSE` filename. The Dockerfile copies this file,
  and the site includes it by exact path. No licensing decision or runtime
  packaging change is part of the docs pass.
- Include the root changelog by reference. Link to account-wide health files.
- Use Issues for support. The standard Discussions creation URL returns 404
  because this repository does not have Discussions enabled.
- Document the CLI as the public interface. Describe consumed GitHub requests
  without presenting internal Python functions as a stable library API.
- Inherit shared configuration and use reusable workflows. Generated theme
  assets, the shared checkout, and build outputs remain ignored.
- Exclude this directory and the copied writing standard from the site.
- Push to the existing default branch for publication, following the user's
  explicit commit, push, and Pages enablement request.

## Source coverage

Reviewed the source modules, package metadata, all Compose definitions, the
Dockerfile, environment template, unit-test scenarios, integration harness
contract, release scripts, workflows, changelog, license, and root README.
Behavioral claims follow implementation first, then tests and workflows.

## Validation procedure

- Build with the shared toolchain using `mkdocs build --strict`.
- Run Markdown style checks with the shared rules, including the writing standard.
- Run the existing unit suite and Ruff.
- Run the sweep verifier with its README allowance adjusted to preserve the
  existing README. Its missing `quickstart.md` and `LICENSE.md` notices reflect
  the deliberate MkDocs and extensionless-license choices above.
- After committing, repeat the full strict build so revision dates come from
  real Git history rather than untracked-page fallback dates.
- Enable workflow-based Pages, push, inspect Actions, and verify the deployed URL.

No application-code changes or undocumented future feature commitments are
included in this pass. Current compatibility and input limits are documented
in the site's Limitations page.

## Revalidation on 2026-10-26

The repository already contains the completed 19-page documentation package
and shared MkDocs site. The sweep ledger records the original deployment in
commits `ea2e616` and `2f02758`. The scope and publication instructions above
describe that original pass.

Rechecked the local sweep runbook, MkDocs rollout, writing standard, current
source modules, tests, and workflows. GitHub metadata confirms the repository
is active, its default branch is `main`, and Pages uses workflow deployment
at `https://williamvdg.me/dreeve-hadge-connector/`. The account Pages CNAME
remains `williamvdg.me`.

Corrected the CI/CD guide's stale release-workflow filename to `publish.yml`.
Added the shared Markdown check and a behavior-to-documentation maintenance
table to the development guide. Preserve the root README and the existing
site structure under the MkDocs rollout's migration rules.

Validation passed: `mkdocs build --strict`, shared Markdown lint across 21
files with zero issues, `git diff --check`, and the sweep verifier with the
existing README allowance. The verifier's notices about `quickstart.md` and
`LICENSE.md` correspond to the documented filename choices above. The live
site returns HTTP 200; the latest remote Docs and Docs Lint runs succeeded.
The user subsequently authorized pulling and pushing these three documentation
edits and verifying the resulting workflow runs and live site.
