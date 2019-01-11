#!/usr/bin/env python3

import warc
import base64
import sys
import argparse
import cchardet

#############################################################################
def convert_encoding(data, new_coding = 'UTF-8'):
  encoding = cchardet.detect(data)['encoding']
  if not encoding:
    return None
  #sys.stderr.write("convert " + encoding + " to " + new_coding + "\n")

  if new_coding.upper() != encoding.upper():
    #sys.stderr.write("convert " + encoding + " to " + new_coding + "\n")
    data = data.decode(encoding).encode(new_coding)

  #print(data", type(data))
  return data

#############################################################################

parser = argparse.ArgumentParser(description='Extract html from warc files')
parser.add_argument('--output-dir', dest='outDir', help='Output directory')
args = parser.parse_args()
#print("outDir", args.outDir)

f = warc.WARCFile(fileobj=sys.stdin.buffer)

lineNum = 0
for record in f:
    #sys.stderr.write("lineNum " + str(lineNum) \
    #                 + " " + record.url \
    #                 + " " + record.date + "\n")

    text = record.payload.read() #.decode('utf8')
    #sys.stderr.write("text" + str(len(text)) + "\n")

    if len(text) > 0:
        try:
          text = convert_encoding(text)
          if not text: 
            sys.stderr.write("Failed to detect encoding: " + record.url + "\n")
            sys.stderr.flush()
            continue

        # write file
          file = open("{outDir}/{name}.html".format(outDir=args.outDir, name=lineNum), "wb")
          file.write(text)
          file.close()
        except UnicodeDecodeError:
          sys.stderr.write("Unicode error: " + record.url + "\n")
          sys.stderr.flush()
          continue


        file = open("{outDir}/{name}.metadata".format(outDir=args.outDir, name=lineNum), "w")
        file.write(record.url + "\t" + record.date)
        file.close()

        lineNum += 1
