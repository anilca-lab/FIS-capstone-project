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

myclient = pymongo.MongoClient('mongodb://127.0.0.1:27017/')
mydb = myclient['Indeed-job-vacancies']
mycollection = mydb['Job-headings']
df = pd.DataFrame(mycollection.find({}))
df_test = df.sample(n = 200, replace = False, random_state = 10720)
df_training = df.drop(index = df_test.index)
df_test.to_csv('47900_test.csv')
df_training.to_csv('47900_training.csv')

indeed_titles = list(df_training.title)
indeed_tokens_list = [word_tokenize(title) for title in indeed_titles]
stopwords_list = stopwords.words('english')
stopwords_list += list(string.punctuation)
stopwords_list += [str(d) for d in range(10)]
indeed_stopped_tokens_list = []
for tokens in indeed_tokens_list:
    stopped_tokens = []
    for token in tokens:
        token_lower = token.lower()
        if token_lower not in stopwords_list:
            pattern = r'[a-z]{3,}'
            token_lower = re.findall(pattern, token_lower)
            stopped_tokens.extend(token_lower)
    indeed_stopped_tokens_list.append(stopped_tokens)

onet_alternate_titles = pd.read_csv('https://www.onetcenter.org/dl_files/database/db_24_1_text/Alternate%20Titles.txt', sep = '\t')
onet_titles = onet_alternate_titles['Alternate Title']
onet_tokens_list = [word_tokenize(title) for title in onet_titles]
onet_stopped_tokens_list = []
for tokens in onet_tokens_list:
    stopped_tokens = []
    for token in tokens:
        token_lower = token.lower()
        if token_lower not in stopwords_list:
            pattern = r'[a-z]{3,}'
            token_lower = re.findall(pattern, token_lower)
            stopped_tokens.extend(token_lower)
    onet_stopped_tokens_list.append(stopped_tokens)

corpus_tokens_list = indeed_stopped_tokens_list + onet_stopped_tokens_list
    
dim = 300
wsize = 5
model = Word2Vec(corpus_tokens_list, 
                 size = dim, 
                 window = wsize, 
                 min_count = 5, 
                 workers = multiprocessing.cpu_count())
model.train(corpus_tokens_list, total_examples = model.corpus_count, epochs = model.epochs)
wv = model.wv
wv['customer']
wv.most_similar('customer')

indeed_vectors_list = []
for title in indeed_stopped_tokens_list:
    vector_title = np.zeros(dim)
    for token in title:
        try:
            vector_title += wv[token]
        except:
            print(token)
    indeed_vectors_list.append(vector_title)

onet_vectors_list = []
for title in onet_stopped_tokens_list:
    vector_title = np.zeros(dim)
    for token in title:
        try:
            vector_title += wv[token]
        except:
            print(token)
    onet_vectors_list.append(vector_title)

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