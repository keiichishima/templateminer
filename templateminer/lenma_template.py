#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""LenMa: Length Matters Syslog Message Clustering.
"""

from Levenshtein import distance as levenshtein_distance
import numpy as np
from sklearn.metrics import accuracy_score
from sklearn.metrics.pairwise import cosine_similarity
import ssdeep

from templateminer import template

class LenmaTemplate(template.Template):
    def __init__(self, index, words, wordlens=None):
        self._index = index
        self._words = words
        self._nwords = len(words)
        if wordlens is not None:
            assert(len(wordlens) == self._nwords)
            self._wordlens = wordlens
        else:
            self._wordlens = [len(w) for w in words]
        self._counts = 1

    def _try_update(self, new_words):
        try_update = [self.words[idx] if self._words[idx] == new_words[idx]
                      else '' for idx in range(self.nwords)]
        if (self.nwords - try_update.count('')) < 3:
            return False
        return True

    def _get_accuracy_score(self, new_words):
        # accuracy score
        # wildcard word matches any words
        fill_wildcard = [self.words[idx] if self.words[idx] != ''
                         else new_words[idx] for idx in range(self.nwords)]
        ac_score = accuracy_score(fill_wildcard, new_words)
        return ac_score

    def _get_wcr(self):
        return self.words.count('') / self.nwords

    def _get_accuracy_score2(self, new_words):
        # accuracy score 2
        # wildcard word matches nothing
        wildcard_ratio = self._get_wcr()
        ac_score = accuracy_score(self.words, new_words)
        return (ac_score / (1 - wildcard_ratio), wildcard_ratio)

    def _get_similarity_score_cosine(self, new_words):
        # cosine similarity
        wordlens = np.asarray(self._wordlens).reshape(1, -1)
        new_wordlens = np.asarray([len(w) for w in new_words]).reshape(1, -1)
        cos_score = cosine_similarity(wordlens, new_wordlens)
        return cos_score

    def _get_similarity_score_levenshtein(self, new_words):
        # levenshtein edit distance based
        d = sum([levenshtein_distance(self.words[idx],
                                     new_words[idx])
                if self.words[idx] != '' else 0
                for idx in range(self.nwords)])
        levenshtein_score = 1 - d / (sum(self._wordlens)
                                     + sum([len(w) for w in new_words]))
        return levenshtein_score

    def _get_similarity_score_jaccard(self, new_words):
        ws = set(self.words) - set('')
        nws = set([new_words[idx] if self.words[idx] != '' else ''
                   for idx in range(len(new_words))]) - set('')
        return len(ws & nws) / len(ws | nws)

    def _count_same_word_positions(self, new_words):
        c = 0
        for idx in range(self.nwords):
            if self.words[idx] == new_words[idx]:
                c = c + 1
        return c

    def get_similarity_score(self, new_words):
        # heuristic judge: the first word (process name) must be equal
        if self._words[0] != new_words[0]:
            return 0

        # check exact match
        ac_score = self._get_accuracy_score(new_words)
        if  ac_score == 1:
            return 1

        cos_score = self._get_similarity_score_cosine(new_words)

        case = 6
        if case == 1:
            (ac2_score, ac2_wcr) = self._get_accuracy_score2(new_words)
            if ac2_score < 0.5:
                return 0
            return cos_score
        elif case == 2:
            (ac2_score, ac2_wcr) = self._get_accuracy_score2(new_words)
            return (ac2_score + cos_score) / 2
        elif case == 3:
            (ac2_score, ac2_wcr) = self._get_accuracy_score2(new_words)
            return ac2_score * cos_score
        elif case == 4:
            (ac2_score, ac2_wcr) = self._get_accuracy_score2(new_words)
            print(ac2_score, ac2_wcr)
            tw = 0.5
            if ac2_score < tw + (ac2_wcr * (1 - tw)):
                return 0
            return cos_score
        elif case == 5:
            jc_score = self._get_similarity_score_jaccard(new_words)
            if jc_score < 0.5:
                return 0
            return cos_score
        elif case == 6:
            if self._count_same_word_positions(new_words) < 3:
                return 0
            return cos_score

    def update(self, new_words):
        self._counts += 1
        self._wordlens = [len(w) for w in new_words] 
        #self._wordlens = [(self._wordlens[idx] + len(new_words[idx])) / 2
        #                  for idx in range(self.nwords)]
        self._words = [self.words[idx] if self._words[idx] == new_words[idx]
                       else '' for idx in range(self.nwords)]

    def print_wordlens(self):
        print('{index}({nwords})({counts}):{vectors}'.format(
            index=self.index,
            nwords=self.nwords,
            counts=self._counts,
            vectors=self._wordlens))

class LenmaTemplateManager(template.TemplateManager):
    def __init__(self,
                 threshold=0.9,
                 predefined_templates=None):
        self._templates = []
        self._threshold = threshold
        if predefined_templates:
            for template in predefined_templates:
                self._append_template(template)

    def infer_template(self, words):
        nwords = len(words)

        candidates = []
        for (index, template) in enumerate(self._templates):
            if nwords != template.nwords:
                continue
            score = template.get_similarity_score(words)
            if score < self._threshold:
                continue
            candidates.append((index, score))
        candidates.sort(key=lambda c: c[1], reverse=True)
        if False:
            for (i,s) in candidates:
                print('    ', s, self.templates[i])
        if len(candidates) > 0:
            index = candidates[0][0]
            self._templates[index].update(words)
            return self._templates[index]

        new_template = self._append_template(
            LenmaTemplate(len(self._templates), words))
        return new_template


if __name__ == '__main__':
    import datetime
    import sys

    from templateminer.basic_line_parser import BasicLineParser as LP

    parser = LP()
    templ_mgr = LenmaTemplateManager()

    nlines = 0
    line = sys.stdin.readline()
    while line:
        if False:
            if nlines % 1000 == 0:
                print('{0} {1} {2}'.format(nlines, datetime.datetime.now().timestamp(), len(templ_mgr.templates)))
            nlines = nlines + 1
        (month, day, timestr, host, words) = parser.parse(line)
        t = templ_mgr.infer_template(words)
        line = sys.stdin.readline()

    for t in templ_mgr.templates:
        print(t)

    for t in templ_mgr.templates:
        t.print_wordlens()
