#!/usr/bin/env python3

import alcazar.bodytext
import argparse
import base64
import cchardet
import ftfy
import hashlib
import html5lib
import magic
import re
import sys
import warc

from boilerpipe.extract import Extractor
from lxml.html.clean import Cleaner
from lxml.etree import ParserError
from lxml import etree
import pycld2 as cld2

#############################################################################
def decode(data):
  encoding = cchardet.detect(data)['encoding']
  if not encoding:
    return None
  data = data.decode(encoding)
  return data

#############################################################################

def guess_lang_from_data2(data):
  try:
    reliable, text_bytes, detected_languages = cld2.detect(
      data, isPlainText=False)
  except cld2.error:
    return "UNK"
  #print("detected_languages", detected_languages)
  return detected_languages[0][1]


# Inline tags that don't start on a new line and only take up as much width as necessary. From https://www.w3schools.com/html/html_blocks.asp
inline_tags = {"a", "abbr", "acronym", "b", "bdo", "big", "br", "button", "cite", "code", "dfn", "em", "i", "img",
               "input", "kbd", "label", "map", "object", "q", "samp", "script", "select", "small", "span", "strong",
               "sub", "sup", "textarea", "time", "tt", "var"}


def getElementText(element, document):
  """Returns a list with word plain text of a tree element of lxml and the corresponding text
  """
  # Return variables for plain text
  text = ""
  if element.text != None:  # If we have text in tag
    # Add interpreted space for non-inline tags
    if element.tag not in inline_tags:
      text = "\n"  # Add artificial separation as browser parser does if tag is not inline
    text = text + element.text

  # Now we recursively iterate through the childs
  for child in element:
    if type(child) is etree._Element and child.tag != "script" and child.tag != "style":
      text = text + getElementText(child, document)

  # Add interpreted space for non-inline tags after all processing of the actual tag content
  if element.tag not in inline_tags:
    text = text + "\n"
  elif element.tag == "br":
    text = text + "\n"

  # Processing parent text (A.K.A. element.tail) similarly as the actual tag
  if element.tail != None:  # If we have tail parent text (text after the closing tag until the next open/close tag)
    text = text + element.tail

  return text


def getDocumentText(document):
  """Returns a list with word plain text of a document tree in lxml format
  """
  docplaintext = ""
  for element in document.getroot():
    if type(
            element) is etree._Element and element.tag != "script" and element.tag != "style":  # Only elements, not scripts or other kind of tags without proper text
      docplaintext = docplaintext + getElementText(element, document)
  return docplaintext

def guess_lang_from_data2(data):
  try:
    reliable, text_bytes, detected_languages = cld2.detect(
      data, isPlainText=False)
  except cld2.error:
    return "UNK"
  #print("detected_languages", detected_languages)
  return detected_languages[0][1]


parser = argparse.ArgumentParser(description='Convert warc to lett')
parser.add_argument("-l", "--languages", help="List accepted languages represented as a comma separated language codes list", dest="langlist", default=None)
args = parser.parse_args()

if args.langlist != None:
  langs=args.langlist.strip().split(",")

m=magic.open(magic.MAGIC_NONE)
m.load()

f = warc.WARCFile(fileobj=sys.stdin.buffer)
seen_md5={}

lineNum = 0
for record in f:
  html  = record.payload.read() #.decode('utf8')

  if len(html) > 0:
    try:
      html = decode(html)
      if not html: 
        sys.stderr.write("Failed to detect encoding: " + record.url + "\n")
        sys.stderr.flush()
        continue
    except UnicodeDecodeError:
      sys.stderr.write("Unicode error: " + record.url + "\n")
      sys.stderr.flush()
      continue
 
    # lang id
    lang = guess_lang_from_data2(html)
    if not lang in langs:
      continue
    
        
    encoded_html = html.encode("utf8")

    # Need the following fields:
    # - language
    # - mimencoding (2 fields)
    # - url 
    # - filename?
    # - text
    # - deboiled html

    #We compute MD5 signature to compare files and detect duplicates
    c = hashlib.md5()
    c.update(encoded_html)
    hexdigest = c.hexdigest()
    if hexdigest in seen_md5:
      continue

    seen_md5[hexdigest] = True

    # normalize html
    cleaner=Cleaner(style=True, links=True, add_nofollow=True,page_structure=False, safe_attrs_only=False)
    try:
      cleanhtml = cleaner.clean_html(re.sub(r'encoding *= *"[^"]+"', '', html, flags=re.IGNORECASE))
    except ParserError:
      sys.stderr.write("lxml parse error: " + record.url + "\n")
      continue
    document = html5lib.parse(ftfy.fix_text(cleanhtml), treebuilder="lxml", namespaceHTMLElements=False)
    tree = etree.tostring(document)
    cleantree = tree.decode("utf8")
    cleantree = cleantree.replace("\t", " ")

    extractor = Extractor(extractor='ArticleExtractor', html=cleantree)
    deboiled_text = extractor.getHTML()


    # Mime
    m.setflags(16|1024)
    mimeEncode = m.buffer(encoded_html).split(" ")
    mimeEncode[0] = mimeEncode[0][:-1]

    # Text
    text = alcazar.bodytext.parse_article(cleantree)
    if text.body_text:
      text = text.body_text
    else:
      text = ""
 
      
    encoded_html = base64.b64encode(deboiled_text.encode('utf8')).decode("utf8")
    encoded_text = base64.b64encode(text.encode("utf8")).decode("utf8")
    print("\t".join([lang,mimeEncode[0],mimeEncode[1],record.url,encoded_html,encoded_text]))


