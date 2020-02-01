import re
from os import walk

for (dirpath, dirnames, filenames) in walk("../scraper/upi_articles"):
    for file in filenames:
        with open("../scraper/upi_articles/"+file, "r+", encoding="utf-8") as f:
            text = re.sub(r"\s+", " ", f.read())
            f.seek(0)
            f.truncate()
            f.write(text)
    break

for (dirpath, dirnames, filenames) in walk("../scraper/cnbc_articles"):
    for file in filenames:
        with open("../scraper/cnbc_articles/"+file, "r+", encoding="utf-8") as f:
            text = re.sub(r"\s+", " ", f.read())
            f.seek(0)
            f.truncate()
            f.write(text)
    break

for (dirpath, dirnames, filenames) in walk("../scraper/reuters_articles"):
    for file in filenames:
        with open("../scraper/reuters_articles/"+file, "r+", encoding="utf-8") as f:
            text = re.sub(r"\s+", " ", f.read())
            f.seek(0)
            f.truncate()
            f.write(text)
    break
	
for (dirpath, dirnames, filenames) in walk("../scraper/forbes_articles"):
    for file in filenames:
        with open("../scraper/forbes_articles/"+file, "r+", encoding="utf-8") as f:
            text = re.sub(r"\s+", " ", f.read())
            f.seek(0)
            f.truncate()
            f.write(text)
    break

