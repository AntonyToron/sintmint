# SintMint
## Overview
Ever been curious about what the general sentiment about a person or place is? SintMint creates a simple way to search for any person, place, or idea and see what the general sentiment is online. It is currently hosted on https://sintmint.herokuapp.com/. You will be greeted by a page like:
![Screenshot from 2021-11-29 02-12-55](https://user-images.githubusercontent.com/16731832/143824035-6840dadf-ea8d-4dbe-8401-f73aced59bfe.png)

## Implementation
SintMint scrapes the top search results on Google and follows the the top N links, scraping the valuable information from the page. It then sends this off to Google's Natural Language Processing API to analyze the content within. It looks for:
- sentiment of the entities that Google found on content
- sentiment of the overall document
- sentiment of the individual sentences within the document
It then combines these three, using the individual magnitudes of each (i.e. how strong of a signal each one Google thinks is), with a bit of filtering on erroneous results. In the end, you should get something like:
![Screenshot from 2021-11-29 02-12-26](https://user-images.githubusercontent.com/16731832/143823965-8a199982-5f02-4b89-aac7-fc10ef4d4e84.png)
