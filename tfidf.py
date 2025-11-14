from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

class TfidfRetriever:
    def __init__(self, passages):
        self.passages = passages
        self.vectorizer = TfidfVectorizer(
            analyzer="char_wb",     # character n-grams within word boundaries
            ngram_range=(3, 5),     # better for German compounds / typos
            lowercase=True,
            min_df=1,
            use_idf=True,
            smooth_idf=True,
            sublinear_tf=True,
            norm="l2",
        )
        self.X = self.vectorizer.fit_transform([p["text"] for p in passages])

    def search(self, query, k=3):
        q = self.vectorizer.transform([query])
        # cosine on L2-normalized TF-IDF == dot product
        scores = (self.X @ q.T).toarray().ravel()
        order = scores.argsort()[::-1][:k]
        return [self.passages[i] for i in order], scores[order]
