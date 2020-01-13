#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 25 14:22:23 2019
The following code scrapes job postings from Indeed. 
@author: anilca@gmail.com
"""
from bs4 import BeautifulSoup
import requests
import math
import pandas as pd
import re
import pymongo

# This function creates a list of DC metropolitan area locations using the Census
# Bureau definitions
def create_loc_list(): 
    filedir = '/Users/flatironschol/FIS-Projects/Capstone/data/'
    areas_df = pd.read_excel(filedir + 'area_definitions_m2018.xlsx')
    dcmetro_df = areas_df.loc[areas_df['May 2018 MSA code '] == 47900]
    dcmetro_list = list(dcmetro_df['County name (or Township name for the New England states)'] + ' ' + dcmetro_df['State abbreviation'])
    return dcmetro_list

# This function return a BeautifulSoup object of: 
# a) job vacancy headers for a given location and page number (type = 'header')
#    header data includes job id, job title, company id, and company name    
# b) job description for a given job id (type = 'desc')
def get_soup(type = 'header', loc = 'District of Columbia DC', page_no = 1, jk = None):
    if type == 'header':
        loc = loc.replace('\s', '+')
        url = 'https://www.indeed.com/jobs'
        parameters = {'l': loc, 'radius': 0}
        header = {'User-Agent' : 'override this bad boy!'}
        if page_no > 1:
            parameters['start'] = 10 * (page_no - 1)     
        response = requests.get(url, headers = header, params = parameters)
        if response.status_code == 200:
            print('HEADER EXTRACTED FOR PAGE ' + str(page_no))
            return BeautifulSoup(response.content, 'html.parser')
        else:
            print('ERROR WITH THE REQUEST: ' + str(response.status_code))
            return None
    elif type == 'desc':
        url = 'https://www.indeed.com/viewjob?jk=' + jk
        header = {'User-Agent' : 'override this bad boy!'}
        response = requests.get(url, headers = header)
        if response.status_code == 200:
            print('DESCRIPTION EXTRACTED FOR ' + jk)
            return BeautifulSoup(response.content, 'html.parser')
        else:
            print('ERROR WITH THE REQUEST: ' + str(response.status_code))
            return None

# This function scrapes total number of jobs for a given BeautifulSoup
# object of Indeed job vacancies given a location
def scrape_no_of_jobs(soup):     
    no_of_jobs = 0
    count = 0  
    for meta in soup.find_all('meta'):
        if (meta.get('name', None) == 'description') & (count == 0):
            count += 1
            content = meta.get('content', None)
            content = content.split(' ')[0]
            try:
                no_of_jobs = int(content.replace(',', ''))
            except:
                print('ERROR WITH NUMBER OF JOBS')
    return no_of_jobs

# This function scrapes job and company keys as well as job
# title and company name for each job from a BeautifulSoup
# object of Indeed job vacancies given a location
def scrape_job_headers(soup):
    jobs_list = []
    for script in soup.find_all('script'):
        if script.get('type', None) == 'text/javascript':
            for line in script:
                line_str = str(line)
                if 'jobmap' in line_str:
                    divided_line = re.split(r';\n', line_str)
                    for cell in divided_line:
                        if 'jobmap[' in cell:
                            jobs_list.append(cell)
    return jobs_list

# This function extracts job and company keys as well as job
# title and company name for each job given in html format
def clean_job_headers(jobs_list):
    job_keys_list = []
    for job in jobs_list:
        job_keys_dict = {} 
        job_keys = job.split('{')[1].replace('}', '')
        job_keys = re.split("(?<='),(?=[a-z])", job_keys)
        for key in job_keys:
            splitted_key = key.split(':')
            if len(splitted_key) == 2:
                job_keys_dict[splitted_key[0]] = splitted_key[1].replace('\'', '')
            elif len(splitted_key) == 3:
                job_keys_dict[splitted_key[0]] = splitted_key[1].replace('\'', '') + ' ' + splitted_key[2].replace('\'', '') 
        job_keys_list.append(job_keys_dict)
    return job_keys_list

# This function scrapes job descriptions for a given list of job ids
def scrape_job_descriptions(clean_job_header_list):
    job_desc_list = []
    for job in clean_job_header_list:
        soup = get_soup(type = 'desc', jk = job['jk'])
        if soup != None:
            print('DESCRIPTION EXTRACTED FOR ' + job['jk'])
            job_desc = soup.find('div', attrs = {'id': 'jobDescriptionText'})
            job_desc_dict = {'jk': job['jk'], 'job description': str(job_desc)}
            job_desc_list.append(job_desc_dict)
        else:
            print('JOB DESCRIPTION NOT FOUND')
    return job_desc_list

def scrape_job_vacancies():
    myclient = pymongo.MongoClient('mongodb://127.0.0.1:27017/')
    mydb = myclient['Indeed-job-vacancies']
    mycollection = mydb['Job-headings']
    result = mycollection.create_index([('jk', pymongo.ASCENDING)], unique=True)
    loc_list = create_loc_list()     
    for loc in loc_list:
        print('SCRAPING JOB HEADERS FOR ' + loc)
        pages_to_scrape = True
        page_no = 1
        no_of_pages = 1
        clean_job_header_list = []
        while pages_to_scrape:
            soup = get_soup(type = 'header', loc = loc, page_no = page_no)
            if soup != None:
                job_header_list = []
                if page_no == 1:
                    no_of_jobs = scrape_no_of_jobs(soup)
                    job_header_list = scrape_job_headers(soup)
                    if no_of_jobs == 0:
                        pages_to_scrape = False
                    else:
                        no_of_pages = math.ceil(no_of_jobs / len(job_header_list))
                else:
                    job_header_list = scrape_job_headers(soup)
                    if page_no == no_of_pages:
#                   if page_no == 2:
                        pages_to_scrape = False
                page_no += 1
                clean_job_header_list.extend(clean_job_headers(job_header_list))
            else:
                print('ERROR IN GETTING THE SOUP OBJECT')
        if len(clean_job_header_list) > 0:
            try:
                mycollection.insert_many(clean_job_header_list)
            except:
                print('DUPLICATE VACANCIES')