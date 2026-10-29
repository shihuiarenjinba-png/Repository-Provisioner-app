# APP cohort binary dispatch gate (PRE_IDENTITY only)

Owner: 00-minute APP lane. Downstream consumer: 36-minute Windows/E2E lane.
The five product source/request pairs are pinned in `docs/APP_COHORT_ROTATION.json`.
This gate is **read-only**: no Windows install, Store registration, Identity CAS,
MSIX generation, security policy changes, merge, or publication.

## Two deliberately distinct results

`python -m tools.app_cohort_dispatch` prints the five current contract rows
with `binary_verified_count=0` and `downstream_binary_gate_pass=false`.
This is **not** a binary-ready job, even if `pre_identity_cloud_ready_count=5`.

To verify actual artifact bytes, first obtain the *current pinned* Actions ZIP
for each product, and create a local UTF-8 JSON mapping of all five slugs to
the corresponding local ZIP paths. No ZIP filename is guessed by the tool:

```json
{
  "offline-notes-canary": "/path/to/notes-current.zip",
  "focus-session-desk": "/path/to/focus-current.zip",
  "file-integrity-ledger": "/path/to/ledger-current.zip",
  "offline-text-diff-desk": "/path/to/text-diff-current.zip",
  "offline-image-inventory-desk": "/path/to/image-inventory-current.zip"
}
```

Run:

```sh
python -m tools.app_cohort_dispatch --require-binary --artifact-map /path/to/zip-map.json > /path/to/app-binary-handoff.json
```

Missing ZIPs, wrong slug set, wrong pinned ZIP hash, unexpected archive members,
bad PE/AMD64 header, EXE digest/size mismatch, stale source/request, unsafe
Identity CAS or MSIX claims cause a nonzero exit and **no successful handoff JSON**.
Do not consume a partial result. Treat the JSON map as local inputs only; never
trust unverified filenames, ZIP metadata, or a stale prior report.

A successful run prints `downstream_binary_gate_pass=true` and
`binary_verified_count=5` with per-product `binary_verification` proof.
The scope is `LOCAL_PINNED_ZIP_BYTES_NOT_LIVE_ACTIONS_ATTESTATION`:
it is **not** proof of a fresh GitHub Actions download, publisher signature,
1024x768 GUI success, WACK, MSIX build, authenticated Partner Center Identity,
or E2E completion. Keep those gates independent and HOLD until evidenced.

Partner Center registration type for every APP in this cohort:
`MSIX_OR_PWA_APP`; selection: **MSIX or PWA app**.
An intermediate unsigned EXE must never switch the registration family to
`EXE_OR_MSI_APP`. Offline Notes Canary Identity remains
`REFERENCE_AVAILABLE` and must not be requested again or CAS-bound without
36-minute lane authenticated evidence. Focus Session Desk is the next new
Partner Center registration trial; its reserved display name is not yet verified.

The 00-minute lane has now downloaded the pinned File Integrity Ledger
artifact (GitHub artifact #12826068537) and independently rechecked all five
ZIP/EXE pairs against the recorded SHA-256 and source/request metadata.
This does not replace a successful run of the integrated dispatcher CLI with
all five explicit paths, nor does it constitute a fresh attestation for the
four previously saved ZIP copies.

This is a verification contract, not an unattended artifact downloader. The
36-minute Windows/E2E lane owns automated download/consumption and the central
E2E ledger. The 00-minute lane does not claim to have wired that external
consumer until it actually invokes this command and checks its exit status.
