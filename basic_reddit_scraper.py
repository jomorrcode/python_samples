# standard library imports
import codecs
import pathlib
import pandas as pd
from collections import deque
import dateutil
from datetime import datetime, timedelta
import numpy as np

# external imports
from psaw import PushshiftAPI
import praw



def reddit_object_to_dict(x):
    """
    Convert object returned by psaw/praw to a dictionary

    Useful columns added:
    * post_type ('submissions' or 'comments')
    * text instead of selftext/body for submissions/comments
    * full_id instead of id  - prepends the object type prefix to the id

    Parameters
    ----------
    x : Object
        a single result from a psaw/praw results generator

    Returns
    -------
    tmp : dict
        dictionary representation of psaw/praw result with additional useful columns added

    """

    if hasattr(x, '__dict__'):
        tmp = x.__dict__
        """
        # remove triple quotes to add call to upvote_ration
        if 'selftext' in tmp:
            #tmp.update({'upvote_ratio': x.upvote_ratio})
        """
        tmp.pop('_reddit', None)
        tmp.pop('_comments', None)
        tmp.pop('_comments_by_id', None)
        tmp.pop('comment_id', None)
        tmp['author'] = tmp['author'].name if tmp['author'] else None
        tmp['subreddit'] = tmp['subreddit'].display_name if tmp['subreddit'] else None
    else:
        tmp = x.d_

    # Submissions have 'title', comments do not
    if 'title' in tmp:
        tmp['full_id'] = "t3_" + tmp['id']
        # For submissions from ['deleted'] authors, there is no 'selftext' key
        if 'selftext' in tmp:
            tmp['text'] = tmp['selftext']
            tmp.pop('selftext', None)
        else:
            tmp['text'] = None
        tmp['post_type'] = 'submission'
    else:
        tmp['full_id'] = "t1_" + tmp['id']
        tmp['text'] = tmp['body']
        tmp.pop('body', None)
        tmp['post_type'] = 'comment'

    tmp['scraped_on'] = datetime.now().strftime("%Y-%m-%d")

    return tmp


def reddit_df_clean(df, columns_to_keep=None):
    """
    Clean up reddint dataframe

    For cleaning up a Pandas Dataframe of reddit data from psaw or praw for analysis or loading into a database

    * Drops duplicates based on id
    * Selects only specific columns
    * Makes the permalink a full URL (prepends https://reddit.com)
    * Cleans up missing values (nan, '', None)

    Parameters
    ----------
    df : pandas.DataFrame
        Pandas dataframe of comment or submissions from psaw or praw
    columns_to_keep : list
        Columns to add to the database

    Returns
    -------
    pandas.DataFrame
        Pandas dataframe of comment or submissions from psaw or praw

    """
    # Drop duplicate rows
    df.drop_duplicates(subset=['id'], inplace=True, ignore_index=True)

    if not columns_to_keep:
        # Columns wanted for smaller dataset
        columns_to_keep = ['author',
                           'author_flair_text',
                           'author_fullname',
                           'collapsed',
                           'collapsed_reason',
                           'controversiality',
                           'created_utc',
                           'domain',
                           'edited',
                           'full_id',
                           'id',
                           'is_self',
                           'is_submitter',
                           'link_id',
                           'locked',
                           'no_follow',
                           'num_comments',
                           'num_crossposts',
                           'over_18',
                           'parent_id',
                           'permalink',
                           'post_type',
                           'score',
                           'scraped_on',
                           'stickied',
                           'subreddit',
                           'text',
                           'title',
                           'total_awards_received',
                           'url']

    available_columns = set(df.columns.values)
    columns_to_add = list(set(columns_to_keep).difference(available_columns))
    for col in columns_to_add:
        df[col] = None

    df = df.loc[:, columns_to_keep]

    df['created_datetime_utc'] = df.created_utc.apply(lambda x: datetime.fromtimestamp(x).strftime("%Y-%m-%d %H:%M:%S"))


    # Add 'https://reddit.com' to permalink values such that the links are complete
    if 'permalink' in df.columns:
        df.loc[:, 'permalink'] = 'https://reddit.com' + df['permalink']

    # Convert NaN  and '' in object columns to None
    cols = sorted(df.columns)
    for col in cols:
        if df[col].dtype == 'object':
            df[col].replace({np.nan: None, '': None}, inplace=True)

    for col in ['collapsed', 'is_self', 'is_submitter', 'controversiality', 'over_18']:
        df[col] = df[col].apply(lambda x: True if x == 1 else False)

    for col in ['num_comments', 'num_crossposts']:
        df[col] = df[col].apply(lambda x: x if not x==np.nan else None)

    # Re-order columns alphabetically
    df.sort_index(axis=1, inplace=True)

    # Reset df index
    df.reset_index(inplace=True, drop=True)

    return df


def main():
    data_folder = "/nfs/scraped_data/raw_data/reddit_posts/"
    clean_folder = "/nfs/scraped_data/clean_data/reddit_posts/"

    api = PushshiftAPI(max_results_per_request=100)   # uses only Pushshift

    # list of subreddits to scrape

    '''
    sub_list = ['coronavirus', 'coronavirusca', 'coronavirusus', 'ncov', 'china_flu', 'coronavirusuk',
                'coronavirusdownunder', 'coronavirusrecession', 'coronavirusaustralia', 'coronavirusflorida',
                'coronavirus_ireland', 'cvnews', 'floridacoronavirus', 'coronavirusfos', 'canadacoronavirus',
                'coronavirus_2019_ncov', 'covid19', 'coronavirusnewyork', 'coronavirustx', 'coronaviruswa', 'covid2019',
                'coronavirusmichigan', 'coronavirusalabama', 'nyccoronavirus', 'coronavirusga', 'coronavirusillinois',
                'ccp_virus', 'coronaviruscanada', 'coronaviruscolorado', 'coronaviruslouisiana', 'coronavirusaz',
                'coronavirusne', 'covid19positive', 'coronavirus_ph', 'covid19_support', 'lockdownskepticism',
                ' coronaviruseu', 'coronavirus_sweden']
    '''

    #sub_list =['coronavirus', 'coronavirusca', 'coronavirusus', 'ncov', 'china_flu', 'coronavirusuk', 'coronavirusrecession', 'cvnews', 'coronavirus_2019_ncvo', 'covid19', 'covid2019', 'ccp_virus', 'covid19positive']

    sub_list = ['todayilearned', 'changemyview', 'unpopularopionion']

    # set dates yyyy,mm,dd
    after = int(datetime(2020, 1, 1).timestamp())  # after midnight, January 1 of the year to collect
    before = int(datetime(2020, 7, 1).timestamp())  # before midnight, January 1 the next year
    #limit = 10000
    #q='coronavirus, wuhan'

    print("scraping submissions", datetime.now())
    posts = list(api.search_submissions(
        after=after,
        before=before,
        subreddit=sub_list,
        # limit=limit
    ))

    all_posts = []
    print("processing submissions", datetime.now())
    for post in posts:
        post = reddit_object_to_dict(post)
        all_posts.append(post)

    print("scraping comments", datetime.now())
    posts = list(api.search_comments(
        after=after,
        before=before,
        subreddit=sub_list,
        # limit=limit
    ))

    print("processing comments", datetime.now())
    for post in posts:
        post = reddit_object_to_dict(post)
        all_posts.append(post)

    df = pd.DataFrame(all_posts)

    print("saving posts", datetime.now())
    print(df.shape)
    
    df.to_json(f"{data_folder}todayilearned_reddit_posts.json", orient='records', lines=True)
    df = reddit_df_clean(df)

    df.to_json(f"{clean_folder}clean_todayilearned_reddit_posts.json", orient='records', lines=True)


if __name__ == '__main__':
    main()
