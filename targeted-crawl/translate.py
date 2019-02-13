#!/usr/bin/env python3

import os
import sys
import argparse
import mysql.connector

oparser = argparse.ArgumentParser(description="Hello")
oparser.add_argument('--dir', dest='dir', help='Data directory', required=True)
options = oparser.parse_args()

mydb = mysql.connector.connect(
    host="localhost",
    user="paracrawl_user",
    passwd="paracrawl_password",
    database="paracrawl",
    charset='utf8'
)

mycursor = mydb.cursor()

for fileName in os.listdir(options.dir):
    if fileName[-8:] != ".text.xz":
        continue

    filePrefix = fileName[:-8]
    fileId = int(filePrefix)
    translatedFile = filePrefix + ".trans"
    print("fileName", fileName, filePrefix, fileName[-8:], translatedFile)

    # translated already?
    if os.path.isfile(translatedFile):
        continue

    # what language is it in?
    sql = "SELECT lang FROM document WHERE id = %s"
    val = (fileId,)
    mycursor.execute(sql, val)
    res = mycursor.fetchone()
    assert(res != None)
    lang = res[0]
    print("lang", lang)
