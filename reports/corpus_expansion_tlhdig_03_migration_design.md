# TLHdig 0.3 migration-design findings

**[AUDIT — no corpus migration, split change, scoring, or training]**

## Decision

**KEEP TLHdig 0.2 PINNED; PREPARE A VERSIONED 0.3 INGESTION PROTOTYPE, NOT A DIRECT REPLACEMENT.** The expansion is material, but most candidate additions are discovery-bin records and 0.3 contains identifier collisions that cross frozen split classes.

## Identifier reconciliation

Of 2,137 candidate-only filename stems, 49 are conservative one-to-one identifier revisions and 5 more belong to unresolved revision groups. 2,083 remain plausible additions. No payload was opened for this reconciliation.

Probable revisions: {'encoding_artifact_change': 4, 'punctuation_or_spacing_change': 3, 'trailing_join_marker_change': 42}. These are identity hypotheses from filenames, not content equivalence claims.

## Where the plausible additions fall

Prospective CTH-folder split counts: `{'dev': 15, 'discovery': 1753, 'mixed_split_or_cth': 1, 'test': 26, 'train': 281, 'unknown_cth': 7}`. 1,753 (84.16%) fall in discovery bins and cannot become supervised labels under the standing bin rule. The upper bound in known real non-test compositions is 296 stems (281 train; 15 dev), while 26 map prospectively to protected test compositions and remain unopened.

The largest unresolved series are: EBo (1,371), DAAM (280), CHDS (189), KBo (119), KUB (43), Bo (32).

## Duplicate-identifier barrier

TLHdig 0.3 has 132 duplicate filename stems. 90 span multiple frozen split classes or an unknown CTH, and 21 involve a test composition. A migration must canonicalize identifier groups before creating a new versioned split; naïve folder inheritance would risk leakage.

## XML regression diagnosis

All 12 reads were unique allowed non-test parse failures. Test, unmatched, and duplicate-stem payload reads remained zero. Root causes: `{'invalid_qname_ao_dash_linenr': 8, 'namespace_prefix_mismatch': 1, 'unclosed_empty_damage_word_at_line_boundary': 1, 'unclosed_inline_element_before_word_close': 1, 'unescaped_markup_inside_attribute': 1}`.

Eight failures use the invalid QName `AO:-LineNrExpl`; the others are an unescaped closing tag inside an attribute, an unclosed `sGr`, a namespace-prefix mismatch, and seven unclosed empty-damage word elements in the one persistent 0.2/0.3 failure. Do not use a permissive recovery parser: apply checksum-guarded, document-specific repairs or obtain corrected upstream XML so damage-state order cannot be silently altered.

## Next gate

Build a separate 0.3 ingestion prototype that (1) constructs canonical identifier groups, (2) quarantines every cross-CTH group, (3) applies reviewed checksum-guarded XML repairs, and (4) reports how many of the 281 prospective train additions are actually parseable and Hittite-bearing. Do not touch the current 0.2 datasets or frozen splits during that prototype.

Cost: 1.6s; no model/content-sensitivity tracer was applicable.

Corpus sources: Müller, Prechel, Rieken & Schwemer, TLHdig Beta 0.2.0, DOI 10.5281/zenodo.15459134 (CC BY 4.0); TLHdig Beta 0.3, DOI 10.5281/zenodo.20328284 (CC BY 4.0).
