import warnings

import numpy as np
from typing import Union, List
from sklearn.metrics import pairwise_distances
from gensim.models import KeyedVectors


from whatlies.embedding import Embedding
from whatlies.embeddingset import EmbeddingSet
from whatlies.language.common import SklearnTransformerMixin


class GensimLanguage(SklearnTransformerMixin):
    """
    This object is used to lazily fetch [Embedding][whatlies.embedding.Embedding]s or
    [EmbeddingSet][whatlies.embeddingset.EmbeddingSet]s from a keyed vector file.
    These files are generated by [gensim](https://radimrehurek.com/gensim/models/word2vec.html).
    This object is meant for retreival, not plotting.

    Important:
        The vectors are not given by this library they must be download/created upfront.
        A potential benefit of this is that you can train your own embeddings using
        gensim and visualise them using this library.

        Here's a snippet that you can use to train your own (very limited) word2vec embeddings.

        ```
        from gensim.test.utils import common_texts
        from gensim.models import Word2Vec
        model = Word2Vec(common_texts, size=10, window=5, min_count=1, workers=4)
        model.wv.save("wordvectors.kv")
        ```

        Note that if a word is not available in the keyed vectors file then we'll assume
        a zero vector. If you pass a sentence then we'll add together the embeddings vectors
        of the seperate words.

    Arguments:
        keyedfile: name of the model to load, be sure that it's downloaded or trained beforehand

    **Usage**:

    ```python
    > from whatlies.language import GensimLanguage
    > lang = GensimLanguage("wordvectors.kv")
    > lang['computer']
    > lang = GensimLanguage("wordvectors.kv", size=10)
    > lang[['computer', 'human', 'dog']]
    ```
    """

    def __init__(self, keyedfile):
        self.kv = KeyedVectors.load(keyedfile)

    def __getitem__(self, query: Union[str, List[str]]):
        """
        Retreive a single embedding or a set of embeddings.

        Arguments:
            query: single string or list of strings

        **Usage**
        ```python
        > from whatlies.language import GensimLanguage
        > lang = GensimLanguage("wordvectors.kv")
        > lang['computer']
        > lang = GensimLanguage("wordvectors.kv", size=10)
        > lang[['computer', 'human', 'dog']]
        ```
        """
        if isinstance(query, str):
            if " " in query:
                return Embedding(
                    query, np.sum([self[q].vector for q in query.split(" ")], axis=0)
                )
            try:
                vec = np.sum([self.kv[q] for q in query.split(" ")], axis=0)
            except KeyError:
                vec = np.zeros(self.kv.vector_size)
            return Embedding(query, vec)
        return EmbeddingSet(*[self[tok] for tok in query])

    def score_similar(
        self, emb: Union[str, Embedding], n: int = 10, metric="cosine", lower=False,
    ) -> List:
        """
        Retreive a list of (Embedding, score) tuples that are the most similar to the passed query.

        Arguments:
            emb: query to use
            n: the number of items you'd like to see returned
            metric: metric to use to calculate distance, must be scipy or sklearn compatible
            lower: only fetch lower case tokens

        Returns:
            An list of ([Embedding][whatlies.embedding.Embedding], score) tuples.
        """
        if isinstance(emb, str):
            emb = self[emb]

        queries = self._prepare_queries(lower=lower)
        distances = self._calculate_distances(emb=emb, queries=queries, metric=metric)
        by_similarity = sorted(zip(queries, distances), key=lambda z: z[1])

        if len(queries) < n:
            warnings.warn(
                f"We could only find {len(queries)} feasible words. Consider changing `top_n` or `lower`",
                UserWarning,
            )

        return [(self[q], float(d)) for q, d in by_similarity[:n]]

    def embset_similar(
        self, emb: Union[str, Embedding], n: int = 10, lower=False, metric="cosine",
    ) -> EmbeddingSet:
        """
        Retreive an [EmbeddingSet][whatlies.embeddingset.EmbeddingSet] that are the most similar to the passed query.

        Arguments:
            emb: query to use
            n: the number of items you'd like to see returned
            metric: metric to use to calculate distance, must be scipy or sklearn compatible
            lower: only fetch lower case tokens

        Returns:
            An [EmbeddingSet][whatlies.embeddingset.EmbeddingSet] containing the similar embeddings.
        """
        embs = [
            w[0] for w in self.score_similar(emb=emb, n=n, lower=lower, metric=metric)
        ]
        return EmbeddingSet({w.name: w for w in embs})
