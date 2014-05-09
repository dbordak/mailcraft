import contextio as c
from secrets import CONSUMER_KEY, CONSUMER_SECRET, EMAIL


def getmail():
    context_io = c.ContextIO(
        consumer_key=CONSUMER_KEY,
        consumer_secret=CONSUMER_SECRET,
        # debug=True
    )

    accounts = context_io.get_accounts(email=EMAIL)

    data = []

    threads = accounts[0].get_threads()

    for thread in threads:
        thread.get()
        threaddata = []
        if thread.messages:
            for mes in thread.messages:
                try:
                    threaddata.append({
                        'subject': mes.subject,
                        'date': mes.date,
                        'from': mes.addresses['from']['email'],
                        'numrecip': len(mes.addresses['to']) +
                        len(mes.addresses['cc'])
                    })
                except:
                    try:
                        threaddata.append({
                            'subject': mes.subject,
                            'date': mes.date,
                            'from': mes.addresses['from']['email'],
                            'numrecip': len(mes.addresses['to'])
                        })
                    except:
                        0
        data.append(threaddata)

    return data
