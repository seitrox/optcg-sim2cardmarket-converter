# OPTCG sim2cardmarket converter

This repository contains 2 parts
* the scraper to get the card data
* a smal website that allows to convert from sim format to cardmarket format

to use head over to [https://seitrox.github.io/optcg-sim2cardmarket-converter/](https://seitrox.github.io/optcg-sim2cardmarket-converter/)

## the scraper

This scraper automatically scrapes https://en.onepiece-cardgame.com/cardlist in order to get all currently available cards.
output of the scraper should be 3 files.  
1x nicely formatted txt file with pretty much all the data on the cards.  
1x the same file but in csv.  
1x a condensed version of the csv, only using the id and the cardname, also filtering out duplicates(alternate art cards)  

This scraper saves the HTML of the individual sets (like op01,op02 etc) and only redownloads them if some time has passed (1 hour), can be changed in code.  

### Prerequesits

* python 3  
* pip

### How to use 

first create a venv

```bash
python -m venv venv
```

Activate the venv and then install the needed packages from requirements.txt
```bash
source venv/bin/activate
pip install -r requirements.txt
```

once this is done sucesfully, just run `scraper.py` 
```bash
python scraper.py
```

if the scraper ran without any further issues, you should now have a `results` folder with the 3 files