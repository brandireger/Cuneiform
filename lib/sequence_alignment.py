"""Deterministic, inspectable sequence alignment for bounded missing spans.

This module contains no corpus loading and no task labels. It aligns a fully
observed left flank and right flank to a witness sequence while reserving a
bounded monotonic witness interval between them as a candidate middle.
"""


def _best_move(diagonal, query_gap, witness_gap):
    """Return deterministic maximum: diagonal, then query gap, then witness."""
    choices = [
        (diagonal, 2, "diagonal"),
        (query_gap, 1, "query_gap"),
        (witness_gap, 0, "witness_gap"),
    ]
    return max(choices)[0], max(choices)[2]


def semiglobal_end_profiles(
        query,
        witness,
        match_score=2,
        mismatch_score=-1,
        gap_score=-1):
    """Align all of ``query`` to a witness substring ending at every boundary.

    Witness prefix is free; query prefix/suffix is not. Profile ``b`` ends at
    witness boundary ``b`` (between tokens b-1 and b).
    """
    query = tuple(query)
    witness = tuple(witness)
    rows = len(query) + 1
    columns = len(witness) + 1
    scores = [[0] * columns for _ in range(rows)]
    moves = [[None] * columns for _ in range(rows)]
    for query_index in range(1, rows):
        scores[query_index][0] = query_index * gap_score
        moves[query_index][0] = "witness_gap"
    for witness_index in range(1, columns):
        moves[0][witness_index] = "free_prefix"

    for query_index in range(1, rows):
        for witness_index in range(1, columns):
            token_score = (
                match_score
                if query[query_index - 1] == witness[witness_index - 1]
                else mismatch_score
            )
            score, move = _best_move(
                scores[query_index - 1][witness_index - 1] + token_score,
                scores[query_index][witness_index - 1] + gap_score,
                scores[query_index - 1][witness_index] + gap_score,
            )
            scores[query_index][witness_index] = score
            moves[query_index][witness_index] = move

    profiles = []
    for endpoint in range(columns):
        query_index = len(query)
        witness_index = endpoint
        aligned_query = []
        aligned_witness = []
        matches = 0
        mismatches = 0
        query_gaps = 0
        witness_gaps = 0
        while query_index > 0:
            move = moves[query_index][witness_index]
            if move == "diagonal":
                query_token = query[query_index - 1]
                witness_token = witness[witness_index - 1]
                aligned_query.append(query_token)
                aligned_witness.append(witness_token)
                if query_token == witness_token:
                    matches += 1
                else:
                    mismatches += 1
                query_index -= 1
                witness_index -= 1
            elif move == "query_gap":
                aligned_query.append(None)
                aligned_witness.append(witness[witness_index - 1])
                query_gaps += 1
                witness_index -= 1
            elif move == "witness_gap":
                aligned_query.append(query[query_index - 1])
                aligned_witness.append(None)
                witness_gaps += 1
                query_index -= 1
            else:
                raise AssertionError(
                    "alignment traceback reached an invalid move")
        profiles.append({
            "score": scores[len(query)][endpoint],
            "witness_start": witness_index,
            "witness_end": endpoint,
            "exact_matches": matches,
            "mismatches": mismatches,
            "query_gaps": query_gaps,
            "witness_gaps": witness_gaps,
            "aligned_query": tuple(reversed(aligned_query)),
            "aligned_witness": tuple(reversed(aligned_witness)),
        })
    return profiles


def _right_profiles(
        query,
        witness,
        match_score,
        mismatch_score,
        gap_score):
    reversed_profiles = semiglobal_end_profiles(
        tuple(reversed(query)),
        tuple(reversed(witness)),
        match_score=match_score,
        mismatch_score=mismatch_score,
        gap_score=gap_score,
    )
    result = {}
    witness_length = len(witness)
    for reversed_endpoint, profile in enumerate(reversed_profiles):
        start = witness_length - reversed_endpoint
        result[start] = {
            **profile,
            "witness_start": start,
            "witness_end":
                witness_length - profile["witness_start"],
            "aligned_query":
                tuple(reversed(profile["aligned_query"])),
            "aligned_witness":
                tuple(reversed(profile["aligned_witness"])),
        }
    return result


def bounded_two_flank_alignments(
        left_flank,
        right_flank,
        witness,
        *,
        maximum_middle_length,
        minimum_exact_matches_per_flank=2,
        minimum_normalized_score=0.5,
        match_score=2,
        mismatch_score=-1,
        gap_score=-1):
    """Return valid monotonic alignments and their candidate witness middles."""
    left_flank = tuple(left_flank)
    right_flank = tuple(right_flank)
    witness = tuple(witness)
    if not left_flank or not right_flank:
        return []
    left_profiles = semiglobal_end_profiles(
        left_flank,
        witness,
        match_score=match_score,
        mismatch_score=mismatch_score,
        gap_score=gap_score,
    )
    right_profiles = _right_profiles(
        right_flank,
        witness,
        match_score,
        mismatch_score,
        gap_score,
    )
    maximum_score = match_score * (
        len(left_flank) + len(right_flank))
    if maximum_score <= 0:
        raise ValueError("match_score and flank lengths must yield max > 0")

    best_by_middle = {}
    for left_boundary, left in enumerate(left_profiles):
        if left["exact_matches"] < minimum_exact_matches_per_flank:
            continue
        maximum_right = min(
            len(witness), left_boundary + maximum_middle_length)
        for right_boundary in range(left_boundary, maximum_right + 1):
            right = right_profiles[right_boundary]
            if right["exact_matches"] < minimum_exact_matches_per_flank:
                continue
            score = left["score"] + right["score"]
            normalized = score / maximum_score
            if normalized < minimum_normalized_score:
                continue
            middle = witness[left_boundary:right_boundary]
            alignment = {
                "middle": middle,
                "score": score,
                "normalized_score": round(normalized, 6),
                "exact_matches": (
                    left["exact_matches"] + right["exact_matches"]),
                "left_boundary": left_boundary,
                "right_boundary": right_boundary,
                "left": left,
                "right": right,
            }
            previous = best_by_middle.get(middle)
            signature = (
                alignment["score"],
                alignment["exact_matches"],
                -left_boundary,
                -right_boundary,
            )
            if previous is None:
                best_by_middle[middle] = alignment
            else:
                previous_signature = (
                    previous["score"],
                    previous["exact_matches"],
                    -previous["left_boundary"],
                    -previous["right_boundary"],
                )
                if signature > previous_signature:
                    best_by_middle[middle] = alignment

    return sorted(
        best_by_middle.values(),
        key=lambda value: (
            -value["score"],
            -value["exact_matches"],
            value["middle"],
            value["left_boundary"],
            value["right_boundary"],
        ),
    )
