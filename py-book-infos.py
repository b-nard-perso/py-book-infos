#
#
# Credits
# https://jevalide.ca/2024/03/24/bibliographie-avec-python-depuis-une-liste-de-livres/
#
# Ref https://pypi.org/project/isbnlib/

from BookInfos import BookInfos
import pandas as pd
import argparse

# Use arguments to run long tasks only when needed,
# depending also on the possibility to access the web.
parser = argparse.ArgumentParser('py-book-infos')
parser.add_argument(
    '--check-external-reference',
    dest='check_external_reference',
    action='store_true',
    help='Check the external reference database of books'
)
parser.add_argument(
    '--fetch-reference-database',
    dest='fetch_reference_database',
    action='store_true',
    help='Fetch the reference database of books'
)
parser.add_argument(
    '--fetch-book-infos',
    dest='fetch_book_infos',
    action='store_true',
    help='Fetch the information of books'
)
parser.add_argument(
    '--test',
    dest='test',
    action='store_true',
    help='For tetsting purposes'
)

args = parser.parse_args()

if args.test:
    print("Test")
    exit(0)

if args.fetch_book_infos:
    book_titles = pd.read_excel(
        "../Export/book_titles.xlsx",
        index_col=None
    ).fillna({
        'ISBN': 0,
        'Nom': '',
        "Prénom": '',
        'Editeur': '',
        'Année': 0
    }).astype({
        'ISBN': 'int64',
        'Année': 'int'
    })
    print(book_titles)

infos = BookInfos()
# Load a reference database of books and fetch information from the web
ref_book_info = pd.DataFrame()
if args.check_external_reference:
    ref_book_info = infos.check_book_list("Rqt_Livres_Externes")

print('This is the end')

exit(0)

# Load the personal reference database of books and fetch information from the web
infos.fetch_reference_database()
df_existing, df_new = infos.compare_with_reference_database(book_titles)


exit(0)


df_book_infos = infos.fetch_book_infos(df_new['Titre'] + ' ' + df_new['Nom'])
df_new = df_new.join(df_book_infos, rsuffix='_infos')
infos.export_to_excel(df_new, 'new_books')

exit(0)
# Don't execute this part since did not manage to overcome the protection of the site
with open("../Export/book_infos_fnac.txt", "w", encoding="utf-8") as file:
    for title in book_titles['Titre'][0:2]:
        print(title)
        info = infos.fetch_book_info_from_fnac(title)
        file.write(f"\n\n{title}: {info}\n")

print("Done")
# df_books = infos.fetch_book_infos(book_titles)
# infos.export_to_excel(df_books, 'book_infos')
