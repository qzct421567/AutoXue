#!/usr/bin/env python
# -*- coding:utf-8 -*-
'''
@project: AutoXue
@file: __init__.py
@author: kessil
@contact: https://github.com/kessil/AutoXue/
@time: 2019-10-26(星期六) 09:03
@Copyright © 2019. All rights reserved.
'''
import re
import random
import time
import requests
import string
from urllib.parse import quote
from collections import defaultdict
from appium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from .unit import Timer, logger, caps, rules
from .model import BankQuery

class CONST:
    CHALLENGE_COUNT_MIN = 20
    CHALLENGE_COUNT_MAX = 40
    CHALLENGE_DELAY_MIN = 1
    CHALLENGE_DELAY_MAX = 8

class Automation():
    # 初始化 Appium 基本参数
    def __init__(self):
        self.desired_caps = {
            "platformName": caps["platformname"],
            "platformVersion": caps["platformversion"],
            "automationName": caps["automationname"],
            "unicodeKeyboard": caps["unicodekeyboard"],
            "resetKeyboard": caps["resetkeyboard"],
            "noReset": caps["noreset"],
            'newCommandTimeout': 800,
            "deviceName": caps["devicename"],
            "uuid": caps["uuid"],
            "appPackage": caps["apppackage"],
            "appActivity": caps["appactivity"]
        }
        logger.info('打开 appium 服务器,正在配置...')
        self.driver = webdriver.Remote('http://localhost:4723/wd/hub', self.desired_caps)
        self.wait = WebDriverWait(self.driver, 10)
        self.size = self.driver.get_window_size()

    # 屏幕方法
    def swipe_up(self):
        # 向上滑动屏幕
        self.driver.swipe(self.size['width'] * random.uniform(0.55, 0.65),
                          self.size['height'] * random.uniform(0.65, 0.75),
                          self.size['width'] * random.uniform(0.55, 0.65),
                          self.size['height'] * random.uniform(0.25, 0.35), random.uniform(800, 1200))
        logger.debug('向上滑动屏幕')

    def swipe_down(self):
        # 向下滑动屏幕
        self.driver.swipe(self.size['width'] * random.uniform(0.55, 0.65),
                          self.size['height'] * random.uniform(0.25, 0.35),
                          self.size['width'] * random.uniform(0.55, 0.65),
                          self.size['height'] * random.uniform(0.65, 0.75), random.uniform(800, 1200))
        logger.debug('向下滑动屏幕')

    def swipe_right(self):
        # 向右滑动屏幕
        self.driver.swipe(self.size['width'] * random.uniform(0.01, 0.11),
                          self.size['height'] * random.uniform(0.75, 0.89),
                          self.size['width'] * random.uniform(0.89, 0.98),
                          self.size['height'] * random.uniform(0.75, 0.89), random.uniform(800, 1200))
        logger.debug('向右滑动屏幕')
    def swipe_left(self):
        # 向右滑动屏幕
        self.driver.swipe(self.size['width'] * random.uniform(0.89, 0.98),
                          self.size['height'] * random.uniform(0.75, 0.89),
                          self.size['width'] * random.uniform(0.01, 0.11),
                          self.size['height'] * random.uniform(0.75, 0.89), random.uniform(800, 1200))
        logger.debug('向左滑动屏幕')

    # 返回事件
    def safe_back(self, msg='default msg'):
        logger.debug(msg)
        self.driver.keyevent(4)
        time.sleep(1)

    def safe_click(self, ele:str):
        self.wait.until(EC.presence_of_element_located((By.XPATH, ele))).click()
        time.sleep(1)

    def __del__(self):
        self.driver.close_app()
        self.driver.quit()


class App(Automation):
    def __init__(self):
        self.bq = BankQuery()
        self.bank = None
        self._score = defaultdict(tuple)
        super().__init__()
        self.driver.wait_activity('com.alibaba.android.rimet.biz.home.activity.HomeActivity', 20, 3)
        # logger.error(self.driver.current_activity)

    def view_score(self):
        self.safe_click(rules['score_entry'])
        score_list = self.wait.until(EC.presence_of_all_elements_located((By.XPATH, rules['score_list'])))
        for score in score_list:
            scores = score.find_elements_by_class_name('android.view.View')
            t, s = scores[0].get_attribute("name"), scores[2].get_attribute("name")
            # print(t, s, re.findall(r'\d+', s))
            self._score[t] = tuple([int(x) for x in re.findall(r'\d+', s)])

        # print(self._score)
        # for i in self._score:
        #     print(i, self._score[i])
        self.safe_back('score -> home')

    def quiz(self):
        self.safe_click(rules['mine_entry'])
        self.safe_click(rules['quiz_entry'])

        # 挑战答题
        self.challenge()

        self.safe_back('quiz -> mine')
        self.safe_back('mine -> home')

    def _search(self, content, options, exclude=''):
        logger.debug(f'search [{content}] in baidu')
        content = re.sub(r'[\(（]出题单位.*', "", content)
        # logger.info(content)
        if options[-1].startswith("以上") and chr(len(options)+64) not in exclude:
            logger.info(options)
            logger.info(f'根据经验: {chr(len(options)+64)} 很可能是正确答案')
            return len(options)-1
        url = quote('https://www.baidu.com/s?wd=' + content, safe=string.printable)
        headers = {
            'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36"
        }
        response = requests.get(url, headers=headers).text
        counts = []
        for i, option in zip(['A', 'B', 'C', 'D', 'E', 'F'], options):
            count = response.count(option)
            counts.append((count, i))
            logger.info(f'{i}. {option}: {count}')
        counts = sorted(counts, key=lambda x:x[0], reverse=True)
        counts = [x for x in counts if x[1] not in exclude]
        c, i = counts[0]
        logger.info(f'根据搜索结果: {i} 很可能是正确答案')
        return ord(i)-65

    def _verify_answer(self, content, options):
        logger.info(content)
        # logger.info("\n".join(options))
        self.bank = self.bq.get({
            "category": "挑战题",
            "content": content,
            "options": options
        })
        # logger.warning(self.bank)
        if self.bank:
            if '' != self.bank["answer"]:
                logger.info(options)
                logger.info(f'提交正确答案 {self.bank["answer"]}')
                return ord(self.bank["answer"])-65
            else:
                logger.info(f'已知的排除项有: {self.bank["excludes"]}')
                return self._search(content, options, self.bank["excludes"])
        return self._search(content, options)


    def _challenge_cycle(self, num):
        self.safe_click(rules['challenge_entry'])
        while num:
            self.bank = None
            content = self.wait.until(EC.presence_of_element_located((By.XPATH, rules['challenge_content']))).get_attribute("name")
            option_elements = self.wait.until(EC.presence_of_all_elements_located((By.XPATH, rules['challenge_options'])))
            options = [x.get_attribute("name") for x in option_elements]
            # print(content, options)
            choose_index = self._verify_answer(content, options) # <int>0~len(options)
            challenge_delay = random.randint(CONST.CHALLENGE_DELAY_MIN, CONST.CHALLENGE_DELAY_MAX)
            logger.info(f'随机延时 {challenge_delay} 秒...')
            time.sleep(challenge_delay)
            option_elements[choose_index].click()            
            try:
                time.sleep(2)
                wrong = self.driver.find_element_by_xpath(rules['challenge_revival'])
                # 找到了，说明答错，先把排除项推送了
                logger.debug("很遗憾这题回答错误...")
                self.bq.put({
                    "category": "挑战题",
                    "content": content,
                    "options": options,
                    "answer": "",
                    "excludes": chr(65+choose_index),
                    "notes": ""
                })
                # if "分享就能复活" == wrong.get_attribute("name"):
                #     logger.debug("分享再来一局吧...")
                #     wrong.click()
                #     time.sleep(2)
                # elif "再来一局" == wrong.get_attribute("name"):
                #     logger.debug("很遗憾呢，请返回再接再厉……")
                #     break
                # else:
                #     logger.debug("肯定出问题了！居然会来到我的位置？")
                self.safe_back('challenge -> quiz')
                break
            except:
                # 没找到，回答正确，继续吧
                num -= 1
                logger.debug("回答正确，请继续你的表演……")
                if not self.bank:
                    logger.debug(f'扩充题库...')
                    self.bq.post({
                        "category": "挑战题",
                        "content": content,
                        "options": options,
                        "answer": chr(65+choose_index),
                        "excludes": "",
                        "notes": ""
                    })
                elif self.bank and '' == self.bank['answer']:
                    logger.debug(f'更新题库...')
                    self.bq.put({
                        "category": "挑战题",
                        "content": content,
                        "options": options,
                        "answer": chr(65+choose_index),
                        "excludes": "",
                        "notes": ""
                    })
            if 0 == num:
                logger.info(f'已达成指定题量，延时30秒安全退出！')
                time.sleep(30)

        return num



    def challenge(self):
        # gain, total = self._score['挑战答题']
        # if gain == total:
        #     logger.info(f'挑战答题已完成')
        #     return
        challenge_count = random.randint(CONST.CHALLENGE_COUNT_MIN, CONST.CHALLENGE_COUNT_MAX)
        logger.info(f'本局挑战答题目标 {challenge_count} 题')
        while True:
            if 0 == self._challenge_cycle(challenge_count):
                logger.info(f'已成功挑战 {challenge_count} 题，返回首页！')
                break
            else:
                logger.info(f'未完成{challenge_count}题，再来一局……')
                time.sleep(5)






        