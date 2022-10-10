# TwitterScoreSystem

## Formula for calculating score
### score 5 = account age > 3650 days and tweets < 10000 and followers < 2000 and ratio of followers to following > 1.2
### and ratio of tweets / retweets in last 1000 tweets > 0.75
### score 4 = account age > 365 * 5 days and tweets < 15000 and followers < 2000 and ratio of followers to following > 1.2
### and ratio of tweets / retweets in last 1000 tweets > 0.75
### score 3 = account age > 365 * 3 days and tweets < 30000 and followers < 3000 and ratio of followers to following > 1
### and ratio of tweets / retweets in last 1000 tweets > 0.75
### score 2 = account age > 365 * 2 days and tweets < 7000 and followers < 2000 and ratio of followers to following > 1
### and ratio of tweets / retweets in last 1000 tweets > 0.75
### score 1 = account age > 365 days and tweets < 3000 and followers < 2000 and ratio of followers to following > 1
### and ratio of tweets / retweets in last 1000 tweets > 0.75
### score 0 = all other cases

# score changers
# if verified account add 3 to score
# if likes / tweets > 100 decrease score by 2
# if 0.5 < followers / following < 1.5 decrease score by 2

