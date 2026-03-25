import math
import time

import random
from google import genai

import util
from log.custom_logger import log

from prompt.agent_prompt import *
from secretary import Secretary
from stock import Stock



def random_init(stock_a_initial, stock_b_initial):
    stock_a, stock_b, cash, debt_amount = 0.0, 0.0, 0.0, 0.0
    while stock_a * stock_a_initial + stock_b * stock_b_initial + cash < util.MIN_INITIAL_PROPERTY \
            or stock_a * stock_a_initial + stock_b * stock_b_initial + cash > util.MAX_INITIAL_PROPERTY \
            or debt_amount > stock_a * stock_a_initial + stock_b * stock_b_initial + cash:
        stock_a = int(random.uniform(0, util.MAX_INITIAL_PROPERTY / stock_a_initial))
        stock_b = int(random.uniform(0, util.MAX_INITIAL_PROPERTY / stock_b_initial))
        cash = random.uniform(0, util.MAX_INITIAL_PROPERTY)
        debt_amount = random.uniform(0, util.MAX_INITIAL_PROPERTY)
    debt = {
        "loan": "yes",
        "amount": debt_amount,
        "loan_type": random.randint(0, len(util.LOAN_TYPE) - 1),
        "repayment_date": random.choice(util.REPAYMENT_DAYS)
    }
    return stock_a, stock_b, cash, debt
# def random_init(stock_initial_price):
#     stock, cash, debt_amount = 0.0, 0.0, 0.0
#     while stock * stock_initial_price + cash < util.MIN_INITIAL_PROPERTY \
#             or stock * stock_initial_price + cash > util.MAX_INITIAL_PROPERTY \
#             or debt_amount > stock * stock_initial_price + cash:
#         stock = int(random.uniform(0, util.MAX_INITIAL_PROPERTY / stock_initial_price))
#         cash = random.uniform(0, util.MAX_INITIAL_PROPERTY)
#         debt_amount = random.uniform(0, util.MAX_INITIAL_PROPERTY)
#     debt = {
#         "loan": "yes",
#         "amount": debt_amount,
#         "loan_type": random.randint(0, len(util.LOAN_TYPE)),
#         "repayment_date": random.choice(util.REPAYMENT_DAYS)
#     }
#     return stock, cash, debt


class Agent:
    def __init__(self, i, stock_a_price, stock_b_price, secretary, model):
        self.order = i
        self.secretary = secretary
        self.model = model
        self.character = random.choice(["Conservative", "Aggressive", "Balanced", "Growth-Oriented"])

        self.stock_a_amount, self.stock_b_amount, self.cash, init_debt = random_init(stock_a_price, stock_b_price)
        #self.stock_b_amount = 0  # stock 以手为单位存储，一手=10股，股价其实是一手的价格
        self.init_proper = self.get_total_proper(stock_a_price, stock_b_price)  # 初始资产 后续借贷不超过初始资产

        self.action_history = [[] for _ in range(util.TOTAL_DATE)]
        self.chat_history = []
        self.loans = [init_debt]
        self.is_bankrupt = False
        self.quit = False

    def run_api(self, prompt, temperature: float = 1):
        return self.run_api_gpt(prompt, temperature)
    
    def run_api_gpt(self, prompt, temperature: float = 1):
        import util
        import time
        from google import genai
        import json
        client = genai.Client(api_key=util.GOOGLE_API_KEY)

        
        self.chat_history.append({"role": "user", "content": prompt})
        max_retry = 2
        retry = 0
        while retry < max_retry:
            try:
                full_prompt = ""
                for msg in self.chat_history:
                    full_prompt += f"{msg['role'].upper()}: {msg['content']}\n"

                response = client.models.generate_content(
                model=self.model,
                contents=full_prompt
            )
                reply = response.text.strip()
                clean_reply = reply.strip().strip("```json").strip("```")
                import json
                try:
                     data = json.loads(reply)  # try to parse JSON
                except json.JSONDecodeError:
                     log.logger.warning(f"Wrong json content in response: {reply}")
                     data = {}  # fallback to empty dict or default response
                self.chat_history = self.chat_history[-10:]

                self.chat_history.append({
                     "role": "assistant",
                     "content": reply
                     })
                return reply
            except Exception as e:
                retry += 1
                if hasattr(e, 'details'):
                   for detail in getattr(e, 'details', []):
                       if isinstance(detail, dict) and '@type' in detail:
                           if 'RetryInfo' in detail.get('@type', ''):
                               log.logger.error("Gemini quota exceeded. Skipping this request.")
                               return ""   
                           else:
                               log.logger.warning(f"Gemini API retry... {e}")
                               time.sleep(1)
                log.logger.error("ERROR: GEMINI API FAILED. SKIP THIS INTERACTION.")
                return ""

    def get_total_proper(self, stock_a_price, stock_b_price):
        return self.stock_a_amount * stock_a_price + self.stock_b_amount * stock_b_price + self.cash

    def get_proper_cash_value(self, stock_a_price, stock_b_price):
        proper = self.stock_a_amount * stock_a_price + self.stock_b_amount * stock_b_price + self.cash
        a_value = self.stock_a_amount * stock_a_price
        b_value = self.stock_b_amount * stock_b_price
        return proper, self.cash, a_value, b_value

    def get_total_loan(self):
        debt = 0
        for loan in self.loans:
            debt += loan["amount"]
        return debt
    def plan_loan(self, date, stock_a_price, stock_b_price, lastday_forum_message):
        if self.quit:
            return {"loan": "no"}
        max_loan = self.init_proper - self.get_total_loan()
        if max_loan <= 0:
            return {"loan": "no"}
        inputs = {
        "date": date,
        "character": self.character,
        "stock_a": self.stock_a_amount,
        "stock_b": self.stock_b_amount,
        "cash": self.cash,
        "debt": self.loans,
        "max_loan": max_loan,
        "loan_type_prompt": LOAN_TYPE_PROMPT,  # use prompt from agent_prompt.py
        "stock_a_price": stock_a_price,
        "stock_b_price": stock_b_price,
        "lastday_forum_message": lastday_forum_message,
        "loan_rate1": util.LOAN_RATE[0],
        "loan_rate2": util.LOAN_RATE[1],
        "loan_rate3": util.LOAN_RATE[2],
    }
        prompt_text = format_prompt(DECIDE_IF_LOAN_PROMPT, inputs)
        resp = self.run_api(prompt_text)
        if resp == "":
            return {"loan": "no"}
        loan_format_check, fail_response, loan = self.secretary.check_loan(resp, max_loan)
        try_times = 0
        MAX_TRY_TIMES = 3
        while not loan_format_check:
            try_times += 1
            if try_times > MAX_TRY_TIMES:
                log.logger.warning("WARNING: Loan format try times > MAX_TRY_TIMES. Skip as no loan today.")
                loan = {"loan": "no"}
                break
            resp = self.run_api(format_prompt(LOAN_RETRY_PROMPT, {"fail_response": fail_response}))
            loan_format_check, fail_response, loan = self.secretary.check_loan(resp, max_loan)
        if loan_format_check and loan.get("loan") == "yes":
            loan["repayment_date"] = date + util.LOAN_TYPE_DATE[loan["loan_type"]]
            self.loans.append(loan)
            self.cash += loan["amount"]
            log.logger.info(f"INFO: Agent {self.order} decide to loan: {loan}")
        else:
            loan = {"loan": "no"}
            log.logger.info(f"INFO: Agent {self.order} decide not to loan")
        return loan


 

    # date=交易日, time=当前交易时段
    # 设置
    
    def plan_stock(self, date, time, stock_a, stock_b, stock_a_deals, stock_b_deals):
        if self.quit:
            return {"action_type": "no"}
        inputs = {
        "date": date,
        "time": time,
        "stock_a": self.stock_a_amount,
        "stock_b": self.stock_b_amount,
        "stock_a_price": stock_a.get_price(),
        "stock_b_price": stock_b.get_price(),
        "stock_a_deals": stock_a_deals,
        "stock_b_deals": stock_b_deals,
        "cash": self.cash
    }
        if date in util.SEASON_REPORT_DAYS and time == 1:
            index = util.SEASON_REPORT_DAYS.index(date)
            inputs["stock_a_report"] = stock_a.gen_financial_report(index)
            inputs["stock_b_report"] = stock_b.gen_financial_report(index)
            prompt_text = format_prompt(DECIDE_BUY_STOCK_PROMPT, inputs)
        else:
            prompt_text = format_prompt(DECIDE_BUY_STOCK_PROMPT, inputs)
        resp = self.run_api(prompt_text)
        if resp == "":
            return {"action_type": "no"}
        action_format_check, fail_response, action = self.secretary.check_action(
                resp, self.cash, self.stock_a_amount, self.stock_b_amount, stock_a.get_price(), stock_b.get_price()
                )
        try_times = 0
        MAX_TRY_TIMES = 3
        while not action_format_check and try_times < MAX_TRY_TIMES:
            try_times += 1
            resp = self.run_api(format_prompt(BUY_STOCK_RETRY_PROMPT, {"fail_response": fail_response}))
            action_format_check, fail_response, action = self.secretary.check_action(
                resp, self.cash, self.stock_a_amount, self.stock_b_amount, stock_a.get_price(), stock_b.get_price()
            )
        if not action_format_check:
            return {"action_type": "no"}
        log.logger.info(f"INFO: Agent {self.order} decide action: {action}")
        return action

    def buy_stock(self, stock_name, price, amount):
        if self.quit:
            return False
        if self.cash < price * amount or stock_name not in ['A', 'B']:
            log.logger.warning("ILLEGAL STOCK BUY BEHAVIOR: remain cash {}".format(self.cash))
            return False
        self.cash -= price * amount
        if stock_name == 'A':
            self.stock_a_amount += amount
        elif stock_name == 'B':
            self.stock_b_amount += amount

        return True

    def sell_stock(self, stock_name, price, amount):
        if self.quit:
            return False
        if stock_name == 'B' and self.stock_b_amount < amount:
            log.logger.warning("ILLEGAL STOCK SELL BEHAVIOR: remain stock_b {}, amount {}".format(self.stock_b_amount,
                                                                                                  amount))
            return False
        elif stock_name == 'A' and self.stock_a_amount < amount:
            log.logger.warning("ILLEGAL STOCK SELL BEHAVIOR: remain stock_a {}, amount {}".format(self.stock_a_amount,
                                                                                                  amount))
            return False
        if stock_name == 'A':
            self.stock_a_amount -= amount
        elif stock_name == 'B':
            self.stock_b_amount -= amount
        self.cash += price * amount
        return True

    def loan_repayment(self, date):
        if self.quit:
            return
        # check是否贷款还款日，还款，破产检查
        for loan in self.loans[:]:
            if loan["repayment_date"] == date:
                self.cash -= loan["amount"] * (1 + util.LOAN_RATE[loan["loan_type"]])
                self.loans.remove(loan)
        if self.cash < 0:
            self.is_bankrupt = True


    def interest_payment(self):
        if self.quit:
            return
        # 贷款付息日付息
        for loan in self.loans:
            self.cash -= loan["amount"] * util.LOAN_RATE[loan["loan_type"]] / 12
            if self.cash < 0:
                self.is_bankrupt = True

    def bankrupt_process(self, stock_a_price, stock_b_price):
        if self.quit:
            return False
        total_value_of_stock = self.stock_a_amount * stock_a_price + self.stock_b_amount * stock_b_price
        if total_value_of_stock + self.cash < 0:
            log.logger.warning(f"Agent {self.order} bankrupt. ")
                               #f"Action history: " + str(self.action_history))
            return True
        if stock_a_price * self.stock_a_amount >= -self.cash:
            sell_a = math.ceil(-self.cash / stock_a_price)
            self.stock_a_amount -= sell_a
            self.cash += sell_a * stock_a_price
        else:
            self.cash += stock_a_price * self.stock_a_amount
            self.stock_a_amount = 0
            sell_b = math.ceil(-self.cash / stock_b_price)
            self.stock_b_amount -= sell_b
            self.cash += sell_b * stock_b_price

        if self.stock_a_amount < 0 or self.stock_b_amount < 0 or self.cash < 0:
            raise RuntimeError("ERROR: WRONG BANKRUPT PROCESS")
        self.is_bankrupt = False
        return False

    def post_message(self):
        if self.quit:
            return ""
        prompt = format_prompt(POST_MESSAGE_PROMPT, inputs={})
        resp = self.run_api(prompt)
        return resp

    def next_day_estimate(self):
        if self.quit:
            return {"buy_A": "no", "buy_B": "no", "sell_A": "no", "sell_B": "no", "loan": "no"}
        prompt = format_prompt(NEXT_DAY_ESTIMATE_PROMPT, inputs={})
        resp = self.run_api(prompt)
        if resp == "":
            return {"buy_A": "no", "buy_B": "no", "sell_A": "no", "sell_B": "no", "loan": "no"}
        format_check, fail_response, estimate = self.secretary.check_estimate(resp)
        try_times = 0
        MAX_TRY_TIMES = 3
        while not format_check:
            try_times += 1
            if try_times > MAX_TRY_TIMES:
                log.logger.warning("WARNING: Estimation format try times > MAX_TRY_TIMES. Skip as all 'no' today.")
                estimate = {"buy_A": "no", "buy_B": "no", "sell_A": "no", "sell_B": "no", "loan": "no"}
                break
            resp = self.run_api(format_prompt(NEXT_DAY_ESTIMATE_RETRY, {"fail_response": fail_response}))
            if resp == "":
                return {"buy_A": "no", "buy_B": "no", "sell_A": "no", "sell_B": "no", "loan": "no"}
            format_check, fail_response, estimate = self.secretary.check_estimate(resp)
        return estimate


