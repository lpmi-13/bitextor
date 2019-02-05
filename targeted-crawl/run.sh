

#xzcat www.samsonite.be.xz | ./import-mysql.py --out-dir out
#xzcat www.bizerba.com.xz | ./import-mysql.py --out-dir out

#BITEXTOR=/home/hieu/workspace/github/paracrawl/bitextor.malign
BITEXTOR=/home/hieu/workspace/github/paracrawl/bitextor.hieu.malign
xzcat www.samsonite.be.xz | $BITEXTOR/bitextor-warc2preprocess.py --output-dir out --lang1 en --lang2 fr
