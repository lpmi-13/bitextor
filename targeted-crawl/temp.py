#!/usr/bin/env python3

#sudo pip3 install mysql-connector-python
import mysql.connector

print("Starting")


mydb = mysql.connector.connect(
  host="localhost",
  user="paracrawl_user",
  passwd="paracrawl_password",
  database="paracrawl"
)

mycursor = mydb.cursor()

mycursor.execute("SHOW TABLES")

for x in mycursor:
  print(x)


print("Finished")
