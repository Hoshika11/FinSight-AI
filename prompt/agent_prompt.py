# prompt/agent_prompt.py

# Simple function to replace variables in prompts
def format_prompt(prompt, inputs=None):
    if inputs:
        for k, v in inputs.items():
            prompt = prompt.replace(f"{{{{{k}}}}}", str(v))
    return prompt

# Prompts as plain strings
BACKGROUND_PROMPT = """
You are a stock trader, and next you will simulate interactions with other traders in the market.
There are two stocks in the market, A and B, where B is the newly listed stock. 
Next, please complete your trading actions according to the order.
"""

LASTDAY_FORUM_AND_STOCK_PROMPT = """
After the close of trading yesterday, the stock prices of Company A and Company B 
were {stock_a_price} dollars per share and {stock_b_price} dollars per share, respectively. 
Posts by other traders on the forum are as follows: {lastday_forum_message}
"""

LOAN_TYPE_PROMPT = """
0. 22days, the benchmark interest rate {loan_rate1}
1. 44days, the benchmark interest rate {loan_rate2}
2. 66days, the benchmark interest rate {loan_rate3}
"""

DECIDE_IF_LOAN_PROMPT = """
It is the {date} day, and your current character is {character}. 
You hold {stock_a} shares of Company A, {stock_b} shares of Company B,
Now you have {cash} dollars in cash and {debt} in your loan situation.
You need to decide whether to continue the loan and the amount of the loan.
The alternative type is {loan_type_prompt}, and you should use the number to select a loan type. 
The loan amount shall not exceed {max_loan}.
Return the result as json, for example:
{{"loan": "yes", "loan_type": 3, "amount": 1000}}
If no loan is required, return:
{{"loan" : "no"}}
"""

LOAN_RETRY_PROMPT = """
The following questions appeared in the loan format you last answered: {fail_response}.
You should return the results as json, for example:
{{"loan": "yes", "loan_type": 2, "amount": 1000}}
If no loan is required, return:
{{"loan" : "no"}}
Please answer again.
"""

DECIDE_BUY_STOCK_PROMPT = """
It is the {time} trading session on the {date} day, and after the previous session, 
the stock price of Company A is {stock_a_price} and the stock price of Company B is {stock_b_price}.
In the current session, the buy and sell order of stock A is {stock_a_deals}, 
and the buy and sell order of stock B is {stock_b_deals}
You currently hold {stock_a} shares of Company A, {stock_b} shares of Company B, and {cash} yuan in cash.
You need to decide whether to buy/sell shares of Company A or Company B, and how much to buy/sell and at what price.
You can refer to the current share price and the market to determine the price yourself. 
The quantity must be an integer.
Return the result as json, for example:
{{"action_type":"buy"|"sell", "stock":"A"|"B", amount: 100, price : 30.1}}
If neither buy nor sell, return:
{{"action_type" : "no"}}
"""

BUY_STOCK_RETRY_PROMPT = """
The following questions appeared in the action format you last answered: {fail_response}.
You should return the result as json, for example:
{{"action_type":"buy"|"sell", "stock":"A"|"B", amount: 100, price: 30.1}}
If neither buy nor sell, return:
{{"action_type" : "no"}}
Please answer again. You can only answer one json action.
"""

FIRST_DAY_FINANCIAL_REPORT = """
The following lists the financial data for the past three years, covering a total of twelve quarters.
Stock A:
Revenue million: 3696.19, 3578.00, 3595.49, 3215.64, 3973.40, 3810.57, 3840.70, 3433.02, 4344.52, 4095.22, 4114.16, 3717.96
Net profit million: 127.711441, 217.9586418, 360.756337, 358.08228, 650.8868033, 693.3022798, 433.2338757, 517.0593354, 712.7358875, 628.310145, 250.5046675, 325.5147258
Cash flow million: 30.0950631, 135.4141818, 344.3249477, 279.5563512, 564.624197, 642.8122273, 350.3899245, 493.4058465, 650.6526937, 579.0037013, 185.7066407, 273.1287018
Stock B:
Revenue million: 570.00, 774.00, 643.00, 995.00, 684.46, 934.37, 782.08, 1204.05, 788.29, 1100.32, 914.96, 1418.37
Net profit million: 85.9691, 142.086, 87.5419224, 135.7643678, 132.7973368, 169.6505746, 194.9436163, 272.1084953, 225.1707811, 356.7201332
Cash flow million: 68.97, 90.171, 82.1754, 124.773, 75.4954968, 123.5240842, 132.7191287, 153.7571212, 194.9436163, 261.1053212, 216.3871992, 345.6568448
"""

FIRST_DAY_BACKGROUND_KNOWLEDGE = """
Company A has been listed for 10 years, deeply rooted in the chemical industry. However, the company's operations 
have encountered bottlenecks, with revenues declining over the past three years. 
Although Company A's performance has declined over the past five years, the overall trend is stable. With the recent 
CEO change and the exploration of new business avenues, the new CEO appears more proactive compared to the 
previous one. The future operational outlook is expected to improve. 

Company B, as a technology company, has just been listed for three years and is in a period of business growth. 
Last year, its revenue declined due to the overall tech environment, but the company's operations remain robust. 
According to the latest corporate news, it is expected that the future revenue growth rate will return to over 20%. 
In the short term, the stock price is expected to continue rising.
While Company B's operations are good, there is a history of concealing critical data before its IPO, casting doubt 
on the reliability of its revenue. 
Company B recently received government inquiries regarding recent operational and stock price fluctuations, and it 
provided explanations while committing to allocate more resources to social services. 

The government recently held talks with both Company A and Company B, actively encouraging their contributions 
to society. Subsequently, agreements on government subsidies were signed with both companies. 

The last 3 years financial report of stock A and B is listed in {first_day_financial_prompt}.
"""

SEASONAL_FINANCIAL_REPORT = """
Stock A: {stock_a_report}
Stock B: {stock_b_report}
"""

POST_MESSAGE_PROMPT = """
The current trading day is over, please briefly post your trading tips on the forum and post them on the forum.
What you post will be publicly visible to all traders. The responses contain only what needs to be posted.
"""

NEXT_DAY_ESTIMATE_PROMPT = """
Based on the market information and forum information of the current trading day, 
please estimate whether you will buy and sell stock A and stock B tomorrow, and whether you will choose loan.
Actions that are expected to take place are marked yes, and actions that will not take place are marked no. 
Return the result in json format, for example:
{{"buy_A":"yes", "buy_B":"no", "sell_A":"yes", "sell_B": "no", "loan": "yes"}}
"""

NEXT_DAY_ESTIMATE_RETRY = """
The following questions appeared in the JSON format you last answered: {fail_response}.
Return the result in json format, for example:
{{"buy_A":"yes", "buy_B":"no", "sell_A":"yes", "sell_B": "no", "loan": "yes"}}
"""
