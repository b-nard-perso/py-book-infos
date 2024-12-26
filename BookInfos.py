#
# Credits
# https://jevalide.ca/2024/03/24/bibliographie-avec-python-depuis-une-liste-de-livres/
# Voir aussi
# https://www.data-bird.co/blog/web-scraping-python
#
# Ref https://pypi.org/project/isbnlib/
#
# Idea of hmtl-requests for sites based on javascript
# https://stackoverflow.com/questions/27652543/how-can-i-use-pythons-requests-to-fake-a-browser-visit-a-k-a-and-generate-user
#
# Clipboard:
# https://stackoverflow.com/questions/101128/how-do-i-read-text-from-the-windows-clipboard-in-python

import isbnlib
import pandas as pd
from tqdm import tqdm
import requests
from requests_html import HTMLSession
#from requests_html import HTMLSession
from bs4 import BeautifulSoup
import sys
from selenium import webdriver
import time
import unicodedata
import tkinter as tk


def normalize_string(s: str) -> str:
    """
    Normalize a string by removing accents and converting to lowercase
    :param s: str input string
    :return: str normalized string
    """
    # Normalize the string
    normalized = unicodedata.normalize('NFD', s)
    # Suppress accents
    no_accents = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    # Convert to lowercase
    return no_accents.lower()

def make_string_search(s_title: str, s_author: str) -> str:
    """
    Make a string to search for a book
    :param s_title: str title of the book
    :param s_author: str author of the book
    :return: str search string
    """
    s_search = s_title if s_author == '' else f"{s_title} {s_author}"
    s_search = s_search.replace(' ', '+')
    s_search = s_search.replace("'", '%27')
    return s_search

class BookInfos:

    def __init__(self):
        # Label names for the dataframe's columns
        self.db_id = 'id'
        self.db_isbn = 'ISBN'
        self.db_title = 'Titre'
        self.db_editor = "Editeur"
        self.db_autor = "Auteur"
        self.db_number = "Nombre"
        # Ref database
        self.db_reference = pd.DataFrame()
        # Output directory
        self.output_dir = '../Export'
        self.verbose = 1
        # Search options
        # Credits
        # https://stackoverflow.com/questions/70750155/how-to-keep-my-user-agent-headers-always-up-to-date-in-my-python-codes
        driver = webdriver.Chrome()
        self.user_agent = driver.execute_script("return navigator.userAgent")
        self.delay_seconds = 2
        driver.quit()
        if self.verbose > 0:
            print(f"user_agent = {self.user_agent}")

    def fetch_reference_database(self, filename: str = "Rqt_Livres_Actifs") -> pd.DataFrame:
        """
        Fetch reference database from an Excel file
        
        Args:
        filename: str
        
        Returns:
        pd.DataFrame: reference database
        """
        self.db_reference = pd.read_excel(
            f"{self.output_dir}/{filename}.xlsx"
        )
        if self.verbose > 0:
            print(f"Reference database loaded from {filename}.xlsx")
        return self.db_reference
    
    def compare_with_reference_database(
            self, 
            df: pd.DataFrame,
            out_cols: list[str] = ['Nombre', 'Destination']
        ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Compare the DataFrame with the reference database
        
        Args:
        df: pd.DataFrame, 
        out_cols: list of columns to keep for the output.
        
        Returns:
        pd.DataFrame: DataFrame with book information
        """
        # Normalize the title strings
        title_low = 'title_low'
        number_request = self.db_number + '_request'
        self.db_reference[title_low] = self.db_reference[self.db_title].apply(normalize_string)
        df[title_low] = df[self.db_title].apply(normalize_string)
        # Select the books that are already in the reference database
        df_existing =  self.db_reference[
            # self.db_reference[title_low].isin(df[title_low]),
            ['id', self.db_title, self.db_number, title_low]
        ].set_index(title_low).join(
            df[[title_low] + out_cols].set_index(title_low),
            rsuffix='_request',
            how='inner'
        ).reset_index().drop(columns=title_low)
        df_existing[self.db_number] = df_existing[number_request] - df_existing[self.db_number]
        df_existing = df_existing.loc[df_existing[self.db_number] > 0].drop(columns=number_request)
        # Select the books that are not in the reference database
        df_new = df.loc[
            ~df[title_low].isin(self.db_reference[title_low])
        ].drop(columns=title_low)
        # Add a column with a link to help find the book
        df_new["URL"] = [
            f"https://www.fnac.com/SearchResult/ResultList.aspx?SCat=0%211&Search={make_string_search(x, y)}+poche&sft=1&sa=0" 
            for x, y in zip(df_new[self.db_title], df_new['Nom'])
        ]

        # save the data
        self.export_to_excel(df_existing, 'existing_books')
        self.export_to_excel(df_new, 'new_books')
        
        if self.verbose > 0:
            print('Comparison with reference database completed')
        return df_existing, df_new
    
    def fetch_book_info_from_isbn(self, isbn_list: list[str]) -> pd.DataFrame:
        """
        Fetch book information from a list of ISBN
        
        Args:
        isbn_list: list of ISBN

        Returns:
        pd.DataFrame: DataFrame with book information
        """
        isbn_meta = []
        # isbn_list = isbn_list[:50]
        for x in tqdm(isbn_list, desc='Fetching book information', file=sys.stdout):
            try:
                isbn_meta_item = isbnlib.meta(x)
                isbn_meta.append(isbn_meta_item)
            except Exception as e:
                isbn_meta.append({})
        
        df_books = pd.DataFrame(isbn_meta)
        rename_dict = {
            'id': self.db_id,
            'ISBN-13': self.db_isbn,
            'Title': self.db_title,
            'Publisher': self.db_editor,
            'Author': self.db_autor
        }
        df_books = df_books.rename(columns=rename_dict)
        df_books["URL]"] = [
            f"https://search.worldcat.org/fr/search?q={isbn}&offset=1" for isbn in df_books[self.db_isbn]
        ]
        df_books["description"] = [isbnlib.desc(x) for x in isbn_list]
        df_books[self.db_isbn] = df_books[self.db_isbn].apply(str)

        if self.verbose > 0:
            print('Research and data retrieval completed')
            if self.verbose > 2:
                print(df_books)
        return df_books
    
    def fetch_book_infos(
        self, 
        book_titles: list[str], 
        filename_out: str = ''
    ) -> pd.DataFrame:
        """
        Fetch book information from a list of book titles
        
        Args:
        book_titles: list of book titles
        filename_out: str ; name of the output file, if empty, no output file
        
        Returns:
        pd.DataFrame: DataFrame with book information
        """
        # Since the process is slow, we will use a progress bar
        # instead of
        # isbn_list = [isbnlib.isbn_from_words(x) for x in book_titles]
        for x in tqdm(book_titles, desc='Fetching ISBN', file=sys.stdout):
            try:
                isbn = isbnlib.isbn_from_words(x)
                if isbn is not None:
                    isbn_list.append(isbn)
            except Exception as e:
                pass
        # Get all the editions of the books
        isbn_list_likes = [isbnlib.editions(x) for x in isbn_list]
        isbn_list = sum(isbn_list_likes, [])    
        isbn_list = list(set(isbn_list))
        if self.verbose > 2:
            print(isbn_list)
        isbn_list_clean = [isbnlib.clean(x) for x in isbn_list if x is not None]
        
        df_books = self.fetch_book_info_from_isbn(isbn_list_clean)

        if self.verbose > 0:
            print('Research and data retrieval completed')
            if self.verbose > 2:
                print(df_books)
        df_books = df_books.sort_values(by=self.db_title)
        if filename_out != '':
            self.export_to_excel(df_books, filename_out)
        return df_books
    
    def export_to_csv(self, df: pd.DataFrame, filename: str):
        """
        Export DataFrame to CSV
        
        Args:
        df: pd.DataFrame
        filename: str
        """
        df.to_csv(
            f"{self.output_dir}/{filename}.csv", 
            index=False,
            sep=';'
        )
        if self.verbose > 0:
            print(f"File {filename}.csv exported to {self.output_dir}")

    def export_to_excel(self, df: pd.DataFrame, filename: str):
        """
        Export DataFrame to Excel
        
        Args:
        df: pd.DataFrame
        filename: str
        """
        df.to_excel(
            f"{self.output_dir}/{filename}.xlsx", 
            index=False
        )
        if self.verbose > 0:
            print(f"File {filename}.xlsx exported to {self.output_dir}")

    def fetch_book_info_from_fnac(
            self, 
            book_title: str,
            through_google: bool = False
        ):
        """
        Get book information from the FNAC website
        
        Args:
        book_title: str
        
        Returns:
        dict: book information
        """
        book_title = book_title.replace(' ', '+')
        book_title = book_title.replace("'", '%27')
        if through_google:
            url = f"https://www.bing.com/search?q=livre+poche+{book_title}+prix+fnac"
        else:     
            url = f"https://www.fnac.com/SearchResult/ResultList.aspx?SCat=0%211&Search={book_title}+poche&sft=1&sa=0"
        if self.verbose > 0:
            print(f"url = {url}")

        # Add headers to simulate a browser visit
        # https://www.zenrows.com/blog/403-web-scraping#complete-your-headers
        headers = {
            'User-Agent': 
            self.user_agent,
            "authority": "www.google.com",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "cache-control": "max-age=0"
        }
        s = HTMLSession() #requests.Session()
        response = s.get(
            url, 
            headers=headers
        )
        if response.status_code != 200:
            print(f"Failed to retrieve data: {response.status_code}")
            return {}
        # Add a delay to avoid being blocked
        time.sleep(self.delay_seconds)

        soup = BeautifulSoup(response.text, 'html.parser')

        book_info = {
            'title': None,
            'author': None,
            'publisher': None,
            'isbn': None,
            'price': None
        }

        if through_google:
            # Parsing logic for Bing search results
            # This part needs to be implemented based on the actual HTML structure of the Bing search results
            pass
        else:
            # Parsing logic for FNAC search results
            try:
                book_info['title'] = soup.find('a', {'class': 'Article-title'}).text.strip()
                book_info['author'] = soup.find('a', {'class': 'Article-author'}).text.strip()
                book_info['publisher'] = soup.find('a', {'class': 'Article-publisher'}).text.strip()
                book_info['isbn'] = soup.find('span', {'class': 'Article-isbn'}).text.strip()
                book_info['price'] = soup.find('span', {'class': 'Article-price'}).text.strip()
            except AttributeError as e:
                print(f"Error parsing book information: {e}")

        if self.verbose > 0:
            print(book_info)

        return book_info
    
    def check_book_list(self, filename: str) -> pd.DataFrame:
        """
        Check the list of books
        
        Args:
        filename: str
        
        Returns:
        pd.DataFrame: DataFrame with book information
        """
        book_titles = pd.read_excel(
            f"{self.output_dir}/{filename}.xlsx",
            index_col=None
        ).fillna({
            'ISBN': '',
            'Editeur': '',
            'Année': 0
        }).astype({
            'ISBN': 'str'
        })
        df_books = self.fetch_book_info_from_isbn(book_titles['ISBN']).dropna()
        df_books = book_titles.set_index('ISBN').join(df_books.set_index('ISBN'), how='inner', rsuffix='_infos')
        if self.verbose > 0:
            print(book_titles)
        self.export_to_excel(df_books, filename + '_infos')
        return book_titles