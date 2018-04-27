# socialreaper
[![](https://readthedocs.org/projects/socialreaper/badge/?version=latest)](https://socialreaper.readthedocs.io)
[![Downloads](http://pepy.tech/badge/socialreaper)](http://pepy.tech/count/socialreaper)
[![Gitter](https://img.shields.io/gitter/room/socialreaper/socialreaper.svg)](https://gitter.im/socialreaper)

`socialreaper` is a Python 3.6+ library that scrapes Facebook, Twitter, Reddit, Youtube, Pinterest, and Tumblr. 

[Documentation](https://socialreaper.readthedocs.io)

Not a programmer? [Try the GUI](https://github.com/scriptsmith/reaper)

# Install
```
pip3 install socialreaper
```

# Examples
For version 0.3.0 only

```
pip3 install socialreaper==0.3.0
```

## Facebook
Get the comments from McDonalds' 1000 most recent posts
```python
from socialreaper import Facebook

fbk = Facebook("api_key")

comments = fbk.page_posts_comments("mcdonalds", post_count=1000, 
    comment_count=100000)

for comment in comments:
    print(comment['message'])
```

## Twitter
Save the 500 most recent tweets from the user `@realDonaldTrump` to a csv file
```python
from socialreaper import Twitter
from socialreaper.tools import to_csv

twt = Twitter(app_key="xxx", app_secret="xxx", oauth_token="xxx", 
    oauth_token_secret="xxx")
    
tweets = twt.user("realDonaldTrump", count=500, exclude_replies=True, 
    include_retweets=False)
    
to_csv(list(tweets), filename='trump.csv')

```

## Reddit
Get the top 10 comments from the top 50 threads of all time on reddit
```python
from socialreaper import Reddit
from socialreaper.tools import flatten

rdt = Reddit("xxx", "xxx")
 
comments = rdt.subreddit_thread_comments("all", thread_count=50, 
    comment_count=500, thread_order="top", comment_order="top", 
    search_time_period="all")
    
# Convert nested dictionary into flat dictionary
comments = [flatten(comment) for comment in comments]

# Sort by comment score
comments = sorted(comments, key=lambda k: k['data.score'], reverse=True)

# Print the top 10
for comment in comments[:9]:
    print("###\nUser: {}\nScore: {}\nComment: {}\n".format(comment['data.author'], comment['data.score'], comment['data.body']))
```

## Youtube
Get the comments containing the strings `prize`, `giveaway` from 
youtube channel `mkbhd`'s videos
```python
from socialreaper import Youtube

ytb = Youtube("api_key")

channel_id = ytb.api.guess_channel_id("mkbhd")[0]['id']

comments = ytb.channel_video_comments(channel_id, video_count=500, 
    comment_count=100000, comment_text=["prize", "giveaway"], 
    comment_format="plainText")
    
for comment in comments:
    print(comment)
```

# CSV export
You can export a list of dictionaries using socialreaper's `CSV` class

```python
from socialreaper import Facebook
from socialreaper.tools import CSV

fbk = Facebook("api_key")
posts = list(fbk.page_posts("mcdonalds"))
CSV(posts, file_name='mcdonalds.csv')
