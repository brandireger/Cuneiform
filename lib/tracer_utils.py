"""Pure helpers for scorer-sensitivity tracers.

The perturbation must match the scorer's invariances. Sequence scorers can be
tested by permuting token order. Bag-of-words scorers cannot: permutation
preserves their complete input representation. For those scorers, replace
token identities while preserving length.
"""


def permute_token_order(lines, rng):
    """Shuffle token order while preserving line lengths and damage states."""
    flat_items = [item for _, tokens in lines for item in tokens]
    token_values = [
        item[0] if isinstance(item, tuple) else item
        for item in flat_items
    ]
    shuffled = token_values[:]
    rng.shuffle(shuffled)

    out = []
    cursor = 0
    for line_index, tokens in lines:
        new_tokens = []
        for item in tokens:
            replacement = shuffled[cursor]
            if isinstance(item, tuple):
                new_tokens.append((replacement, item[1]))
            else:
                new_tokens.append(replacement)
            cursor += 1
        out.append((line_index, new_tokens))
    return out


def corrupt_token_identities(tokens, rng, vocabulary):
    """Replace every token with a different vocabulary item.

    This is the order-invariant counterpart to :func:`permute_token_order`.
    Sequence length is preserved, but the bag of lexical identities changes.
    """
    vocabulary = tuple(dict.fromkeys(vocabulary))
    if len(vocabulary) < 2:
        raise ValueError(
            "corrupt_token_identities requires at least two vocabulary items")

    out = []
    for token in tokens:
        replacement = vocabulary[rng.randrange(len(vocabulary))]
        while replacement == token:
            replacement = vocabulary[rng.randrange(len(vocabulary))]
        out.append(replacement)
    return out
