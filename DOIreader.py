# -*- coding: utf-8 -*-
"""
Created on Thu Jun  9 11:46:35 2022

@author: depriester
"""


import pandas as pd
import requests as req
import re
from unidecode import unidecode

def possible_abbrv(firstname):
    possible_set=[]
    split_name=re.split('\W+', firstname.rstrip('.'))
    firstletters=[parts[0] for parts in split_name]
    possible_set.append(''.join(firstletters))         
    possible_set.append('.'.join(firstletters) + '.')
    possible_set.append('-'.join(firstletters))
    possible_set.append('-'.join(firstletters) + '.')    
    possible_set.append('.-'.join(firstletters) + '.' )
    return possible_set

def format_parser(names, pattern):
# =============================================================================
#     Used for format specification for author names, e.g.:
#       - 'Lastname, Firstname'
#       - 'F. Lastname'
#       - 'Firstname LASTNAME'
# =============================================================================
    names_dict=dict()
    for i,key in enumerate(('lastname', 'firstname')):
        s=re.search(r'[\.\,\-,\s*]+', names[i])
        if s is None:
            abbrv=names[i][0].upper()
            abbrv_dot=abbrv + '.'
            sep=''
        else:
            sep=s.group() 
            name_split= names[i].rstrip('.').title().split(sep)
            abbrv=[namepart[0] for namepart in name_split]
            abbrv_dot=[namepart[0] + '.' for namepart in name_split]
            sep=sep.strip('.')
        names_dict[key]=names[i].lower()
        names_dict[key.capitalize()]=names[i].title()
        names_dict[key.upper()]=names[i].upper()
        names_dict[key[0].upper()]=sep.join(abbrv)
        names_dict[key[0].upper() + '.']=sep.join(abbrv_dot)
    s=re.search(r'[^a-zA-Z\.*]+', pattern)
    sep=s.group()
    keys=pattern.split(sep)
    seq=[]
    for key in keys:
        seq.append(names_dict[key])
    return sep.join(seq)

#%%
def doireader(doi_list, merge_similar_authors=False, format_author_names=None):
# =============================================================================
#     Parse a list a DOIs given in a text file and return a pandas DataFrame
# with the following entries:
#       - DOI
#       - document title
#       - journal name
#       - document type (journal article, book etc.)
#       - publishing date
#       - link to document
#       - full list of authors
#
# Arguments:
#       - doi_list (string): path to text file containing all the DOIs (one 
# per line)
#       - merge_similar_authors (default = False): try to merge ambiguous
# names (eg: 'Dupont Laurent' and 'Dupont L.')
#       - Format_author_names (default=None): if a string is given, the author
# names (firstname and lastname) will be formatted accordingly. For instance,
# if the author is Laurent Dupont, 
#   format_author_names='Lastname, Firstname'
# will produce 'Dupont, Laurent',  whereas 
#   format_author_names='F. LASTNAME'
# will produce L. DUPONT. If None (default), the names are given as a list
# ([<lastname>, <firstname>]). Note that this argument is case sensitive.
# 
# =============================================================================    
    print('Start Processing')
    print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
    dois_raw=pd.read_table(doi_list, header=None)
    dois=dois_raw.loc[:,0].unique()
    authors=['Author{:0>2d}'.format(k) for k in range(1,21)]
    fields=['title', 'journal', 'type', 'date', 'url']
    df=pd.DataFrame(columns=fields + authors, index=dois)
    family_list=[]
    given_list=[]
    
    for i,doi in enumerate(dois):
        
        # Ensure valid URL
        print('Fetching ' + doi + '...', end=' ')
        if doi.startswith('doi.org/'):
            doi_url='https://' + doi
        elif not doi.startswith(('http', 'https')):
            doi_url='https://doi.org/' + doi
        else:
            doi_url=doi
        
        # Get JSON data
        try:
            r = req.get(doi_url, headers={'Accept': 'application/json'})
            json=pd.json_normalize(r.json())
            entry=json.loc[0]
            
            # Get fields of interest
            authors=pd.DataFrame(entry['author'])
            title=entry['title']
            journal=entry['container-title']
            art_type=entry['type']
            date=entry['published-print.date-parts'][0]
            urls=pd.DataFrame(entry['link'])
            print('Done.')
            print('Title: ' + title)
            
            # Format journal
            journal_fix=journal.replace('&amp;','&')
            
            # Get valuable URL
            valid_urls=urls.loc[urls['content-type']=='application/pdf']
            if len(valid_urls):
                url=valid_urls.loc[0]['URL']
            else:
                url=doi_url
                
            # Format date
            if len(date)==3:
                fdate='{2:0>2}/{1:0>2}/{0}'.format(*date)
            elif len(date)==2:
                fdate='{1:0>2}/{0}'.format(*date)
            else:
                fdate='{}'.format(*date)
            
            # Concatenate data
            df.loc[doi,fields]=(title, journal_fix, art_type, fdate, url)
            for k,author in authors.iterrows():
                df.loc[doi,'Author{:0>2d}'.format(k+1)]=[author['family'], author['given']]
                family_list.append(author['family'])
                given_list.append(author['given'])
                
        except:
            # The DOI cannot be found
            msg='Error {}: '.format(r.status_code) +  r.reason
            print('\n >> ' + msg + '!')
            df.loc[doi,'title']=msg
                
        print('------------------')
    
    print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
    print('Cleaning up data')
    df.dropna(axis=1, how='all', inplace=True) # Remove empty columns (typically, author10 to author20)
    
    if merge_similar_authors:
        print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
        print('Merge duplicate authors')        
        # Try to merge duplicate authors, even if some entries use abbreviated notations        
        authorlist=pd.DataFrame({'familyname':family_list, 'firstname':given_list})
        strfilter=authorlist.firstname.str.match(r'[A-Z\.]{1,}\b')
        full_names = authorlist.loc[~strfilter]
        for j,full_name in full_names.iterrows():
            for column in df.iloc[:,len(fields):]:
                for doi,data in df.loc[:,column].iteritems():
                    if isinstance(data,  list):
                        familyname=unidecode(data[0])
                        fisrtname=unidecode(data[1])
                        if (familyname == unidecode(full_name['familyname'])) and  (fisrtname in possible_abbrv(full_name['firstname']) ):
                            df.loc[doi,column]=[full_name['familyname'], full_name['firstname']]
                            
    if format_author_names is not None:
        print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
        print('Format author names')        
        for column in df:
            if column.startswith('Author'):
                for doi,author in df.loc[:,column].iteritems():
                    if isinstance(author, list):
                        df.loc[doi,column]=format_parser(author,format_author_names)                           
                            
        
    print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
    print('Finished!')                              
    return df

#%%             
if __name__ == "__main__":
    df = doireader('dois.txt', merge_similar_authors=False)    
    df.to_excel('Bibliography.xlsx', freeze_panes=(1,0))
        

