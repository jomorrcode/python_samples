"""
A collection of twitter scraping functions for import into collection scripts

v0.1
John Morrow
14 May, 2020
"""

# standard imports
import pandas as pd
from datetime import datetime as dt, timedelta
import sys
from pathlib import Path
import subprocess
from io import StringIO
import os

# external imports
import twint



def keyword_scraper(name, start_date, end_date, query, output="tweets/", lang=None, hide=True, limit=None):
    """
    :param name: name for this scrape.  will be used as identifier for saved files
    :param start_date: earliest date to scrape.  string in format "yyyy-mm-dd"
    :param end_date:  exclusive date to stop scrape. string in format "yyyy-mm-dd"
    :param query: string of keywords to search.  separate terms with OR as spaces == AND
    :param output: folder to save output to.  default is "tweets/"
    :param lang: two letter language code to limit collection to that language.  default collects all tweets
    :param hide: change to False to have scraped data display to screen
    :param limit: pass in integer to limit scrape to that many tweets per day.  default is all tweets
    :return:
    """

    # initialize parameters
    start_dt = dt.strptime(start_date, "%Y-%m-%d")
    end_dt = dt.strptime(end_date, "%Y-%m-%d")
    if output[-1] != "/":
        output = output + '/'

    # create output folder if it doesn't exist
    Path(output).mkdir(parents=True, exist_ok=True)

    # intialize twint
    c = twint.Config()
    if hide:
        c.Hide_output = True
    if lang:
        c.Lang = lang
    if limit:
        c.Limit = limit

    c.Store_json = True
    c.Search = query

    cnt = 0  # counter for number of failed scrapes per day

    # main loop
    os.system('clear')
    while start_dt < end_dt:

        print(f"Scrape {name} begun at {dt.now()}")

        complete = False

        # set parameters for single day search
        c.Since = start_dt.strftime('%Y-%m-%d')
        c.Until = (start_dt + timedelta(days=1)).strftime('%Y-%m-%d')
        c.Output = f"{output}{name}_tweets_{c.Since}.json"
        c.Resume = f"{output}{name}_resume_{c.Since}"

        while not complete:
            try:
                print(f"Scraping {c.Since}")
                twint.run.Search(c)
                complete = True

            except Exception as e:
                print(f"Error: {e}. Resuming scrape")


        """
        The results of twitter scraping via twint can be unpredictable.
        This code attempts to test to see if either the correct number of tweets has been collected
        or if the scrape reached the last hour of the day being scraped      
        """
        # check if json file exists
        if not Path(f'{c.Output}').is_file():
            start_dt = start_dt + timedelta(days=1)
            print(f"No results returned for {c.Since}. Commencing ", start_dt)
            cnt = 0
            continue

        # check if the completed scrape returned the 'limit' number of tweets 
        if limit:
            cmd = f"wc -l {c.Output}".split(' ')
            returned_output = subprocess.check_output(cmd)
            ret = returned_output.decode("utf-8")
            num_tweets = int(ret.split(' ')[0])

            if num_tweets >= limit or cnt > 5:
                start_dt = start_dt + timedelta(days=1)
                print(f"Scrape complete. {num_tweets} collected. Commencing ", start_dt)
                cnt = 0

            else:
                cnt += 1
                print("Scrape incomplete.  Resuming.")
        else:

            cmd = ['tail', '-n', '1', f'{c.Output}']

            a = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            b = StringIO(a.communicate()[0].decode('utf-8'))

            

            print("Checking last tweet time...")

            df = pd.read_json(b, lines=True)
            if (df.iloc[0].time[:2] == "00") or (cnt > 5):
                start_dt = start_dt + timedelta(days=1)
                print("Scrape complete. End of day reached. Commencing ", start_dt)
                cnt=0

            else:
                cnt += 1
                print("Scrape incomplete.  Resuming.")

    print(f"Scrape {name} completed at {dt.now()}")


def user_tweets_scraper(user_id,start_date, end_date=None,hide=True, limit=None):
    """
    :param user_id: twitter user_id to scrape
    :param start_date: earliest date to scrape.  string in format "yyyy-mm-dd"
    :param end_date:  exclusive date to stop scrape. if None, scrape until today
    :param hide: change to False to have scraped data display to screen
    :param limit: pass in integer to limit scrape to that many tweets per day.  default is all tweets
    :return: dataframe of user's tweets
    """

    c = twint.Config()
    c.User_id = user_id
    c.Pandas_clean = True
    c.Pandas = True
    c.Since = start_date
    if end_date:
        c.Until = end_date
    if hide:
        c.Hide_output=True
    
    twint.run.Search(c)

    return twint.storage.panda.Tweets_df


def followers_scraper():
    pass


def user_profile_scraper():
    pass

def clean_tweets(df):
    """
    :param df: dataframe of tweets
    :return: cleaned dataframe for analysis
    """
    cols_to_drop = ["retweet_date", "retweet","translate", "trans_src", "trans_dest", "retweet_id", "user_rt",
                        "user_rt_id", "source", "geo", "near", "search", "user_id_str", "day", "hour", "timezone",
                    "date", "time"]
    df.drop(columns=cols_to_drop, inplace=True, errors='ignore')
        
    df.replace({'':None}, inplace=True)
    df['video'] = df.video.astype('bool')

    df.rename(columns={'created_at':'created_at_utc'})

    return df