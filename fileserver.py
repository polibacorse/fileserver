from http.server import SimpleHTTPRequestHandler, HTTPServer
import os, sys, io, urllib, html
from http import HTTPStatus
from datetime import datetime
import tarfile
import shutil

class FileHandler(SimpleHTTPRequestHandler):
	def list_directory(self, path):
		"""Helper to produce a directory listing (absent index.html).
		Return value is either a file object, or None (indicating an
		error).  In either case, the headers are sent, making the
		interface the same as for send_head().
		"""
		url = urllib.parse.urlparse(self.path)
		query = urllib.parse.parse_qs(url.query)
		# dispatch query
		if query:
			self.evaluate(query, path)

		try:
			list = os.listdir(path)
		except OSError:
			self.send_error(
				HTTPStatus.NOT_FOUND,
				"No permission to list directory")
			return None
		list.sort(key=lambda a: a.lower())
		r = []
		displaypath = url.path
		enc = sys.getfilesystemencoding()
		title = 'Directory listing for %s' % displaypath
		r.append('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" '
			'"http://www.w3.org/TR/html4/strict.dtd">')
		r.append('<html>\n<head>')
		r.append('<meta http-equiv="Content-Type" '
			'content="text/html; charset=%s">' % enc)
		r.append('<title>%s</title>\n</head>' % title)
		r.append('<body>\n<h1>%s</h1>' % title)
		r.append('<hr>\n<form action="." method="GET">\n<ul>')
		for name in list:
			fullname = os.path.join(path, name)
			displayname = linkname = name
			# Append / for directories or @ for symbolic links
			if os.path.isdir(fullname):
				displayname = name + "/"
				linkname = name + "/"
			if os.path.islink(fullname):
				displayname = name + "@"
				# Note: a link to a directory displays with @ and links with /
			r.append('<li>'
				'<input type="checkbox" name="files" value="{1}">'
				'<a href="{0}">{1}</a></li>'.format(
					urllib.parse.quote(linkname, errors='surrogatepass'),
					html.escape(displayname, quote=False)
				))
		r.append('</ul>\n'
			'<input type="submit" name="action" value="Download">\n'
			'<input type="submit" name="action" value="Delete">\n'
			'</form>\n<hr>\n<em>PC5 Linux &mdash; Fileserver</em>'
			'</body>\n</html>\n')
		encoded = '\n'.join(r).encode(enc, 'surrogateescape')
		f = io.BytesIO()
		f.write(encoded)
		f.seek(0)
		self.send_response(HTTPStatus.OK)
		self.send_header("Content-type", "text/html; charset=%s" % enc)
		self.send_header("Content-Length", str(len(encoded)))
		self.end_headers()
		return f

	def evaluate(self, query, path):
		if query['action'][0] == 'Download':
			# archive creation
			filename = path + datetime.today().isoformat() + '.tar.xz'
			archive = tarfile.open(name=filename, mode='x:xz')
			for file in query['files']:
				archive.add(path + file)
			archive.close()

			# send file
			with open(filename, 'rb') as f:
				self.send_response(HTTPStatus.OK)
				self.send_header('Content-type', 'application/octet-stream')
				self.send_header('Content-Disposition', 'attachment; filename="{}"'.format(filename))
				fs = os.fstat(f.fileno())
				self.send_header('Content-Length', str(fs.st_size))
				self.end_headers()
				try:
					shutil.copyfileobj(f, self.wfile)
				except BrokenPipeError:
					pass

		if query['action'][0] == 'Delete':
			for file in query['files']:
				try:
					os.remove(path + file)
				except OSError: # directory
					try: 
						shutil.rmtree(path + file)
					except FileNotFoundError:
						return

def main():
	server_address = ('', 8000)
	httpd = HTTPServer(server_address, FileHandler)
	httpd.serve_forever()

if __name__ == '__main__':
	main()