#!/usr/bin/env python3

import os
import sys
import argparse
import mysql.connector
import lzma
import socket
import subprocess

###########################################################
def systemCheck(cmd):
    sys.stderr.write("Executing:" + cmd + " on " + socket.gethostname() + "\n")
    sys.stderr.flush()

    subprocess.check_call(cmd, shell=True)
###########################################################

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

# cmd = "xzcat " + txtPath + " | ~/workspace/github/mosesdecoder/bin/moses2 -f /home/hieu/workspace/experiment/issues/paracrawl/fr-en/smt-dir/model/moses.bin.ini.1"
# systemCheck(cmd)
mtProc = subprocess.Popen(["/home/hieu/workspace/experiment/issues/paracrawl/phi-system/translate-pipe.sh",
                         "fr"
                         ],
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE)

enSplitProc = subprocess.Popen(["/home/hieu/workspace/github/mosesdecoder/scripts/ems/support/split-sentences.perl",
                                "-b",
                                "-l", "en"],
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE)


for fileName in os.listdir(options.dir):
    if fileName[-8:] != ".text.xz":
        continue

    filePrefix = fileName[:-8]
    fileId = int(filePrefix)
    translatedFile = filePrefix + ".trans"
    #print("fileName", fileName, filePrefix, fileName[-8:], translatedFile)

    # what language is it in?
    sql = "SELECT lang FROM document WHERE id = %s"
    val = (fileId,)
    #print("fileId", fileId)
    mycursor.execute(sql, val)
    res = mycursor.fetchone()
    assert(res != None)
    lang = res[0]

    if lang not in ["en", "fr"]:
        continue

    # read input
    txtPath = options.dir + "/" + fileName
    with lzma.open(txtPath, 'rt') as f:
        inLines = f.read()
        inLines = inLines.split("\n")
        if len(inLines[-1]) == 0:
            del inLines[-1]
    print("fileName", fileName, filePrefix, fileName[-8:], translatedFile, lang, len(inLines))

    # split
    extractedLines = []
    for inLine in inLines:
        #print("inLine", inLine)
        #inLine += "\n"

        frSplitProc = subprocess.Popen(
            ["/home/hieu/workspace/github/mosesdecoder/scripts/ems/support/split-sentences.perl",
             "-b",
             "-l", "fr"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        cout, cerr = frSplitProc.communicate(input=inLine.encode('utf-8'))

        splittedLines = cout.decode("utf-8")
        splittedLines = splittedLines[0:-1].split("\n")
        #print("splittedLines", inLine, splittedLines)
        extractedLines += splittedLines

    extractPath = options.dir + "/" + str(fileId) + "." + lang + ".extracted.xz"
    with lzma.open(extractPath, 'wt') as extractFile:
        for extractedLine in extractedLines:
            extractFile.write(extractedLine + "\n")

    if lang != "fr":
        continue

    # translate
    transPath = options.dir + "/" + str(fileId) + ".trans.xz"
    transFile = lzma.open(transPath, 'wt')

    for inLine in extractedLines:
        #print("inLine", inLine)
        inLine += "\n"
        mtProc.stdin.write(inLine.encode('utf-8'))
        mtProc.stdin.flush()
        outLine = mtProc.stdout.readline()
        outLine = outLine.decode("utf-8")
        transFile.write(outLine)

    transFile.close()

    # doc align
    for enId in [1, 2, 3]:
        inputL1 = "{docId}.trans.xz".format(docId=fileId)
        inputL2 = "{docId}.text.xz".format(docId=endId)
        cmd = "/home/hieu/workspace/github/paracrawl/bitextor.hieu.malign/document-aligner/compute_matches.py --lang1 {inputL1} --lang2 {inputL2} --output_matches {output} --threshold {DOC_THRESHOLD} --word_tokeniser '{WORDTOK1}'"



    #exit()
