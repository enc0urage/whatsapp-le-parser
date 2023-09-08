import json
import sys
import phonenumbers
import email.policy
from bs4 import BeautifulSoup
from dateutil.parser import parse as parse_date
from email.parser import BytesParser as EmailParser
from email.utils import parsedate_to_datetime


def parse_eml(file_name):
    bp = EmailParser(policy=email.policy.default)
    with open(file_name, "rb") as f:
        return bp.parse(f)


def parse_headers(eml):
    res = {}

    res["to"] = eml["To"]
    res["subject"] = eml["Subject"]
    res["date"] = int(parsedate_to_datetime(eml["Date"]).timestamp())
    res["message-id"] = eml["message-id"]

    return res


def normalize_phone(phone_number):
    phone_number = "+" + phone_number.replace("+", "")
    n = phonenumbers.parse(phone_number)
    return phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.E164)


def normalize_date(d):
    return int(parse_date(d).timestamp())


def parse_date_range(s):
    res = [int(parse_date(x).timestamp()) for x in s.split(" to ")]
    return {"from": res[0], "to": res[1]}


def parse_message(m):
    res = {}

    for a in m.find("td").find_all("table", recursive=False):
        th = a.find("th").text.lower().replace(" ", "_")
        td = a.find("td").text

        if "timestamp" == th:
            res[th] = normalize_date(td)
        elif "sender" == th:
            res[th] = normalize_phone(td)
        elif "recipients" == th:
            if "," in td:
                res[th] = [normalize_phone(x) for x in td.split(", ")]
            else:
                res[th] = [normalize_phone(td)]
        elif "sender_port" == th or "message_size" == th:
            res[th] = int(td)
        else:
            res[th] = td

    return res


def parse_message_log(l):
    res = []

    for msg in l.find_all("table", recursive=False):
        res.append(parse_message(msg))

    return res


def parse_call_participants(p):
    res = []

    for a in p.find_all("table"):
        th = a.find("th").text
        td = a.find("td").text

        if th == "Phone Number":
            res.append(normalize_phone(td))
        else:
            res.append(td)

    return res


def parse_call_events(e):
    res = {}
    event_type = None
    event = None

    for a in e.find_all("table", recursive=False):
        th = a.find("th").text.lower().replace(" ", "_")
        td = a.find("td")

        if "type" == th:
            if event is not None:
                res[event_type] = event
            event_type = td.text
            event = {}
        elif "timestamp" == th:
            event[th] = normalize_date(td.text)
        elif th == "from" or "to" == th:
            if len(td.text) == 0:
                event[th] = None
            else:
                event[th] = normalize_phone(td.text)
        elif "from_port" == th:
            event[th] = int(td.text)
        elif "participants" == th:
            event[th] = parse_call_participants(td)
        else:
            event[th] = td.text

    res[event_type] = event
    return res


def parse_call(c):
    res = {}

    for a in c.find("td").find_all("table", recursive=False):
        th = a.find("th").text.lower().replace(" ", "_")
        td = a.find("td")

        if "call_creator" == th:
            res[th] = normalize_phone(td.text)
        elif "events" == th:
            res["events"] = parse_call_events(td)
        else:
            res[th] = td.text

    return res


def parse_calls(l):
    res = []

    for call in l.find_all("table", recursive=False):
        res.append(parse_call(call))

    return res


def parse_additional_properties(soup):
    res = {}
    for div in soup.find_all("div", recursive=False):
        for table in div.find_all("table", recursive=False):
            th = table.find("th").text

            if "Message Log" == th:
                res["messages"] = parse_message_log(table.find("td"))
            elif "Call Log" in th:
                res["calls"] = parse_calls(table.find("td"))

    return res


def parse_data(eml):
    res = {}
    soup = BeautifulSoup(eml.get_content(), "html.parser")

    res["link"] = soup.find("a")["href"]
    tables = soup.find_all("table", recursive=False)

    for table in tables:
        th = table.find("th").text

        if "Service" == th:
            res["service"] = table.find("td").text
        elif "Identifier" in th:
            res["identifier"] = normalize_phone(table.find("td").text)
        elif "Account Type" == th:
            res["type"] = table.find("td").text
        elif "Generated" == th:
            res["generated"] = normalize_date(table.find("td").text)
        elif "Date Range" == th:
            res["date_range"] = parse_date_range(table.find("td").text)
        elif "Message Log" == th:
            res["messages"] = parse_message_log(table.find("td"))
        elif "Call Log" in th:
            res["calls"] = parse_calls(table.find("td"))
        elif "Additional Properties" == th:
            res |= parse_additional_properties(soup)

    if "messages" not in res:
        res["messages"] = []
    if "calls" not in res:
        res["calls"] = []

    return res


def cli():
    input_file = sys.argv[1]
    print(input_file, file=sys.stderr)
    result = {"file": input_file.rsplit("/", 1)[-1]}
    eml = parse_eml(input_file)
    result |= parse_headers(eml)
    result |= parse_data(eml)

    json.dump(result, sys.stdout, indent=2)
