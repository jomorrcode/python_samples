"""

Sqlite3 database creation for the pushshift to sqlite utilitu module

22 April, 2022
"""

import sqlite3

""" DB SCHEMAS """


def get_schemas():
    """
    Text schemas for sqlite tables

    :return:
        strings containing schema for the db tables
    """

    users_schema = """
        author TEXT PRIMARY KEY,
        reddit_user_id TEXT,
        account_created_utc INTEGER,
        comment_karma INTEGER,
        submission_karma INTEGER,
        total_karma INTEGER,
        verified_email INTEGER,
        icon_image_url TEXT
    """

    subreddits_schema = """
        subreddit TEXT PRIMARY KEY,
        description TEXT,
        public_description TEXT,
        subreddit_created_utc INTEGER,
        subscribers INTEGER,
        nsfw INTEGER
    """

    submissions_schema = """
        record_id INTEGER PRIMARY KEY,
        author TEXT,
        author_flair_text TEXT,
        post_flair_text TEXT,
        created_utc INTEGER,
        reddit_id TEXT,
        num_comments INTEGER,
        nsfw TEXT,
        score INTEGER,
        text TEXT,
        subreddit TEXT,
        title TEXT,
        total_awards_received INTEGER,

        FOREIGN KEY (author) REFERENCES users (author),
        FOREIGN KEY (subreddit) REFERENCES subreddits (subreddit)
    """

    return users_schema, subreddits_schema, submissions_schema


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


def create_tables(cursor):
    """
    Create db tables if necessary

    :param cursor: sqlite cursor instance

    :return:
        None
    """
    users_schema, subreddits_schema, submissions_schema = get_schemas()

    cursor.execute(f"CREATE TABLE IF NOT EXISTS users ({users_schema})")
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_c_karma ON users(comment_karma)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_s_karma ON users(submission_karma)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_t_karma ON users(total_karma)')

    cursor.execute(f"CREATE TABLE IF NOT EXISTS subreddits ({subreddits_schema})")
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_subscribers ON subreddits(subscribers)')

    cursor.execute(f"CREATE TABLE IF NOT EXISTS submissions ({submissions_schema})")
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_score ON submissions(score)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_n_com ON submissions(num_comments)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sub ON submissions(subreddit)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_date ON submissions(created_utc)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_author ON submissions(author)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_auth_sub ON submissions(author, subreddit)')


def main():
    print("Enter filepath for sqlite db file: (i.e. F:/Data/my_db.db)")
    db_file = input("DB File: ")

    conn, cursor = get_db_connection(db_file)

    # create tables if necessary
    create_tables(cursor)
    conn.commit()


if __name__ == '__main__':
    main()
