import pandas as pd
from psaw import PushshiftAPI
import pickle
import codecs


api = PushshiftAPI()

def reddit_author_timeofday_distribution(author, api=api, after=1577836800):
    # Search comments
    gen1 = api.search_comments(author=author, select=['created_utc'], aggs='created_utc',after=after, frequency='hour',limit=0, metadata=False)
    data = list(gen1)[0]['created_utc']
    
    # Search submissions
    gen2 = api.search_submissions(author=author, select=['created_utc'], aggs='created_utc',after=after, frequency='hour',limit=0, metadata=False)
    data2 = list(gen2)[0]['created_utc']
    # Append submissions data to comments data
    data.extend(data2)
    df = pd.DataFrame(data)
    
    # If there's data, parse the dates, aggregate and return
    if df.shape[0]>0:
        df['datetime'] = pd.to_datetime(df['key'],unit='s')
        df['hour'] = df['datetime'].dt.hour
        hour_counts = df.groupby('hour').agg(sum)
        ret = hour_counts['doc_count'].reset_index()
        ret['author'] = author
        return ret.pivot(index='author',columns='hour',values='doc_count')
    
    # If no data, return None
    else:
        return None

def save_freq(temp_df):
    with codecs.open("/nfs/scraped_data/clean_data/reddit_posts/users_agg_freq.json", 'a', encoding='utf-8') as fout:
        temp_df.to_json(fout, orient='records', lines=True)
        fout.write('\n')


def main():
    with open("/nfs/scraped_data/clean_data/reddit_posts/reddit_users_list.pkl", "rb") as fin:
        authors = pickle.load(fin)

    start_chunk = 0
    end_chunk = 10

    while start_chunk < len(authors):
        temp_df=pd.DataFrame()
        print(f"Getting authors {start_chunk} to {end_chunk}.")
        for author in authors[start_chunk:end_chunk]:    
            try:
                author = author.lower()
                freq = reddit_author_timeofday_distribution(author)
                temp_df = pd.concat([temp_df, freq])
            except KeyError as e:
                print(author, e)

        temp_df.reset_index(inplace=True)
        save_freq(temp_df)
        print("Last author saved:", end_chunk)
        start_chunk = end_chunk
        end_chunk += 10



if __name__ == "__main__":
    main()