from collections import Counter
from dataclasses import dataclass
import math
import re

from app.web_extract import (
    ExtractedWebPage,
)


TARGET_PASSAGE_CHARS = 1200
PASSAGE_OVERLAP_CHARS = 200
DEFAULT_TOP_K = 5

_BM25_K1 = 1.2
_BM25_B = 0.75

_EN_STOPWORDS = {
    "a",
    "an",
    "the",
    "what",
    "where",
    "when",
    "who",
    "why",
    "how",
    "is",
    "are",
    "was",
    "were",
    "do",
    "does",
    "did",
    "my",
    "your",
    "i",
    "you",
    "for",
    "to",
    "of",
    "in",
    "on",
    "and",
    "or",
    "about",
    "please",
}

_ZH_STOPWORDS = {
    "的",
    "了",
    "是",
    "在",
    "我",
    "你",
    "请",
    "和",
    "与",
    "及",
}

_TOKEN_RE = re.compile(
    r"[a-z0-9]+"
    r"(?:[._+-][a-z0-9]+)*"
    r"|"
    r"[\u3400-\u4dbf"
    r"\u4e00-\u9fff"
    r"\uf900-\ufaff]+",
    flags=re.IGNORECASE,
)


class WebPassageError(
    ValueError
):
    def __init__(
        self,
        code,
        message,
    ):
        super().__init__(
            message
        )
        self.code = str(
            code
        )


@dataclass(
    frozen=True,
    slots=True,
)
class WebPassage:
    passage_id: str
    ordinal: int
    start_char: int
    end_char: int
    text: str


@dataclass(
    frozen=True,
    slots=True,
)
class RankedWebPassage:
    passage: WebPassage
    score: float
    matched_terms: tuple[str, ...]
    exact_phrase_match: bool


def _raise(
    code,
    message,
):
    raise WebPassageError(
        code,
        message,
    )


def _is_han_text(
    value,
):
    return all(
        (
            "\u3400" <= char <= "\u4dbf"
            or "\u4e00" <= char <= "\u9fff"
            or "\uf900" <= char <= "\ufaff"
        )
        for char in value
    )


def lexical_terms(
    text,
):
    if not isinstance(
        text,
        str,
    ):
        _raise(
            "WEB_PASSAGE_TEXT_INVALID",
            "lexical input must be text",
        )

    terms = []

    for token in _TOKEN_RE.findall(
        text.casefold()
    ):
        if _is_han_text(
            token
        ):
            if (
                token
                not in _ZH_STOPWORDS
            ):
                terms.append(
                    token
                )

            if len(token) >= 2:
                for index in range(
                    len(token) - 1
                ):
                    bigram = token[
                        index:index + 2
                    ]

                    if (
                        bigram
                        not in _ZH_STOPWORDS
                    ):
                        terms.append(
                            bigram
                        )

        elif (
            token
            not in _EN_STOPWORDS
        ):
            terms.append(
                token
            )

    return tuple(
        terms
    )


def _preferred_end(
    text,
    start,
    maximum_end,
    *,
    target_chars,
):
    if maximum_end >= len(text):
        return len(text)

    preferred_breaks = (
        "\n\n",
        "\n",
        ". ",
        "? ",
        "! ",
        "。 ",
        "？ ",
        "！ ",
        "; ",
        "； ",
        ", ",
        "， ",
        " ",
    )

    minimum_end = min(
        maximum_end,
        start
        + max(
            1,
            target_chars // 2,
        ),
    )

    window = text[
        minimum_end:maximum_end
    ]

    for separator in preferred_breaks:
        position = window.rfind(
            separator
        )

        if position >= 0:
            end = (
                minimum_end
                + position
                + len(separator)
            )

            if end > start:
                return end

    return maximum_end


def build_web_passages(
    page,
    *,
    target_chars=TARGET_PASSAGE_CHARS,
    overlap_chars=PASSAGE_OVERLAP_CHARS,
):
    if not isinstance(
        page,
        ExtractedWebPage,
    ):
        _raise(
            "WEB_PASSAGE_INPUT_INVALID",
            (
                "page must be an "
                "ExtractedWebPage"
            ),
        )

    target_chars = int(
        target_chars
    )
    overlap_chars = int(
        overlap_chars
    )

    if target_chars <= 0:
        _raise(
            "WEB_PASSAGE_SIZE_INVALID",
            "target_chars must be positive",
        )

    if (
        overlap_chars < 0
        or overlap_chars >= target_chars
    ):
        _raise(
            "WEB_PASSAGE_OVERLAP_INVALID",
            (
                "overlap_chars must be >= 0 "
                "and smaller than target_chars"
            ),
        )

    text = page.text

    if not text:
        return ()

    passages = []
    start = 0

    while start < len(text):
        maximum_end = min(
            len(text),
            start + target_chars,
        )

        end = _preferred_end(
            text,
            start,
            maximum_end,
            target_chars=target_chars,
        )

        if end <= start:
            end = maximum_end

        passage_text = text[
            start:end
        ].strip()

        if passage_text:
            passages.append(
                WebPassage(
                    passage_id=(
                        f"passage_"
                        f"{len(passages) + 1}"
                    ),
                    ordinal=len(
                        passages
                    ),
                    start_char=start,
                    end_char=end,
                    text=passage_text,
                )
            )

        if end >= len(text):
            break

        next_start = max(
            start + 1,
            end - overlap_chars,
        )

        while (
            next_start < end
            and next_start < len(text)
            and not text[
                next_start
            ].isspace()
        ):
            next_start += 1

        while (
            next_start < len(text)
            and text[
                next_start
            ].isspace()
        ):
            next_start += 1

        start = next_start

    return tuple(
        passages
    )


def rank_web_passages(
    query,
    passages,
):
    if not isinstance(
        query,
        str,
    ):
        _raise(
            "WEB_PASSAGE_QUERY_INVALID",
            "query must be text",
        )

    query = " ".join(
        query.split()
    )

    if not query:
        _raise(
            "WEB_PASSAGE_QUERY_INVALID",
            "query must not be empty",
        )

    passages = tuple(
        passages
    )

    if not passages:
        return ()

    for passage in passages:
        if not isinstance(
            passage,
            WebPassage,
        ):
            _raise(
                "WEB_PASSAGE_INPUT_INVALID",
                (
                    "passages must contain "
                    "WebPassage records"
                ),
            )

    query_terms = lexical_terms(
        query
    )

    if not query_terms:
        return tuple(
            RankedWebPassage(
                passage=passage,
                score=0.0,
                matched_terms=(),
                exact_phrase_match=False,
            )
            for passage in passages
        )

    passage_terms = [
        lexical_terms(
            passage.text
        )
        for passage in passages
    ]

    term_counts = [
        Counter(
            terms
        )
        for terms in passage_terms
    ]

    document_frequency = Counter()

    for counts in term_counts:
        for term in counts:
            document_frequency[
                term
            ] += 1

    document_count = len(
        passages
    )

    lengths = [
        len(terms)
        for terms in passage_terms
    ]

    average_length = (
        sum(lengths)
        / document_count
        if document_count
        else 1.0
    )

    if average_length <= 0:
        average_length = 1.0

    query_counter = Counter(
        query_terms
    )

    normalized_phrase = (
        query.casefold()
    )

    ranked = []

    for (
        passage,
        counts,
        document_length,
    ) in zip(
        passages,
        term_counts,
        lengths,
    ):
        score = 0.0
        matched = []

        for (
            term,
            query_frequency,
        ) in query_counter.items():
            frequency = counts.get(
                term,
                0,
            )

            if frequency <= 0:
                continue

            matched.append(
                term
            )

            df = document_frequency[
                term
            ]

            idf = math.log(
                1.0
                + (
                    (
                        document_count
                        - df
                        + 0.5
                    )
                    / (
                        df
                        + 0.5
                    )
                )
            )

            denominator = (
                frequency
                + _BM25_K1
                * (
                    1.0
                    - _BM25_B
                    + _BM25_B
                    * (
                        document_length
                        / average_length
                    )
                )
            )

            score += (
                idf
                * (
                    frequency
                    * (
                        _BM25_K1
                        + 1.0
                    )
                    / denominator
                )
                * query_frequency
            )

        exact_phrase_match = (
            normalized_phrase
            in passage.text.casefold()
        )

        if exact_phrase_match:
            score += 2.0

        ranked.append(
            RankedWebPassage(
                passage=passage,
                score=float(
                    score
                ),
                matched_terms=tuple(
                    sorted(
                        set(
                            matched
                        )
                    )
                ),
                exact_phrase_match=(
                    exact_phrase_match
                ),
            )
        )

    ranked.sort(
        key=lambda item: (
            -item.score,
            item.passage.ordinal,
        )
    )

    return tuple(
        ranked
    )


def select_web_passages(
    query,
    passages,
    *,
    top_k=DEFAULT_TOP_K,
):
    top_k = int(
        top_k
    )

    if top_k <= 0:
        _raise(
            "WEB_PASSAGE_TOP_K_INVALID",
            "top_k must be positive",
        )

    ranked = rank_web_passages(
        query,
        passages,
    )

    selected = [
        item
        for item in ranked
        if item.score > 0.0
    ]

    return tuple(
        selected[:top_k]
    )
