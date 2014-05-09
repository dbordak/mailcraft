import contextio as c
from secrets import CONSUMER_KEY, CONSUMER_SECRET, EMAIL


def cleanMessage(mes):
    cur = {
        'subject': mes.subject,
        'date': mes.date,
        'from': mes.addresses['from']['email'],
        'numrecip': len(mes.addresses['to'])
    }
    if 'cc' in mes.addresses:
        cur['numrecip'] += len(mes.addresses['cc'])
    return cur


def getThreadMessages(thread):
    thread.get()
    if not thread.messages:
        return None
    return [cleanMessage(mes) for mes in thread.messages]


def getmail():
    threads = c.ContextIO(
        consumer_key=CONSUMER_KEY,
        consumer_secret=CONSUMER_SECRET,
        # debug=True
    ).get_accounts(email=EMAIL)[0].get_threads()

    return [getThreadMessages(thread) for thread in threads]
