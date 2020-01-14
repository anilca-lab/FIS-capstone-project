#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan  6 21:55:54 2020

@author: flatironschol
"""
import pymongo
import pandas as pd
from nltk import word_tokenize
from nltk.corpus import stopwords
import string
from nltk.stem.wordnet import WordNetLemmatizer
import re
from gensim.models import Word2Vec 
from sklearn.metrics.pairwise import cosine_similarity
from scipy.spatial import distance
import multiprocessing
import numpy as np

def vectorize_title(wv, dim, stopped_tokenized_titles_list):
    vectorized_title_list = []
    exceptions_list = []
    for tokenized_title in stopped_tokenized_titles_list:
        vectorized_title = np.zeros(dim)
        for token in tokenized_title:
            try:
                vectorized_title += wv[token]
            except:
                exceptions_list.append(token)
        vectorized_title_list.append(vectorized_title)
    return vectorized_title_list

def compute_similarity(stopped_tokenized_indeed_titles_list, stopped_tokenized_soc_titles_list):
    vectorized_indeed_titles_list = vectorize_title(wv, dim, stopped_tokenized_indeed_titles_list)
    vectorized_soc_titles_list = vectorize_title(wv, dim, stopped_tokenized_soc_titles_list)
    similarity_matrix = 1 - distance.cdist(vectorized_indeed_titles_list, vectorized_soc_titles_list, 'cosine')
    max_similarity_list = numpy.amax(similarity_matrix, axis = 1)
    max_similarity_index_list = numpy.amax(similarity_matrix, axis = 1)
    indeed_titles_list = []
    for tokenized_title in stopped_tokenized_indeed_titles_list:
        title = ''
        for token in tokenized_title:
            title += token + ' '
        indeed_titles_list.append(title.rstrip())
    soc_titles_list = []
    for tokenized_title in stopped_tokenized_soc_titles_list:
        title = ''
        for token in tokenized_title:
            title += token + ' '
        soc_titles_list.append(title.rstrip())
        return similarity_list
    
"""
most_similar_titles = []
for i in range(len(indeed_vectors_list)):
    highest_cosine = 0
    highest_j = None
    for j in range(len(onet_vectors_list)):
        cosine = cosine_similarity([indeed_vectors_list[i]], [onet_vectors_list[j]])
        if cosine > highest_cosine:
            highest_cosine = cosine
            highest_j = j
    most_similar_dict = {'indeed_title': indeed_titles[i], 
                         'onet_title': onet_titles[highest_j],
                         'cosine': highest_cosine}
    print(most_similar_dict)
    most_similar_titles.append(most_similar_dict)
"""