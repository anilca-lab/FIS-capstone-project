#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 15 22:27:08 2020

@author: flatironschol
"""
import streamlit as st
import pandas as pd
import numpy as np
from nltk import word_tokenize
from gensim.models.keyedvectors import KeyedVectors
from gensim.models import Word2Vec
from gensim.test.utils import get_tmpfile
import plotly.figure_factory as ff
import time
from data_cleaning import create_stop_words, clean_soc_titles, stop_tokenized_titles, substitute_words 
from soc_classification import find_most_similar

@st.cache
def get_stopwords():
    stopwords_list = create_stop_words()
    return stopwords_list

@st.cache
def get_soc_titles():
    soc_titles_df = clean_soc_titles()
    return soc_titles_df

@st.cache
def tokenize_soc_titles(soc_titles_df, stopwords_list):
    tokenized_soc_titles_list = [word_tokenize(title) for title in soc_titles_df.title]
    stopped_tokenized_soc_titles_list = stop_tokenized_titles(tokenized_soc_titles_list, stopwords_list)
    return stopped_tokenized_soc_titles_list

@st.cache
def get_pretrained_model():
#    print(f'3 {time.perf_counter()}')
#    wv = KeyedVectors.load_word2vec_format('../data/GoogleNews-vectors-negative300.bin.gz', binary=True)
    model = Word2Vec.load('../data/model2_large_corpus.model')
    wv = model.wv
    return wv

@st.cache
def get_actual_soc():
    actual_soc_df = pd.read_excel('../data/soc_structure_2010.xls')
    six_dig_df = actual_soc_df[['Unnamed: 2','Unnamed: 4']]
    six_dig_df = six_dig_df.rename(columns = {'Unnamed: 2': 'soc_code_6',
                                              'Unnamed: 4': 'soc_title_6'})
    six_dig_df = six_dig_df.dropna()
    six_dig_df['soc_code_2'] = [code[0:2] for code in six_dig_df.soc_code_6]
    two_dig_df = actual_soc_df[['Bureau of Labor Statistics','Unnamed: 4']]
    two_dig_df = two_dig_df.rename(columns = {'Bureau of Labor Statistics': 'soc_code_2',
                                              'Unnamed: 4': 'soc_title_2'})
    two_dig_df = two_dig_df.dropna()
    two_dig_df['soc_code_2'] = [code[0:2] for code in two_dig_df.soc_code_2]
    actual_soc_df = six_dig_df.merge(two_dig_df, how = 'inner', on = 'soc_code_2')
    return actual_soc_df
    
@st.cache(allow_output_mutation = True)
def get_existing_vacancies():
    classified_vacancies_df = pd.read_csv('classified_vacancies_upd.csv')
    return classified_vacancies_df

@st.cache(allow_output_mutation = True)
def get_fips():
    fips_df = pd.read_excel('list1_Sep_2018.xls', skiprows = 2, dtype = {'CBSA Code': str,
                                                                         'FIPS State Code': str,
                                                                         'FIPS County Code': str})
    fips_df = fips_df[['CBSA Code', 'FIPS State Code', 'FIPS County Code']]
    #fips_df['state'] = ['0' + state if len(state) == 1 else state for state in fips_df['FIPS State Code']]
    #fips_df['county'] = ['00' + state if len(state) == 1 else '0' + state if len(state) == 2 else state for state in fips_df['FIPS County Code']]
    fips_df['fips'] = fips_df['FIPS State Code'] + fips_df['FIPS County Code']
    fips_df = fips_df.drop(columns = ['FIPS State Code', 'FIPS County Code'])
    fips_df = fips_df.rename(columns = {'CBSA Code': 'msa'})
    return fips_df

def plot_map(family):
    classified_vacancies_df = get_existing_vacancies()
    classified_vacancies_df['msa'] = [str(msa)[0:5] for msa in classified_vacancies_df.msa]
    family_df = classified_vacancies_df.loc[classified_vacancies_df.soc_code_6 == family]
    family_df = family_df.groupby(['msa']).count()[['title']].reset_index()
    fips_df = get_fips()
    family_df = family_df.merge(fips_df, how = 'inner', on = 'msa')
    fips = family_df.fips
    values = family_df.title
    endpts = list(np.mgrid[min(values):max(values):5j])
    fig = ff.create_choropleth(fips=fips, values=values, binning_endpoints=endpts, legend_title='Number of vacancies', round_legend_values=True, state_outline={'width': 1})
    fig.layout.template = None
    return fig
    
def main():
    page = st.sidebar.selectbox("Choose a task:", ['Classify', 'Visualize', 'Test yourself'])
    if page == 'Classify':
        st.title('Find the Family of a Job')
        title = st.text_input('Enter a job title:')
        if title.strip() != '':
            wv = get_pretrained_model()
            soc_titles_df = get_soc_titles()
            stopwords_list = get_stopwords()
            stopped_tokenized_soc_titles_list = tokenize_soc_titles(soc_titles_df, stopwords_list)        
            tokenized_title_list = [word_tokenize(title)]
            stopped_tokenized_title_list = stop_tokenized_titles(tokenized_title_list, stopwords_list)
            stopped_tokenized_title_list = substitute_words(stopped_tokenized_title_list)
            max_similarity_list, max_similarity_index_list = find_most_similar(wv, 600, stopped_tokenized_title_list, stopped_tokenized_soc_titles_list)
            actual_soc_df = get_actual_soc()
            soc_code_6 = soc_titles_df.iloc[max_similarity_index_list[0]].soc_6
            soc_code_6 = soc_code_6[0:6]+'0'
            soc_title = actual_soc_df.loc[actual_soc_df.soc_code_6 == soc_code_6]
            family = soc_title.iloc[0, 1]
            extended_family = soc_title.iloc[0, 3]
            soc_code_2 = soc_code_6[0:2]
            cousins = actual_soc_df.loc[actual_soc_df.soc_code_2 == soc_code_2]
            cousins = cousins.iloc[:, 1]
            cousins = cousins.rename(f'All {extended_family}')
            st.write('**Family:**', family)
            st.write('**Extended family:**', extended_family)
            st.write(cousins)
    elif page == 'Test yourself':
        st.title('Test Yourself against the Machine')
        job_titles = ['Cashier', 'Data Scientist', 'Customer Account Advisor', 'Piano Instructor', 'AMP Hostess', '2020 Summer Games Internship']
        title2 = st.sidebar.selectbox("Select a job title", job_titles, 0)
        st.subheader(title2)
        actual_soc_df = get_actual_soc()
        soc_title_2_list = actual_soc_df.soc_title_2.unique()
        soc_title_2 = st.sidebar.selectbox("Select extended family", soc_title_2_list, 0)
        soc_title_6_list = actual_soc_df.loc[actual_soc_df.soc_title_2 == soc_title_2].soc_title_6.unique()
        soc_title_6 = st.sidebar.selectbox("Select family", soc_title_6_list, 0)
        st.write('**Your classification:**', soc_title_6)
        if st.button('Click to see the machine classification'):
            wv = get_pretrained_model()
            soc_titles_df = get_soc_titles()
            stopwords_list = get_stopwords()
            stopped_tokenized_soc_titles_list = tokenize_soc_titles(soc_titles_df, stopwords_list)        
            tokenized_title_list = [word_tokenize(title2)]
            stopped_tokenized_title_list = stop_tokenized_titles(tokenized_title_list, stopwords_list)
            stopped_tokenized_title_list = substitute_words(stopped_tokenized_title_list)
            max_similarity_list, max_similarity_index_list = find_most_similar(wv, 600, stopped_tokenized_title_list, stopped_tokenized_soc_titles_list)
            soc_code_6 = soc_titles_df.iloc[max_similarity_index_list[0]].soc_6
            soc_code_6 = soc_code_6[0:6]+'0'
            soc_title = actual_soc_df.loc[actual_soc_df.soc_code_6 == soc_code_6]
            family = soc_title.iloc[0, 1]
            st.write('**Machine classification:**', family)
    else:
        actual_soc_df = get_actual_soc()
        soc_title_2_list = actual_soc_df.soc_title_2.unique()
        st.title('Labor Demand across Major Metropolitan Areas')
        soc_title_2 = st.sidebar.selectbox("Select extended family", soc_title_2_list, 0)
        soc_title_6_list = actual_soc_df.loc[actual_soc_df.soc_title_2 == soc_title_2].soc_title_6.unique()
        soc_title_6 = st.sidebar.selectbox("Select family", soc_title_6_list, 0)
        soc_code_6 = actual_soc_df.loc[actual_soc_df.soc_title_6 == soc_title_6].soc_code_6.unique()[0]
        st.subheader(soc_title_6)
        fig = plot_map(soc_code_6)
        st.plotly_chart(fig)
            
if __name__ == '__main__':
    print(f'0 {time.perf_counter()}')
    main()
