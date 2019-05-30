from ubuntu:18.04

RUN apt-get update && \
    apt-get install -y cmake automake pkg-config python3 python3-pip \
    libboost-all-dev openjdk-8-jdk liblzma-dev time git httrack

COPY . ./bitextor

WORKDIR /bitextor

RUN git submodule update --init --recursive

RUN pip3 install -r requirements.txt && \
    pip3 install -r bicleaner/requirements.txt https://github.com/vitaka/kenlm/archive/master.zip && \
    pip3 install -r restorative-cleaning/requirements.txt 

RUN ./autogen.sh && make

#RUN wget https://github.com/bitextor/bitextor-data/releases/download/bitextor-v1.0/en-el.dic

CMD ["bash"]
