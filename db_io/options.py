# Import packageds/modules
import argparse

# This function will return all command line arguemnts as an object
def get_args():

	# Initalize an argparser object. Documentation on the argparser module is here:
	# https://docs.python.org/3/library/argparse.html
	argparser = argparse.ArgumentParser(prog='dbTests', usage='%(prog)s [options]')

	# Add ability for user to specify that they want to use SQLite, instead of MySQL database
	# Also, lets user specify the name and path of the SQLite DB file to use
	argparser.add_argument('--sqlite', help="use SQLITE file as DB. Example: test.sqlite", type=str, default=None)

	# Boolean arguement of using TEST MySQL DB or the main MySQL DB
	argparser.add_argument('--test', action='store_true', help='Use table CLAS12TEST instead of default CLAS12OCR', default=False)

	# Boolean arguement for resetting test database
	argparser.add_argument('--reset', action='store_true', help='Delete and re-create the CLAS12TEST database table', default=False)

	# Boolean arguement resetting production database
	argparser.add_argument('--force-reset', action='store_true', help='DANGER ZONE: Delete and re-create the CLAS12OCR database table', default=False)

	# Convert the arguement strings into attributes of the namespace
	args = argparser.parse_args()

	return args
