#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 15 22:27:08 2020

@author: flatironschol
"""
import streamlit as st
import pandas as pd
from nltk import word_tokenize
from gensim.models.keyedvectors import KeyedVectors
import plotly.figure_factory as ff
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
    wv = KeyedVectors.load_word2vec_format('../data/GoogleNews-vectors-negative300.bin.gz', binary=True)
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
    
@st.cache
def get_existing_vacancies():
    vacancies_df = pd.read_csv('vacancies.csv')
    return vacancies_df

@st.cache
def get_fips():
    fips_df = pd.read_csv('')
    return fips_df

def plot_map(family):
    vacancies_df = get_existing_vacancies()
    family_df = vacancies_df.loc[vacancies_df.soc_code_6 == family]
    fips_df = get_fips()
    df = family_df.merge(fips_df, how = 'left', on = ['msa'])
    fips = df.fips
    
    fig = ff.create_choropleth(fips=fips, values=values)
    return fig
    
def main():
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
        max_similarity_list, max_similarity_index_list = find_most_similar(wv, 300, stopped_tokenized_title_list, stopped_tokenized_soc_titles_list)
        actual_soc_df = get_actual_soc()
        soc_code_6 = soc_titles_df.iloc[max_similarity_index_list[0]].soc_6
        soc_code_6 = soc_code_6[0:6]+'0'
        soc_title = actual_soc_df.loc[actual_soc_df.soc_code_6 == soc_code_6]
        family = soc_title.iloc[0, 1]
        extended_family = soc_title.iloc[0, 3]
        soc_code_2 = soc_code_6[0:2]
        cousins = actual_soc_df.loc[actual_soc_df.soc_code_2 == soc_code_2]
        cousins = cousins.iloc[:, 1]
        cousins = cousins.rename(columns = {'soc_title_6': 'All occupations in the same extended family'})
        st.write('**Family:**', family)
        st.write('**Extended family:**', extended_family)
        st.table(cousins)
        st.write(f'**Here is how the demand for {family} varies across major metropolitan areas:**')
        
            
if __name__ == '__main__':
    main()