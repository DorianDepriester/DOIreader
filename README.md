# DOIreader
Python script to retrieve bibliographic data from a list of DOIs

## Purpose
Collecting data about numerous articles and papers can be very time consuming and tedious. One way to do it in an automatic and reproducible way is to use the Digital Object Identifiers (DOIs) usually associated with such materials.

This script reads a list of DOIs from a text file, and generates a table (Pandas' dataframe) gathering all relevant data (e.g. title, date, authors etc.). This table can then eventually be exported in a an Excel file for further analyses.

## Features
Efforts have been made to track ambiguous duplicates (Is George Abitbol the same author as G. Abitbol?). This script also formats the author names with respect to your needs (change order, abbreviate names, capitalize etc.).
