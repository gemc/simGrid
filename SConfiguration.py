# SConfiguration class definition

import os.path

from statuses import NOTSUBMITTED, PROCESSING, SUBMITTED, SCRIPTS_GENERATED


class SConfiguration():
	"""Steering card configuration for a simulation submission."""

	def __init__(self, scardFile):
		"""Initialize from a scard text file."""
		self._init_fields()
		self.file = scardFile

		if not os.path.isfile(scardFile):
			raise FileNotFoundError('Scard file not found: {}'.format(scardFile))

		with open(scardFile) as f:
			self.parseSCard(f.read())

	@classmethod
	def from_string(cls, scard_text):
		"""Initialize from a scard text string (e.g. fetched from the database)."""
		obj = cls.__new__(cls)
		obj._init_fields()
		obj.parseSCard(scard_text)
		return obj

	def _init_fields(self):
		"""Set all scard attributes to None."""
		self.file          = None
		self.project       = None
		self.type          = None
		self.connection    = None
		self.version       = None
		self.username      = None
		self.configuration = None
		self.generator     = None
		self.genOptions    = None
		self.nevents       = None
		self.njobs         = None
		self.jobs          = None
		self.client_ip     = None
		self.fields        = None
		self.torus         = None
		self.solenoid      = None
		self.bkmerging     = None
		self.softwarev     = None
		self.dstOUT        = None
		self.zposition     = None
		self.raster        = None
		self.beam          = None
		self.vertex_choice = None
		self.string_id     = None
		self.output_type   = None
		self.submission    = None
		self.gemcv         = None
		self.coatjavav     = None
		self.genExecutable = None
		self.user_string   = None
		self._extra        = {}

	def parseSCard(self, scardContent):
		"""Parse scard key: value lines into attributes.

		Unknown keys are stored in _extra rather than raising an error,
		so the class stays forward-compatible with new scard fields.
		After parsing, _resolve_type() is called to ensure self.type is
		always set even when the scard omits the type field.
		"""
		label = self.file if self.file else 'string'

		for raw_line in scardContent.splitlines():
			line = raw_line.strip()
			if not line:
				continue

			pos = line.find(':')
			if pos < 0:
				continue

			key   = line[:pos].strip()
			value = line[pos + 1:].strip()

			if not key or key == 'file':
				continue

			if hasattr(self, key) and not key.startswith('_'):
				setattr(self, key, value)
			else:
				self._extra[key] = value

		self._resolve_type()
		self._resolve_software_versions()
		print('SConfiguration: parsed {} successfully (type {})'.format(label, self.type))

	def _resolve_software_versions(self):
		"""Populate gemcv and coatjavav from softwarev (e.g. 'gemc/5.10 coatjava/10.0.7')."""
		if not self.softwarev:
			return
		for token in self.softwarev.split():
			if '/' not in token:
				continue
			name, _, version = token.partition('/')
			if name == 'gemc':
				self.gemcv = version
			elif name == 'coatjava':
				self.coatjavav = version

	def _resolve_type(self):
		"""Set self.type to '1' or '2' when the scard does not include it.

		Type 1 — generator-based: the generator field holds a known executable
		         name (e.g. 'clasdis', 'dvcs', 'pythia').  The node runs the
		         generator to produce events, then feeds them to gemc.

		Type 2 — lund-file-based: the generator field holds a filesystem path
		         or URL pointing to a directory of pre-generated lund files
		         (starts with '/' or contains '://').  Each subjob reads one
		         lund file; the number of jobs equals the number of files.

		If type is already set explicitly in the scard it is left unchanged.
		"""
		if self.type is not None:
			return
		if self.generator and (
			self.generator.startswith('/') or '://' in self.generator
		):
			self.type = '2'
		else:
			self.type = '1'

	def show(self):
		"""Print all fields in aligned format."""
		known = [
			('file',          self.file),
			('project',       self.project),
			('type',          self.type),
			('connection',    self.connection),
			('version',       self.version),
			('username',      self.username),
			('configuration', self.configuration),
			('generator',     self.generator),
			('genOptions',    self.genOptions),
			('nevents',       self.nevents),
			('njobs',         self.njobs),
			('client_ip',     self.client_ip),
			('fields',        self.fields),
			('torus',         self.torus),
			('solenoid',      self.solenoid),
			('bkmerging',     self.bkmerging),
			('softwarev',     self.softwarev),
			('dstOUT',        self.dstOUT),
			('zposition',     self.zposition),
			('raster',        self.raster),
			('beam',          self.beam),
			('vertex_choice', self.vertex_choice),
			('string_id',     self.string_id),
			('output_type',   self.output_type),
			('submission',    self.submission),
		]
		extra = [(k, v) for k, v in self._extra.items()]
		all_fields = known + extra

		width = max(len(k) for k, _ in all_fields)
		print('SConfiguration:')
		for key, value in all_fields:
			print('  {} : {}'.format(key.ljust(width), value))
