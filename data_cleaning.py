#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This file includes code to clean the job vacancy headers scraped from the online
job portal, Indeed. It drops the duplicate vacancies - based on their ids - and
re-attampts to scrape the missing job vacancy headers i.e. title field in
particular from the job vacancy descriptions.      
"""
import pymongo
import pandas as pd
import numpy as np
import re
import os
import scraping
from nltk.corpus import stopwords
from nltk import word_tokenize

os.chdir('/Users/flatironschol/FIS-Projects/Capstone/FIS-capstone-project')
"""
The following code was run only once to drop duplicate vacancies that already
existed in the Indeed-job-vacancies database. 
"""
# myclient = pymongo.MongoClient('mongodb://127.0.0.1:27017/')
# myclient.admin.command('copydb', 
#                       fromdb = 'Indeed-job-vacancies', 
#                       todb = 'Backup-Indeed-job-vacancies-1-17-20')  
# myclient.drop_database('Indeed-job-vacancies')
# mydb = myclient['Indeed-job-vacancies']
# mycollection = mydb['Job-headings']
# mycollection.create_index([('jk', pymongo.ASCENDING)], unique=True)
#my_backup_db = myclient['Backup-1-9-20-Indeed-job-vacancies']
#my_backup_collection = my_backup_db['Job-headings']
#for doc in my_backup_collection.find({}):
#    try:
#        mycollection.insert_one(doc)
#    except:
#        print('DUPLICATE VACANCY')


"""
The following function scrapes job vacancy titles from vacancy descriptions
for missing values. Originally, titles have been scraped from the vacancy headers.   
"""
def scrape_missing_titles():
    myclient = pymongo.MongoClient('mongodb://127.0.0.1:27017/')
    mydb = myclient['Indeed-job-vacancies']
    mycollection = mydb['Job-headings']
    jk_list = list(mycollection.find({'title': None}, {'jk': 1}))
    title_list = []
    for item in jk_list:
        jk = item['jk']
        soup = scraping.get_soup(type = 'desc', jk = jk)
        if soup != None:
            title = soup.find('meta', attrs = {'id': 'indeed-share-message'})
            if title != None:
                title = title['content']
            else:
                title = soup.find('p', attrs = {'class': 'job-title'})
                if title != None:
                    title = title.text
                else:
                    title = soup.find('title')
                    if title != None:
                        title = title.text
                    else:
                        print('ERROR EXTRACTING THE TITLE USING VARIOUS TAG')
            if title != None:
                title_dict = {'jk': jk, 'title': title}
                title_list.append(title_dict)
                mycollection.update_one({'jk': jk}, {'$set': {'title': title}})
        else:
            print('ERROR WITH GETTING THE SOUP OBJECT')       
    return title_list

# updated_nas = scrape_missing_titles()  

"""
The following code was run only once to add date and MSA code to the existing
vacancies in the database
"""
# myclient = pymongo.MongoClient('mongodb://127.0.0.1:27017/')
# mydb = myclient['Indeed-job-vacancies']
# mycollection = mydb['Job-headings']
# mycollection.update_many({'date': None}, {'$set': {'date': '01-06-20'}})
# mycollection.update_many({'msa': None}, {'$set': {'msa': '47900'}})

"""
The following code was run only once to put the newly scraped vacancies to the
local database
"""
# myclient = pymongo.MongoClient('mongodb://127.0.0.1:27017/')
# mydb = myclient['Indeed-job-vacancies']
# mycollection = mydb['Job-headings']
# df = pd.read_csv('indeed_df.csv')
# df = df.drop(columns = ['Unnamed: 0', '_id'])
# post = df.to_dict(orient = 'records')
# duplicate = 0
# for p in post:
#     try:
#         mycollection.insert_one(p)
#     except:
#         duplicate += 1

"""
The following creates a list of tokens to be dropped in addition to the usual
stop words.
"""
def create_stop_words():
    stopwords_list = stopwords.words('english')
    stopwords_list.append('and')
    with open('../data/adjectives.txt', 'r') as file:
        adjective_list = file.readlines()
    adjective_list = [re.sub(r'^\s+|\s+$|^\ufeff', '', adjective.lower()) for adjective in adjective_list]
    stopwords_list.extend(adjective_list)
    df = pd.read_excel('../data/list2_Sep_2018.xls', skiprows = 2, header = 0)
    location_list = [str(location).split(',')[0].replace('-', ' ').lower() for location in df['CBSA Title']]
    location_list.extend([str(location).lower() for location in df['Principal City Name']])
    location_list = list(set(location_list))
    location_list = [location for location in location_list if len(location.split(' ')) == 1]
    stopwords_list.extend(location_list)
    return stopwords_list

def substitute_words(tokenized_title_list):
    # This function makes word-by-word substitutions (See: word_substitutes.csv)
    # For each row, everything in the second to last column will be substituted with the first column
    # Example, one row reads "assistant | assistants | asst | asst. | assts"
    # If any word is "assistants", "asst." or "assts" is found, it will be substituted with simply "assistant"    
    df = pd.read_csv('../data/word_substitutes.csv', header = None, encoding='cp437')
    alternative_tokens = np.array(df.iloc[:, 1:5])
    base_tokens = np.array(df.iloc[:, 0])
    substituted_tokenized_title_list = []
    for tokenized_title in tokenized_title_list:
        substituted_tokenized_title = []
        for token in tokenized_title:   
            i = np.where(alternative_tokens == token)[0]
            new_token = base_tokens[i]
            if new_token.size == 0:
                substituted_tokenized_title.append(token)
            else:
                substituted_tokenized_title.extend(new_token)
        substituted_tokenized_title_list.append(substituted_tokenized_title)
    return substituted_tokenized_title_list

def stop_tokenized_titles(tokenized_titles_list, stopwords_list):
    stopped_tokenized_titles_list = []
    for tokenized_title in tokenized_titles_list:
        stopped_tokenized_title = []
        for token in tokenized_title:
            token_lower = token.lower()
            if token_lower not in stopwords_list:
                pattern = r'[a-z]{3,}'
                stopped_tokenized_title.extend(re.findall(pattern, token_lower))
        stopped_tokenized_titles_list.append(stopped_tokenized_title)
    return stopped_tokenized_titles_list
    
def clean_soc_titles():
    soc_df = pd.read_excel('../data/soc_2010_direct_match_title_file.xls', skiprows = 6)
    soc_df = soc_df[['2010 SOC Direct Match Title', '2010 SOC Code']] 
    onet_df = pd.read_csv('../data/Alternate Titles.txt', sep = '\t')
    onet_df['soc_2'] = [code.split('-')[0] for code in onet_df['O*NET-SOC Code']]
    onet_df['soc_6'] = [code.split('.')[0] for code in onet_df['O*NET-SOC Code']]
    onet_df = onet_df.rename(columns = {'Alternate Title':'title', '2010 SOC Code':'soc_6'})
    soc_df = soc_df.rename(columns = {'2010 SOC Direct Match Title':'title', '2010 SOC Code':'soc_6'})
    soc_df = pd.concat([soc_df, onet_df], join = 'inner', ignore_index = True)
    soc_duplicated_titles = soc_df[soc_df.duplicated(subset = ['title'], keep = False)]
    soc_duplicated_titles = soc_duplicated_titles[~soc_duplicated_titles.duplicated(keep = False)]
    soc_df = soc_df.drop(soc_duplicated_titles.index)
    soc_df = soc_df.drop_duplicates(keep = 'first')
    return soc_df