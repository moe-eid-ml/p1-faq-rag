from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

class TfidfRetriever:
    def __init__(self, passages):
        self.passages = passages
        self.vectorizer = TfidfVectorizer(lowercase=True, ngram_range=(1,2))
        self.X = self.vectorizer.fit_transform([p["text"] for p in passages])

    def search(self, query, k=3):
        q = self.vectorizer.transform([query])
        scores = (self.X @ q.T).toarray().ravel()   # cosine on tf-idf = dot on L2-normalized rows
        order = scores.argsort()[::-1][:k]
        return [self.passages[i] for i in order], scores[order]
