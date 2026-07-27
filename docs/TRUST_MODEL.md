# Trust Model

The control plane is intentionally bounded: it can propose changes to its configuration artifacts, but cannot authorize its own changes.

## Invariants

- One primary writer operates per transaction.
- The write set is explicit before mutation.
- Deterministic validation precedes semantic review.
- An independent, read-only verifier reviews authored output.
- Failed verification triggers rollback or rejection.
- A run cannot both author and authorize its own change.
- Control-plane agents do not modify application source.
- Manifest policy becomes the canonical source of truth.
- Generated policy files are never edited manually.
- Persistent instructions stay concise and scoped; multi-step procedures belong in skills or workflows.

## Trust boundary

The writer is not trusted to attest to its own authorization. Validation evidence and independent review are required before an external authority accepts a proposal.
