# Security

Please report vulnerabilities privately through GitHub: **Security → Report a vulnerability** on this repository. Do not open a public issue.

Supported versions: the latest release.

Notes for users:

- DedupKit reads only the data you pass to it. It makes no network calls (the evaluation scripts download the public catalog sample; the library does not).
- Matching compares every pair inside a block, so the cost grows with the square of the block size. Keep `max_block` low (default 100) on untrusted input.
- Regular expressions use bounded patterns without nested quantifiers.
