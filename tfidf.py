import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


class TfidfRetriever:
    """
    Lexical retriever with a small fusion:
    - char_wb 3-5 grams (robust to German compounds/typos)
    - word 1-2 grams (better for normal phrasing and key terms)

    We compute cosine similarities for both (TF-IDF is L2-normalized),
    normalize each score vector to [0, 1] by dividing by its max,
    then fuse with a weighted sum.
    """

    def __init__(self, passages, w_char: float = 0.6, w_word: float = 0.4):
        self.passages = passages
        self.w_char = float(w_char)
        self.w_word = float(w_word)

        texts = [p["text"] for p in passages]

        # Character n-grams within word boundaries (great for German + typos)
        self.vectorizer_char = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            lowercase=True,
            min_df=1,
            use_idf=True,
            smooth_idf=True,
            sublinear_tf=True,
            norm="l2",
        )
        self.X_char = self.vectorizer_char.fit_transform(texts)

        # Word n-grams (helps normal keyword matching and longer queries)
        self.vectorizer_word = TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),
            lowercase=True,
            min_df=1,
            use_idf=True,
            smooth_idf=True,
            sublinear_tf=True,
            norm="l2",
            token_pattern=r"(?u)\b\w+\b",
        )
        self.X_word = self.vectorizer_word.fit_transform(texts)

        # Backwards-compat attributes (some code may reference these)
        self.vectorizer = self.vectorizer_char
        self.X = self.X_char

    @staticmethod
    def _safe_unit_max(scores: np.ndarray) -> np.ndarray:
        m = float(scores.max()) if scores.size else 0.0
        if m <= 0.0:
            return scores
        return scores / (m + 1e-12)

    def search(self, query, k=3):
        # cosine on L2-normalized TF-IDF == dot product
        q_char = self.vectorizer_char.transform([query])
        scores_char = (self.X_char @ q_char.T).toarray().ravel()

        q_word = self.vectorizer_word.transform([query])
        scores_word = (self.X_word @ q_word.T).toarray().ravel()

        s_char = self._safe_unit_max(scores_char)
        s_word = self._safe_unit_max(scores_word)

        scores = (self.w_char * s_char) + (self.w_word * s_word)
        order = scores.argsort()[::-1][:k]
        return [self.passages[i] for i in order], scores[order]
