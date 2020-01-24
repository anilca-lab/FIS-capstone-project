#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan  6 21:55:54 2020

@author: flatironschol
"""
import numpy as np
from gensim.models import Word2Vec
from gensim.test.utils import get_tmpfile
from gensim.models.keyedvectors import KeyedVectors
from scipy.spatial import distance
import data_cleaning

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

def find_most_similar(wv, dim, stopped_tokenized_indeed_titles_list, stopped_tokenized_soc_titles_list):
    """
    This function computes cosine similarity between the vacancy titles and 
    the standard occupational titles and returns the highest similarity score
    and the index.
    """
    vectorized_indeed_titles_list = vectorize_title(wv, dim, stopped_tokenized_indeed_titles_list)
    vectorized_soc_titles_list = vectorize_title(wv, dim, stopped_tokenized_soc_titles_list)
    print('starting similarity')
    similarity_matrix = 1 - distance.cdist(vectorized_indeed_titles_list, vectorized_soc_titles_list, 'cosine')
    print('starting masking')
    masked_similarity_matrix = np.ma.masked_invalid(similarity_matrix)
    print('starting amax')
    max_similarity_list = np.amax(masked_similarity_matrix, axis = 1)
    print('starting argmax')
    max_similarity_index_list = np.argmax(masked_similarity_matrix, axis = 1)
    #return max_similarity_list, max_similarity_index_list
    return max_similarity_list, max_similarity_index_list
    
def assign_code(indeed_titles_df, soc_titles_df, soc_index_list, cosine_score_list):
    soc_titles_list = []
    soc_codes_list = []
    for i in soc_index_list:
        try:
            soc_titles_list.append(soc_titles_df.iloc[i].title)
            soc_codes_list.append(soc_titles_df.iloc[i].soc_6)
        except:
            print(soc_titles_df.iloc[i].title, soc_titles_df.iloc[i].soc_6)
    indeed_titles_df['soc_title'] = soc_titles_list
    indeed_titles_df['soc_code'] = soc_codes_list
    indeed_titles_df['cosine_similarity'] = cosine_score_list
    return indeed_titles_df

def drop_duplicate_tokenized_titles(stopped_tokenized_titles_list):
    """
    This function drop duplicates from titles after they are cleaned.
    """
    titles_list = []
    for tokenized_title in stopped_tokenized_titles_list: 
        title = ''
        for token in tokenized_title:
            title += token + ' '
        titles_list.append(title.rstrip())
    titles_almost_orig_df = pd.DataFrame(titles_list)
    titles_df = titles_almost_orig_df.drop_duplicates()
    stopped_tokenized_titles_list = [word_tokenize(title) for title in titles_df[0]]
    return titles_almost_orig_df, titles_df, stopped_tokenized_titles_list