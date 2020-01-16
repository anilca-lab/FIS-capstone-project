#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This file includes code to scrape job vacancy data from the online
job portal, Indeed. It does two types of scraping:
    1 - Job headers including job title, job key, company name data for a given location
    2 - The job description for a given job key
The code uses BeautifulSoup and regex to extract the relevant data from the html pages.
The scraped data is stored in MongoDB.
"""
import requests
from bs4 import BeautifulSoup
import math
import pandas as pd
import re
import pymongo
#import os

#os.chdir('/Users/flatironschol/FIS-Projects/Capstone/FIS-capstone-project')

def create_loc_list():
    """
    This function creates a list of counties of the ten largest metropolitan areas
    using the Census Bureau CBSA codes.
    """
    areas_df = pd.read_excel('area_definitions_m2018.xlsx')
    #metro_df = areas_df.loc[areas_df['May 2018 MSA code '].isin([35620, 31080, 16980, 19100, 26420, 33100, 37980, 12060, 71650, 47900])]
    metro_df = areas_df.loc[areas_df['May 2018 MSA code '].isin([71650])]
    county_list = list(metro_df['County name (or Township name for the New England states)'] + ' ' + metro_df['State abbreviation'])
    code_list = metro_df['May 2018 MSA code ']
    return county_list, code_list

def get_soup(type = 'header', loc = 'District of Columbia DC', page_no = 1, jk = None):
    """
    This function return a BeautifulSoup object of: 
        1 - Job vacancy headers for a given location and page number (type = 'header')
            header data includes job id, job title, company id, and company name    
        2 - Job description for a given job id (type = 'desc')
    """
    f = open('log.txt', 'a')
    if type == 'header':
        loc = loc.replace('\s', '+')
        url = 'https://www.indeed.com/jobs'
        parameters = {'l': loc, 'radius': 0}
        header = {'User-Agent' : 'override this bad boy!'}
        if page_no > 1:
            parameters['start'] = 10 * (page_no - 1)     
        response = requests.get(url, headers = header, params = parameters)
        if response.status_code == 200:
            f.write('HEADER EXTRACTED FOR PAGE ' + str(page_no) + '\n')
            f.close()
            return BeautifulSoup(response.content, 'html.parser')
        else:
            f.write('ERROR WITH THE REQUEST: ' + str(response.status_code) + '\n')
            f.close()
            return None
    elif type == 'desc':
        url = 'https://www.indeed.com/viewjob?jk=' + jk
        header = {'User-Agent' : 'override this bad boy!'}
        response = requests.get(url, headers = header)
        if response.status_code == 200:
            f.write('DESCRIPTION EXTRACTED FOR PAGE ' + jk + '\n')
            f.close()
            return BeautifulSoup(response.content, 'html.parser')
        else:
            f.write('ERROR WITH THE REQUEST: ' + str(response.status_code) + '\n')
            f.close()
            return None

def scrape_no_of_jobs(soup):
    """
    This function scrapes total number of jobs for a given BeautifulSoup
    object including Indeed job vacancies for a given location and page number.
    """
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
                f = open('log.txt', 'a')
                f.write('ERROR WITH NUMBER OF JOBS\n')
                f.close()
    return no_of_jobs

def scrape_job_headers(soup):
    """
    This function scrapes job and company keys as well as job
    title and company name for each job as a single string 
    from a BeautifulSoup object of Indeed job vacancies for a location 
    and page number.
    """
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

def clean_job_headers(jobs_list):
    """
    This function extracts job and company keys as well as job
    title and company name for each job given as a string.
    """
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

def scrape_job_descriptions(clean_job_header_list):
    """
    DO NOT USE THIS FUNCTION---
    This function scrapes job descriptions for a given list of job ids.
    """
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
    """
    This is the main function which brings together the scraping-cleaning functions
    from above. The output are the job headers and descriptions recorded in 
    MongoDB/Amazon Document DB.
    """
    myclient = pymongo.MongoClient('mongodb://anilca:occupational2020@docdb-2020-01-15-20-21-28.cluster-cwumlwnktm8n.us-east-1.docdb.amazonaws.com:27017/?ssl=true&ssl_ca_certs=rds-combined-ca-bundle.pem&replicaSet=rs0')
    mydb = myclient['Indeed-job-vacancies']
    mycollection = mydb['Job-headings']
    result = mycollection.create_index([('jk', pymongo.ASCENDING)], unique=True)
    county_list, code_list = create_loc_list()     
    for county, code in zip(county_list, code_list):
        f = open('log.txt', 'a')
        f.write('SCRAPING JOB HEADERS FOR ' + county + '\n')
        f.close()
        pages_to_scrape = True
        page_no = 1
        no_of_pages = 1
        clean_job_header_list = []
        while pages_to_scrape:
            soup = get_soup(type = 'header', loc = county, page_no = page_no)
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
                        pages_to_scrape = False
                page_no += 1
                clean_job_header_list.extend(clean_job_headers(job_header_list))
            else:
                f = open('log.txt', 'a')
                f.write('ERROR IN GETTING THE SOUP OBJECT\n')
                f.close()
        if len(clean_job_header_list) > 0:
            for job_header in clean_job_header_list:
                try:
                    mycollection.insert_one(job_header)
                except:
                    f = open('log.txt', 'a')
                    f.write('DUPLICATE VACANCY\n')
                    f.close()
            mycollection.update_many({'msa': None}, {'$set': {'msa': code}})
            mycollection.update_many({'county': None}, {'$set': {'county': county}})
    mycollection.update_many({'date': None}, {'$set': {'date': '01-15-20'}})
    print('DATA COLLECTION COMPLETED')