#!/usr/bin/env python3
#  # dancerank-batch.py
# This programme is only for testing the functionality of batch processing.
# Try by entering
# "for file in Corpus/*; do dancerank-batch.py "$(cat $file)" -o tests/testoutput_<some_date>.csv; done"
# in your shell. You have to change into the directory where dancerank-batch.py is situated,
# or you will receive an error.
#
#  Copyright 2015 Alexander Blesius <alexander.blesius@klassphil.uni-giessen.de>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#


import argparse
import csv
import datetime
from html.parser import HTMLParser
import nltk.tag
import os
import re
import urllib.request
import urllib.parse

# # # # # Stanford Tagger settings # # # # #
# location of the NER models
os.environ['STANFORD_MODELS'] = '/home/alex/Informatik/stanford-ner-2015-04-20/' \
                                'stanford-german-2015-01-30-models/edu/stanford/nlp/models/ner/'

# location of the file "stanford-ner.jar".
# Make sure that CLASSPATH variable is set and debugger knows about it!
os.environ['STANFORD_PARSER'] = '/home/alex/Informatik/stanford-ner-2015-04-20/'

tagger = nltk.tag.StanfordNERTagger('german.dewac_175m_600.crf.ser.gz')  # 'german.hgc_175m_600.crf.ser.gz')
# # # # #

# constants
csv_header = ["NAME SIR", "NAME LADY", "CLUB", "TOURNAMENT LOCATION", "DATE", "RANK"]


class WikiCityParser(HTMLParser):
    cities = []
    dd_flag = False

    def handle_starttag(self, tag, attrs):
        if tag == 'dd':
            self.dd_flag = True

    def handle_data(self, data):
        if self.dd_flag:
            self.cities.append(data)
            self.dd_flag = False

    def getcities(self):
        return self.cities


class DanceClubParser(HTMLParser):
    clubs = []
    p_flag = False

    def handle_starttag(self, tag, attrs):
        if tag == 'p':
            self.p_flag = True

    def handle_data(self, data):
        if self.p_flag:
            self.clubs.append(data)
            self.p_flag = False

    def getclubs(self):
        return self.clubs


# useful functions, to keep code more readable
def is_month(x):
    """
    Tests whether given parameter is a month, either in numeric or month name form.

    :param x: str
    :return: True or False
    """

    months = ["Januar", "Jan", "Februar", "Feb", "März", "April", "Apr", "Mai", "Juni", "Juli",
              "August", "Aug", "September", "Sep", "Sept", "Oktober", "Okt", "November", "Nov", "Dezember", "Dez"]

    if x in months or (x.isdigit() and 1 <= int(x) <= 12):
        return True
    else:
        return False


def convert_to_string(mylist):
    """
    Converts a list to a string, the elements of which are separated by a space.

    :param mylist: a list to be converted to a string
    :return: string
    """

    return ' '.join(mylist)


def string_to_target(csvlist, target=None):
    """
    Converts csv_list to a string (via convert_to_string function), then passes it to target or to STDOUT.

    :param csvlist: a list of elements to be converted; name stems from its main function,
    to become an element of the csv output format.

    :param target: the chosen output file, default=None

    :return: None if no target is given; the string created from csvlist, ending with "," otherwise.
    """

    if target:
        return target.write(convert_to_string(csvlist))
    else:
        return print(convert_to_string(csvlist), end=",")


def argparsing():
    """
    A parser for commandline arguments.
    Returns a file object if specified via "-o", and a string object containing the query text.
    See the output of "dancerank.py -h" for help.

    :return: outputfile (file object), querytext (string)
    """

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                     description="Reads a string containing information about a dancing tournament "
                                                 "and returns a csv file.\n\n"
                                                 "Nota Bene:\n"
                                                 "The input string MUST NOT contain single quotation marks, "
                                                 "but should be surrounded by them.\n",

                                     epilog="EXIT VALUES\n"
                                            "0\tsuccess\n"
                                            "1\tabort by user\n"
                                            "2\tsyntax error\n"
                                            "3\tcouldn't parse string\n"
                                     )

    parser.add_argument("string", type=str, help="string containing dancing tournament information")
    parser.add_argument("-o", "--output", action="store", dest="output", help="specify csv output file")

    # content of parentheses is for debugging purposes only;
    # else also a text from Corpus/ may be used.
    try:
        parse_arguments = parser.parse_args(
#              ["""
# TATATA
#
# Am vergangenen Samstag fanden in Kelkheim zum 33. Mal die Taunus-Tanz-Tage statt.
# sodass nach der Vorrunde alle Paare in die Endrunde übernommen wurden.
# Guido und Doris Krams konnten in allen Tänzen als zweitbestes Paar überzeugen und somit den 2.Platz
# für sich entscheiden. Tanz-Club Schwarz-Silber Frankfurt bla
#             """, "-o", "/tmp/test.csv"]
        )
    except:
        parser.parse_args(["-h"])

    # noinspection PyUnboundLocalVariable
    # (can't be because of try-except-clause)
    _output = parse_arguments.output
    _querytext = parse_arguments.string
    outputfile = None

    # test whether user tries to overwrite existing file
    if parse_arguments.output:
        global opentype
        if os.path.isfile(_output):
            opentype = "a"
            print("Appending to file.")
            outputfile = open(_output, 'a')
        else:
            opentype = "w"
            outputfile = open(_output, 'w')

    return outputfile, _querytext


def cleantext(text):
    """
    Cleans text from special characters, and splits the input string into a list of words.

    :param text: string
    :return: list (of strings)
    """

    cleaned = []
    specials = r'.,_;:&()!?"/'
    for element in text:
        if element in specials:
            cleaned.append(re.sub(r'[.,_;:&()!?"/]', ' ', element))
        else:
            cleaned.append(element)

    _string = ''.join(cleaned)

    return _string.split()


def process_query(query):
    """
    Run Information Extraction methods on the query list.

    :param query: list of strings
    :return: list of tuples (element, IOB-tag)
    """

    # tagging of the query
    results = tagger.tag(query)

    # variables & constants
    sir = []
    lady = []
    club = []
    loc = []
    date = []
    rank = []

    # checking for german cities for the LOC tag
    wikiparser = WikiCityParser()
    url_e = "http://de.wikipedia.org/wiki/"+urllib.parse.quote("Liste_der_Städte_in_Deutschland")
    wiki_page = urllib.request.urlopen(url_e).read().decode('utf-8').rstrip('\n')
    wiki_content = wikiparser.feed(wiki_page)
    citylist = wikiparser.getcities()

    # checking for danceclubs for club recognition
    club_list= open('./Corpus/Tanzvereine', 'r')
    german_clubs = [line.rstrip('\n') for line in club_list if not line.startswith('#')]     # filter comments

    clubparser = DanceClubParser()
    url_2 = "http://htv.de/vereine/"
    htv_page = urllib.request.urlopen(url_2).read().decode('utf-8').rstrip('\n')
    htv_content = clubparser.feed(htv_page)
    hessian_clubs = clubparser.getclubs()

    clublist = set(german_clubs + hessian_clubs)

    year = str(datetime.datetime.now().year)
    ranking = re.compile(r'Platz|Stelle|Stufe|Rang')
    first = re.compile(r'erste[mnr]?', flags=re.IGNORECASE)
    second = re.compile(r'zweite[mnr]?', flags=re.IGNORECASE)
    third = re.compile(r'dritte[mnr]?', flags=re.IGNORECASE)

    # named entity recognition for couple's names, club, and tournament location
    for n in range(0, len(results)):
        if results[n][1] == 'O' and not sir and n < len(results) - 6:
            if 'PER' in results[n+1][1]:
                # in this case the couple is probably married
                if results[n+2][1] == 'O':
                    if 'PER' in results[n+3][1]:
                        if 'PER' in results[n+4][1]:
                            if results[n+5][1] == 'O':
                                sir.append(results[n+1][0])
                                sir.append(results[n+4][0])
                                lady.append(results[n+3][0])
                                lady.append(results[n+4][0])
                # looks for names of the kind "namea surnamea nameb surnameb"
                elif 'PER' in results[n+2][1]:
                    if 'PER' in results[n+3][1]:
                        if 'PER' in results[n+4][1]:
                            if results[n+5][1] == 'O':
                                sir.append(results[n+1][0])
                                sir.append(results[n+2][0])
                                lady.append(results[n+3][0])
                                lady.append(results[n+4][0])
                    # looks for "namea surnamea and nameb surnameb"
                    elif results[n+3][1] == 'O':
                        if 'PER' in results[n+4][1]:
                            if 'PER' in results[n+5][1]:
                                if results[n+6][1] == 'O':
                                    sir.append(results[n+1][0])
                                    sir.append(results[n+2][0])
                                    lady.append(results[n+4][0])
                                    lady.append(results[n+5][0])
        elif 'ORG' in results[n][1]:
            if not club and n < len(results) - 3:
                # Saves the elements tagged as 'ORG' in a separate list
                orgs = []
                for c in range(0, 4):
                    if 'ORG' in results[n+c][1]:
                        orgs.append(results[n+c][0])

                # Checks whether an element of orgs is a city
                city = None
                for org in orgs:
                    orgregex = re.compile(org)
                    if orgregex.search(convert_to_string(citylist)):
                      city = org

                if city:
                    # Counts the clubs that match the city
                    matchingclubs = []
                    for _club in clublist:
                        if city in _club:
                            matchingclubs.append(_club)

                    if len(matchingclubs) > 0:
                        isDanceclub = re.compile(r'[A-Z]{2,}|(C|club$)')
                        for _club in matchingclubs:
                            for org in orgs:
                                if org in _club and org is not city and not isDanceclub.search(org):
                                    club.append(_club)

        elif 'LOC' in results[n][1]:
            # compare with list of German cities
            locregex = re.compile(results[n][0])
            if locregex.search(convert_to_string(citylist)):
                loc.append(results[n][0])

        #elif results[n][0] in [_city for _city in citylist]:
        #    loc.append(results[n][0])

    # temporal event recognition and ranking recognition
    i = 0
    while i <= len(query) - 2:
        if query[i].isdigit() and is_month(query[i + 1]):
            if query[i + 2].isdigit():
                date.append([query[i], query[i + 1], query[i + 2]])
            else:
                date.append([query[i], query[i + 1], year])     # assume it's the current year
        elif ((first.match(query[i]) or query[i] == "1") and ranking.match(query[i+1])) or \
                (ranking.match(query[i]) and (first.match(query[i+1]) or query[i+1] == "1")):
            rank.append("1")
        elif ((second.match(query[i]) or query[i] == "2") and ranking.match(query[i+1])) or \
                (ranking.match(query[i]) and (second.match(query[i+1]) or query[i+1] == "2")):
            rank.append("2")
        elif ((third.match(query[i]) or query[i] == "3") and ranking.match(query[i+1])) or \
                (ranking.match(query[i]) and (third.match(query[i+1]) or query[i+1] == "3")):
            rank.append("3")
        elif query[i].isdigit() and ranking.match(query[i+1]):
            rank.append(query[i])
        elif ranking.match(query[i]) and query[i+1].isdigit():
            rank.append(query[i+1])
        i += 1

    # create new list of dates which stores the dates as strings instead of lists
    # this is to avoid errors with the convert_to_string function
    date = ['.'.join(x) for x in date]

    return sir, lady, club, loc, date, rank


def create_output(ranking, outfile=None):
    """
    Writes output created by process_query() either to STDOUT or to file.

    :param ranking:
    :param outfile: file object
    :return: csv formatted rows
    """

    couple_information = [convert_to_string(n) for n in ranking]
    if outfile is None:
        print(','.join(csv_header), end="\n")
        [print(x, end=",") for x in couple_information]
        print("\n")
    else:
        if not (opentype == 'a' or opentype == 'append'):
            csv.writer(outfile).writerows([csv_header, couple_information])
        else:
            csv.writer(outfile).writerows([couple_information])
        outfile.close()


if __name__ == '__main__':
    output, querytext = argparsing()
    cleaned_query = cleantext(querytext)
    result = process_query(cleaned_query)
    create_output(result, outfile=output)
