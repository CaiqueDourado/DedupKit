# Third-party notices

DedupKit contains no third-party code. It implements ideas from these works:

- **OpenRefine clustering keyers** (fingerprint and n-gram fingerprint), described in
  [OpenRefine: Clustering in depth](https://openrefine.org/docs/technical-reference/clustering-in-depth).
  OpenRefine is BSD-3-Clause licensed. DedupKit's versions differ: accents are removed with a generated table
  and punctuation becomes a space.
- **RSLP stemmer**, plural step: V. M. Orengo and C. Huyck, "A Stemming Algorithm for the Portuguese Language",
  *Proceedings of SPIRE 2001*, pp. 186–193. DedupKit applies a subset of the plural rules to text without accents.
- **GS1 check digit** for GTIN-8/12/13/14, as specified in the GS1 General Specifications.

The Brazilian Portuguese phonetic key is DedupKit's own set of rules (spec/ALGORITHMS.md, section 1.7); it is not a port
of Metaphone-PT or of any other library.
