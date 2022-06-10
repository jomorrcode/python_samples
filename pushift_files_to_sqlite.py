"""
v.0.1
April 20, 2022

Processing Pushshift Monthly Archive Files into SQLite Database

Pushshift archives its Reddit data in very large monthly compressed files (generally in .zst format).
This script contains functions to iterate over those files, and save select fields to an sqlite database
for use in analysis.  Note: These files are very large.  Proceed with caution.

The database is setup with 3 tables:  users, subreddits, submissions. Comments will be added later.

For now the users and subreddits tables are mere placeholders, holding only the name and id of each.
If desired, these tables can later be enriched via the Reddit API, and eventually functions will be added
to facilitate this enrichment.

This is very much an MVP and a work in progress
"""

import sqlite3
import json
from datetime import datetime
import traceback
from glob import glob

import zstandard

""" DB FUNCTIONS """


def get_db_connection(db_file: str):
    """
    Connect to DB

    :param db_file - a string filepath to the sqlite db file
    
    :return:
        sqlite_connection and cursor
    """

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    return conn, cursor


def insert_users(cursor, users):
    cursor.executemany("INSERT INTO users (author) VALUES (?) ON CONFLICT (author) DO NOTHING", users)


def insert_subreddits(cursor, subreddits):
    cursor.executemany("INSERT INTO subreddits (subreddit) VALUES (?) ON CONFLICT (subreddit) DO NOTHING", subreddits)


def insert_submissions(cursor, submissions):
    cursor.executemany("""
        INSERT INTO submissions 
        VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT (record_id) DO UPDATE SET
            score = excluded.score,
            num_comments = excluded.num_comments
    """, submissions)


""" EXTRACT TRANSFORM LOAD FUNCTIONS """


def read_lines_zst(file_name):
    # this zst reader courtesy of https://github.com/Watchful1/PushshiftDumps

    with open(file_name, 'rb') as file_handle:
        buffer = ''
        reader = zstandard.ZstdDecompressor(max_window_size=2 ** 31).stream_reader(file_handle)
        while True:
            chunk = reader.read(2 ** 27).decode()
            if not chunk:
                break
            lines = (buffer + chunk).split("\n")

            for line in lines[:-1]:
                # yield line, file_handle.tell()
                yield line

            buffer = lines[-1]
        reader.close()


def data_cleaning(post: dict):
    """
    Functionality to clean up data and pass back only desired fields

    :param post: dict  content and metadata of a reddit post

    :return:
        tuple of fields for insertion into database
    """
    unwanted_authors = ['[deleted]', '[removed]', 'automoderator']

    # skip posts from undesirable authors or posts to personal subreddits
    if (post['author'] in unwanted_authors) or (post['subreddit_name_prefixed'].startswith('u/')):
        return None

    # replace empty string with placeholder for posts with no body content
    if post['selftext'] == '':
        post['selftext'] = "[NO TEXT]"

    # only a subset of the fields are being saved to the db
    # adjust the table schema and add fields here if desired
    author = post['author'].lower().strip()

    if post['author_flair_text']:
        author_flair_text = post['author_flair_text'].lower().strip()
    else:
        author_flair_text = "none"

    if post['link_flair_text']:
        post_flair_text = post['link_flair_text'].lower().strip()
    else:
        post_flair_text = "none"

    created_utc = post['created_utc']
    reddit_id = f"t3_{post['id']}"
    num_comments = post['num_comments']
    nsfw = post['over_18']
    score = post['score']
    text = post['selftext']
    subreddit = post['subreddit'].lower().strip()
    title = post['title']
    total_awards_received = post['total_awards_received']

    return (author, author_flair_text, post_flair_text, created_utc, reddit_id, num_comments,
            nsfw, score, text, subreddit, title, total_awards_received)


def etl(conn, cursor, archive_file):
    """
    Iterate over the compressed archive file, saving select data from each post to the database

    :param conn: sqlite connection object
    :param cursor: sqlite cursor object
    :param archive_file: filepath to pushshift monthly archive file

    :return:
        integer counts of posts processed and saved to database
    """
    post_count = 0
    saved_count = 0

    submissions_list = []
    users_set = set()
    subreddits_set = set()

    #start = datetime.now()

    for line in read_lines_zst(archive_file):

        post = data_cleaning(json.loads(line))

        # skip this line if rejected by data cleaning function
        if not post:
            continue

        post_count += 1

        # add author from index 0 of the cleaned tuple to the users set
        users_set.add((post[0],))

        # add subreddit from index 9 of the cleaned tuple to the subreddit set
        subreddits_set.add((post[9],))

        # add the cleaned tuple to the list of submissions
        submissions_list.append(post)

        # check if enough posts have been processed to insert in bulk
        if len(submissions_list) % 100000 == 0:

            # noinspection PyBroadException
            try:

                insert_users(cursor, users_set)
                insert_subreddits(cursor, subreddits_set)
                insert_submissions(cursor, submissions_list)

                conn.commit()

                saved_count += len(submissions_list)

                #print(f"Saved {post_count} posts", (datetime.now() - start).total_seconds())


            except Exception:
                print("Error inserting records")
                traceback.print_exc()

            submissions_list = []
            users_set = set()
            subreddits_set = set()

            #start = datetime.now()



    return post_count, saved_count


def main():
    # setup database & archive file
    # TODO migrate to proper CLI for user input
    # TODO add logging
    # for MVP, archive locations are just hard coded - change as required
    start_time = datetime.now()

    archive_file_folder = "D:/Data/Pushshift_Dumps/submissions_01-2020_06-2021/"
    archive_files = glob(f"{archive_file_folder}*.zst")

    db_file = input("Database file: ")

    conn, cursor = get_db_connection(db_file)

    # be careful with iterating over a folder full of these files!!!
    # the submission files can run to 20M+ rows and comments files ten times that
    # I suggest just doing a couple at a time

    for file in archive_files[0:1]: # use one for debugging
        # extract data from file, transform, and load into db
        print(f"Processing {file}...")
        post_count, saved_count = etl(conn, cursor, file)

        print(f"""
        {file} processed.
        {post_count} posts processed.
        {saved_count} posts inserted into database.""")
        

    print(f"Time Elapsed: {((datetime.now() - start_time).total_seconds())/60} minutes")
    print("Exiting...")


if __name__ == '__main__':
    main()
