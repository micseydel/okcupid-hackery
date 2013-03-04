#!/usr/bin/env python

#http://sujitpal.blogspot.com/2007/04/building-tag-cloud-with-python.html

import pickle
import os
from getpass import getpass
from urllib2 import URLError
from time import sleep, time
from random import choice
from collections import Counter
from itertools import count

from mechanize import Browser
import lxml.html as html
try:
    from matplotlib import pyplot as plot
    matplotlib = True
except ImportError:
    matplotlib = False

NUM_ZERO_GROWTH_SEARCHES = 15

LOGIN_URL = "http://www.okcupid.com/login"
PROFILE_URL_BASE = "http://www.okcupid.com/profile/"
SEARCH_URL = ("http://www.okcupid.com/match?"
    "filter1=0,63&"
    "filter2=2,100,18&"
    "filter3=5,31536000&"
    "filter4=1,0&"
    "filter5=35,0&"
    "locid=0&"
    "timekey=1&"
    "matchOrderBy=MATCH&"
    "custom_search=0&"
    "fromWhoOnline=0&"
    "mygender=m&"
    "update_prefs=0&"
    "sort_type=0&"
    "sa=1&"
)
# SEARCH_URL = ("http://www.okcupid.com/match"
#     "?filter1=0,34"
#     "&filter2=2,100,18" # age
#     "&filter3=5,2678400"
#     "&filter4=1,1"
#     "&filter5=35,0"
#     "&locid=0"
#     "&timekey=1"
#     "&matchOrderBy=MATCH"
#     "&custom_search=0"
#     "&fromWhoOnline=0"
#     "&mygender=m"
#     "&update_prefs=0"
#     "&sort_type=0"
#     "&sa=1")

class User(object):
    def __init__(self, username, percents, age, img_url, sexuality, status,
        location, reply_rate):
        self.username = username
        self.match, self.friend, self.enemy = percents
        self.age = age
        self.img = img_url
        self.orientation = sexuality
        self.status = status
        self.city, self.state = location.split(", ")[-2:]
        self.reply_rate = reply_rate

    def __hash__(self):
        return hash(self.username)

def merge(lists):
    ''' function to merge many sorted lists with unique elements
        used with permission from Hardy Jones III
        released under an Apache Version 2.0 license
    '''
    # Get the first sorted list to work with.
    result, rest = lists[0], lists[1:]

    # Iterate each of the rest of the sorted lists.
    for each_list in rest:
        # We'll need the index and item in the current list.
        for i, element in enumerate(each_list):
            # If we've already seen the element,
            # we need to check some stuff.
            if element in result:
                pos = result.index(element)
                # First make sure we're checking within bounds.
                # If the previous element is already before
                # the present element, then as far as we know,
                # the elements in the result are sorted.
                if i > 0 and result.index(each_list[i-1]) < pos:
                    continue
                # Otherwise, we need to make sure everything we've
                # entered so far is in the sorted position.
                else:
                    for each in each_list[:i]:
                        # If an element isn't sorted, then sort it.
                        if result.index(each) > pos:
                            result.remove(each)
                            result.insert(pos, each)
            # If we made it here, then we've never seen this element.
            # Just throw it on the back.
            else:
                result.append(element)

    return result

def login(br, username, password):
    br.open(LOGIN_URL)
    br.select_form(nr=0)
    br["username"] = username
    br["password"] = password
    br.submit()

def do_search(br):
    while True:
        try:
            resp = br.open(SEARCH_URL)
            break
        except URLError:
            pass

    page = html.parse(resp)
    match_results = page.getroot().get_element_by_id("match_results")

    users = {}
    usernames = []
    for _wrap, percentages, actions in match_results:
        _user_info, essay = _wrap
        user_image, match_row_screenname, aso, location, activity = _user_info

        percents = [int(percent.text_content().split('%')[0])
            for percent in percentages]
        if percents[0] < 99: break
        username = match_row_screenname[0][0].text_content()
        age, sex, sexuality, status = (aso_element.encode("utf-8")
            for aso_element in aso.text_content().split()[::2])

        try:
            reply_rate = activity[0][1].text_content()
        except IndexError:
            reply_rate = activity.text_content()

        user = User(username.encode("utf-8"), percents,
            int(age), user_image[0].get("src"), sexuality, status,
            location.text_content().encode("utf-8"), reply_rate
        )
        users[username] = user
        usernames.append(user.username)

    return users, usernames

def get_data(br):
    if os.path.isfile("okcupid.pickle"):
        with open("okcupid.pickle", "rb") as okc_file:
            all_users = pickle.load(okc_file)
            username_lists = pickle.load(okc_file)
        return all_users, username_lists

    all_users = {}
    username_lists = []
    num_users = 0
    for search in count(1):
        users, usernames = do_search(br)
        username_lists.append(usernames)

        all_users.update(users)
        growth = len(all_users) - num_users
        print "Growth:", growth
        print "99%ers so far:", len(all_users)
        if growth == 0:
            give_up_yet -= 1 # not init'd; but will be
            print "Remaining 0 growth searches:", give_up_yet
            if give_up_yet == 0:
                print "stopped after", search, "searches"
                break
        else:
            give_up_yet = NUM_ZERO_GROWTH_SEARCHES
        num_users = len(all_users)
        sleep(choice(range(7, 14))) # to look less suspicious

    try:
        with open("okcupid.pickle", "wb") as okc_file:
            pickle.dump(all_users, okc_file)
            pickle.dump(username_lists, okc_file)
    except TypeError:
        print "It looks like pickling failed because of a TypeError"

    return all_users, username_lists

def inform(all_users, username_lists):
    states = {}
    for city, state in ((u.city, u.state) for u in all_users.values()):
        if state in states:
            states[state].append(city)
        else:
            states[state] = [city]

    key = lambda x: len(x[1])
    for state, cities in sorted(states.iteritems(), key=key):
        print state, "({}, {:.2f}%)".format(
            len(cities), 100 * float(len(cities)) / len(all_users))
        for city, count in sorted(Counter(cities).iteritems(),
            key=lambda x: x[1], reverse=True):
            print "   ", city,
            print "({})".format(count) if count > 1 else ""
        print


    print "Top 10 users (out of {}):".format(len(all_users))
    for place, username in enumerate(merge(username_lists)[:10], 1):
        print "{:2}) {}".format(place, username)

    if not matplotlib:
        print "Install matplotlib for some pretty graphs"
        return False

    orientation = Counter(user.orientation for user in all_users.values())
    plot.title("Orientation")
    labels, fracs = zip(*orientation.iteritems())
    plot.pie(fracs, labels=labels, shadow=True, autopct='%1.1f%%')
    plot.show()

    status = Counter(user.status for user in all_users.values())
    plot.title("Relationship Status")
    labels, fracs = zip(*status.iteritems())
    explode = [0.05 if label == 'Single' else 0 for label in labels]
    plot.pie(fracs, explode, labels, shadow=True, autopct='%1.1f%%')
    plot.show()

    reply_rates = Counter(user.reply_rate for user in all_users.values())
    plot.title("Replies...")
    labels = ("Go for it.", "often", "selectively", "very selectively")
    fracs = [reply_rates[label] for label in labels]
    plot.pie(fracs, labels=labels, shadow=True, autopct='%1.1f%%')
    plot.show()

    plot.bar(*zip(
        *Counter(user.friend for user in all_users.values()).items())
    )
    plot.title("Friend percents")
    plot.xlabel("Percent")
    plot.ylabel("Number of People")
    plot.show()

    plot.bar(*zip(
        *Counter(user.enemy for user in all_users.values()).items())
    )
    plot.title("Enemy percents")
    plot.xlabel("Percent")
    plot.ylabel("Number of People")
    plot.show()

    plot.bar(*zip(
        *Counter(user.age for user in all_users.values()).items())
    )
    plot.xlabel("Years")
    plot.ylabel("Number of People")
    plot.title("Age")
    plot.show()

def scrape_user(br, username):
    resp = br.open(PROFILE_URL_BASE + username)
    page = html.parse(resp).getroot()

    last_online, ethnicity, height, body_type, diet, looking_for, smokes, \
        drinks, drugs, religion, sign, education, job, income, offspring, \
        pets, speaks = page.get_element_by_id("profile_details")

    essays = {}
    for sum_num in xrange(10):
        key = "essay_text_{}".format(sum_num)
        try:
            element = page.get_element_by_id(key)
            tags = filter(lambda element: element.tag != "br", self_summary)
            essays[key] = element
        except KeyError:
            essays[key] = None

    self_summary, doing_with_life, good_at, people_notice, favorites, \
        never_do_without, think_about, friday, private, message_if = \
        (essays["essay_text_{}".format(sum_num)] for sum_num in xrange(10))

    if self_summary is None:
        tags = filter(lambda element: element.tag != "br", self_summary)
    else:
        pass

    if doing_with_life is None:
        pass
    else:
        pass

    if good_at is None:
        pass
    else:
        pass

    if people_notice is None:
        pass
    else:
        pass

    if favorites is None:
        pass
    else:
        pass

    if never_do_without is None:
        pass
    else:
        pass

    if think_about is None:
        pass
    else:
        pass

    if friday is None:
        pass
    else:
        pass

    if private is None:
        pass
    else:
        pass

    if message_if is None:
        pass
    else:
        pass

if __name__ == "__main__":
    username = raw_input("Enter username: ")
    password = getpass()

    br = Browser()
    login(br, username, password)
    start = time()
    all_users, username_lists = get_data(br)
    print "{}:{:2}".format(*divmod(time() - start, 60))

    #sorted_usernames = merge(username_lists)
    #inform(all_users, username_lists)
