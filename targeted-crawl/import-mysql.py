#!/usr/bin/env python3
# xzcat www.samsonite.be.xz | ./import-mysql.py  --out-dir out --lang1 en --lang2 fr

#sudo pip3 install mysql-connector-python
import mysql.connector
import warc
import sys
import cchardet
import logging
import re
import html5lib
import ftfy
import argparse
import hashlib
import magic
import base64
import html
import lzma
import urllib
import subprocess
import pycld2 as cld2
from lxml.html.clean import Cleaner
from lxml import etree
from bs4 import BeautifulSoup

######################################################################################
def guess_lang_from_data2(data):
    reliable, text_bytes, detected_languages = cld2.detect(
        data, isPlainText=False)
    return detected_languages[0][1]

######################################################################################
def convert_encoding(data):
    encoding = cchardet.detect(data)['encoding']

    if len(data) > 0:
        #We convert, even if the text is detected to be UTF8 so, if it is an error and conversion fails, the error is catched here
        for enc in [encoding, 'utf-8', 'iso-8859-1', 'windows‑1252']:
            try:
                return (enc,data.decode(enc))
            except UnicodeDecodeError:
                pass

    return (None,'')
######################################################################################
def strip_scheme(url):
    parsed = urllib.parse.urlparse(url)
    scheme = "%s://" % parsed.scheme
    return parsed.geturl().replace(scheme, '', 1)
######################################################################################

print("Starting")

oparser = argparse.ArgumentParser(description="Script that takes every record in a WARC file and runs preprocessing, which includes: HTML normalization, deduplication, MIME and language identification, and boilerplate removing. The result of each pre-processing step is stored in a XZ compressed file in the output directory.")
oparser.add_argument("--boilerpipe", action="store_true", default=False, help="Use boilerpipe bodytext to do the de-boiling")
oparser.add_argument("--alcazar", action="store_true", default=False, help="Use alcazar bodytext extract relevant text from HTML. By default BeautifulSoup4is used")
oparser.add_argument('--lang1', dest='l1', help='Language l1 in the crawl', default=None)
oparser.add_argument('--lang2', dest='l2', help='Language l2 in the crawl', default=None)
oparser.add_argument('--out-dir', dest='outDir', help='Output directory', required=True)
options = oparser.parse_args()

languages=[]
if options.l1 != None:
    languages.append(options.l1)
if options.l2 != None:
    languages.append(options.l2)


mydb = mysql.connector.connect(
    host="localhost",
    user="paracrawl_user",
    passwd="paracrawl_password",
    database="paracrawl",
    charset='utf8'
)

mycursor = mydb.cursor()

#mycursor.execute("SHOW TABLES")
#for x in mycursor:
#  print(x)

f = warc.WARCFile(fileobj=sys.stdin.buffer)
seen_md5={}
magic.Magic(mime=True)

mtProc = subprocess.Popen(["/home/hieu/workspace/experiment/issues/paracrawl/phi-system/translate-pipe.sh",
                         "fr"
                         ],
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE)
numPages = 0
for record in f:
    numPages += 1
    if numPages % 100 == 0:
        print("write", numPages)
        mydb.commit()

    #We convert into UTF8 first of all
    orig_encoding,html_text = convert_encoding(record.payload.read())
    pageURL=record.url

    if pageURL == "unknown":
        logging.info("Unknown page url")
        continue

    if orig_encoding == None:
        logging.info("Encoding of document " + pageURL + " could not be identified")

    if len(html_text) == 0:
        logging.info("Empty page")
        continue

    # HTML is then normalized
    cleaner = Cleaner(style=True, links=True, add_nofollow=True, page_structure=False, safe_attrs_only=False)

    cleanhtml = cleaner.clean_html(re.sub('encoding *= *"[^"]+"', '', html_text, flags=re.IGNORECASE))
    document = html5lib.parse(ftfy.fix_text(cleanhtml), treebuilder="lxml", namespaceHTMLElements=False)
    tree = etree.tostring(document)
    cleantree = tree.decode("utf8").replace("&#160;", " ")
    cleantree = cleantree.replace("\t", " ")

    # lang id
    lang = guess_lang_from_data2(cleantree)
    if len(languages)>0 and lang not in languages:
        logging.info("Language of document "+pageURL+": "+lang+". Not among searched languages.")
        continue

    #If enabled, remove boilerplate HTML
    if options.boilerpipe:
        extractor = Extractor(extractor='ArticleExtractor', html=cleantree)
        deboiled = extractor.getHTML()
    else:
        deboiled = cleantree

    #We compute MD5 on the HTML (either normalized one or after boilerpipe if enabled): if we get duplicate files we discard them
    c = hashlib.md5()
    c.update(deboiled.encode())

    hash = c.hexdigest()
    #print("c", hash)

    sql = "SELECT id FROM document WHERE md5 = %s"
    val = (hash,)
    mycursor.execute(sql, val)
    res = mycursor.fetchone()
    print("page", res, hash, pageURL)

    #checking for duplicate content (duplicates are discarded)
    if res is not None:
        # duplicate page
        docId = res[0]

        sql = "SELECT id, document_id FROM url WHERE val = %s"
        val = (pageURL, )
        mycursor.execute(sql, val)
        res = mycursor.fetchone()

        if res is not None:
            # url exists
            if res[1] is None:
                sql = "UPDATE url SET document_id = %s WHERE val = %s"
                val = (docId, pageURL)
                mycursor.execute(sql, val)
            else:
                assert(res[1] == docId)
        else:
            sql = "INSERT INTO url(val, document_id) VALUES (%s, %s)"
            #print("url1", pageURL)
            val = (pageURL, int(docId))
            mycursor.execute(sql, val)

        continue

    # new doc
    if options.alcazar:
        # get text with Alcazar library
        btext = alcazar.bodytext.parse_article(cleantree)
        if btext.body_text:
            plaintext = btext.body_text
        else:
            plaintext = ""
    else:
        # use beautifulsoup
        if options.boilerpipe:
            soup = BeautifulSoup(deboiled, "lxml")
        else:
            soup = BeautifulSoup(cleantree, "lxml")
        for script in soup(["script", "style", "img"]):
            script.extract()    # rip it out

        plaintext = soup.get_text()
        plaintext = re.sub(r"\n+","\n",re.sub(r" *\n *","\n",re.sub(r" +"," ",re.sub(r"\r","", plaintext))))

    if len(plaintext) == 0:
        # empty doc. Should we still go thru links anyway?
        continue

    #Guessing MIME of the file (checked on original content)
    mime=magic.from_buffer(html_text, mime=True)
    #mimeFile.write(mime.encode()+b"\n")

    #urlFile.write(url.encode()+b"\n")
    #langFile.write(lang.encode()+b"\n")
    #encodingFile.write(orig_encoding.encode()+b"\n")

    norm_html = cleantree.encode()
    b64norm=base64.b64encode(norm_html)
    #normHtmlFile.write(b64norm+b"\n")

    if options.boilerpipe:
        b64deboil=base64.b64encode(deboiled.encode())
        #deboilFile.write(b64deboil+b"\n")

    b64text=base64.b64encode(html.unescape(plaintext).encode())
    #plainTextFile.write(b64text+b"\n")
    #print("{0}\t{1}\t{2}\t{3}\t{4}".format(lang, orig_encoding, mime, b64norm.decode("utf-8"), b64text.decode("utf-8")))

    sql = "INSERT INTO document(mime, lang, md5) VALUES (%s, %s, %s)"
    val = (mime, lang, hash)
    #print("val", type(val))
    mycursor.execute(sql, val)
    docId = mycursor.lastrowid

    sql = "SELECT id, document_id FROM url WHERE val = %s"
    val = (pageURL, )
    mycursor.execute(sql, val)
    res = mycursor.fetchone()

    if res is not None:
        # url exists
        assert(res[1] == None)
        sql = "UPDATE url SET document_id = %s WHERE val = %s"
        val = (int(docId), pageURL)
        mycursor.execute(sql, val)
    else:
        sql = "INSERT INTO url(val, document_id) VALUES (%s, %s)"
        #print("url1", pageURL)
        val = (pageURL, int(docId))
        mycursor.execute(sql, val)
    #print(html_text)

    # links
    soup = BeautifulSoup(html_text, features="lxml")
    for link in soup.findAll('a'):
        url = link.get('href')

        if url is not None:
            linkStr = link.string

            url = urllib.parse.unquote(url)
            url = urllib.parse.urljoin(pageURL, url)
            url = strip_scheme(url)
            #print("url3", url)

            imgURL = link.find('img')
            if imgURL:
                imgURL = imgURL.get('src')
            else:
                imgURL = None

            #print("link", url, " ||| ", linkStr, " ||| ", imgURL)

            # does url already exist?
            sql = "SELECT id FROM url WHERE val = %s"
            val = (url, )
            mycursor.execute(sql, val)
            res = mycursor.fetchone()
            #print("res", res, hash, url)

            if (res is not None):
                urlId = res[0]
            else:
                sql = "INSERT INTO url(val) VALUES(%s)"
                val = (url, )
                mycursor.execute(sql, val)
                urlId = mycursor.lastrowid

            #print("urlId", urlId)

            sql = "INSERT INTO link(text, hover, image_url, document_id, url_id) VALUES(%s, %s, %s, %s, %s)"
            val =(str(linkStr), "hover here", str(imgURL), int(docId), int(urlId))
            mycursor.execute(sql, val)

    # write html and text files
    filePrefix = options.outDir + "/" + str(docId)

    with lzma.open(filePrefix + ".html.xz", "wt") as htmlFile:
        htmlFile.write(html_text)
    with lzma.open(filePrefix + ".norm.xz", "wt") as normHtmlFile:
        normHtmlFile.write(norm_html.decode("utf-8"))
    with lzma.open(filePrefix + ".text.xz", "wt") as textFile:
        textFile.write(plaintext)

    # split
    inLines = plaintext.split("\n")
    if len(inLines[-1]) == 0:
        del inLines[-1]

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

    # write splitted file
    extractPath = options.outDir + "/" + str(docId) + "." + lang + ".extracted.xz"
    with lzma.open(extractPath, 'wt') as extractFile:
        for extractedLine in extractedLines:
            extractFile.write(str(docId) + "\t" + extractedLine + "\n")

    if lang == "fr":
        # translate
        transPath = options.outDir + "/" + str(docId) + ".trans.xz"
        transFile = lzma.open(transPath, 'wt')

        for inLine in extractedLines:
            # print("inLine", inLine)
            inLine += "\n"
            mtProc.stdin.write(inLine.encode('utf-8'))
            mtProc.stdin.flush()
            outLine = mtProc.stdout.readline()
            outLine = outLine.decode("utf-8")
            transFile.write(str(docId) + "\t" + outLine)

        transFile.close()

    # doc align
    if lang == "en":
        otherLang = "fr"
    else:
        otherLang = "en"

    sql = "SELECT id FROM document WHERE lang=%s"
    val = (otherLang,)
    mycursor.execute(sql, val)
    res = mycursor.fetchall()
    #print("res", res)

    for rec in res:
        otherDocId = rec[0]
        #print("other doc id", otherDocId)

        #cmd = "/home/hieu/workspace/github/paracrawl/bitextor.hieu.malign/document-aligner/compute_matches.py --lang1 {input1} --lang2 {input2} --output_matches {output} --threshold {DOC_THRESHOLD} --word_tokeniser '{WORDTOK1}'".format(input1=, input2=, output=, DOC_THRESHOLD=0.2, WORDTOK1="")




# everything done
# commit in case there's any hanging transactions
mydb.commit()

print("Finished")
