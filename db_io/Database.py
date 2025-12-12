# Database class definition
#
import os.path

# version can be production or devel, passed through the steering card
# - production will use the CLAS12TEST table
# - devel will use the CLAS12OCR table
#
# connection can be mysql or sqlite, passed through the steering card
# - mysql will set the connection to
# - sqlite will set the filename to

class Database():

	# constructor from Steering Card (scard) text file
	def __init__(self, dbtype, version):

		self.dbtype         = dbtype
		self.version        = version



	def connect_to_mysql(host, username, password, db_name):

		# This is so tests work on travis-ci, where we ue root user
		if username == 'root':
			host='localhost'

		return MySQLdb.connect(host, username, password, db_name)

	def show(self):
		print('Database:');
		print('- dbtype:   {0}'.format(self.dbtype));
		print('- version:  {0}'.format(self.version));


#db = Database()
#print(conf.client_ip)
